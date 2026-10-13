import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from apps.assistant.context import get_candidate_opportunities_context
from apps.assistant.rag.retrieval import retrieve_with_source
from apps.opportunities.models import Opportunity

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Evaluates RAG vector retrieval against baseline heuristic and keyword methods."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to evaluation JSON cases file.",
        )
        parser.add_argument(
            "--k",
            type=int,
            default=8,
            help="Number of top candidates to retrieve (default: 8).",
        )

    def handle(self, *args, **options):
        file_arg = options["file"]
        k = options["k"]

        file_path = Path(file_arg)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_arg

        if not file_path.exists():
            raise CommandError(f"Evaluation file does not exist: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cases = json.load(f)
        except Exception as exc:
            raise CommandError(f"Failed to read evaluation JSON file: {exc}")

        if not isinstance(cases, list) or not cases:
            raise CommandError("Evaluation JSON file must contain a non-empty list of cases.")

        today = timezone.localdate()
        open_opps = list(
            Opportunity.objects.filter(status=Opportunity.Status.OPEN)
            .filter(Q(deadline__isnull=True) | Q(deadline__gte=today))
            .order_by("-created_at")
        )
        open_opps_by_id = {opp.id: opp for opp in open_opps}

        api_calls_count = 0
        results: List[Dict[str, Any]] = []

        self.stdout.write(f"Loaded {len(cases)} test cases. Evaluating across {len(open_opps)} open opportunities...\n")

        for idx, case in enumerate(cases, start=1):
            query = case.get("query", "")
            profile = case.get("profile") or {}
            expected_ids = case.get("expected_ids") or []
            expected_titles = case.get("expected_titles") or []

            # 1. Resolve target IDs and warn on misses
            target_ids: Set[int] = set()

            for eid in expected_ids:
                if eid in open_opps_by_id:
                    target_ids.add(eid)
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[WARNING] Case #{idx} ('{query[:40]}...'): expected_id {eid} matches no open listing."
                        )
                    )

            for etitle in expected_titles:
                matching = [
                    opp.id for opp in open_opps if etitle.lower() in (opp.title or "").lower()
                ]
                if matching:
                    target_ids.update(matching)
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[WARNING] Case #{idx} ('{query[:40]}...'): expected_title '{etitle}' matches no open listing."
                        )
                    )

            # (a) OLD heuristic context
            _, old_opts = get_candidate_opportunities_context(profile)
            old_ranked_ids = [opt["id"] for opt in old_opts[:k]]
            old_rank: Optional[int] = None
            for r_idx, oid in enumerate(old_ranked_ids, start=1):
                if oid in target_ids:
                    old_rank = r_idx
                    break

            # (b) Keyword baseline
            query_tokens = [t for t in re.findall(r"\w+", query.lower()) if len(t) >= 3]
            scored_keyword = []
            for opp in open_opps:
                skills_str = " ".join(opp.required_skills) if isinstance(opp.required_skills, list) else ""
                haystack = f"{opp.title} {opp.description or ''} {skills_str}".lower()
                match_count = sum(1 for token in query_tokens if token in haystack)
                if match_count > 0:
                    scored_keyword.append((match_count, opp.id))

            scored_keyword.sort(key=lambda x: (x[0], x[1]), reverse=True)
            keyword_ranked_ids = [item[1] for item in scored_keyword[:k]]
            keyword_rank: Optional[int] = None
            for r_idx, oid in enumerate(keyword_ranked_ids, start=1):
                if oid in target_ids:
                    keyword_rank = r_idx
                    break

            # (c) Vector retrieval
            _, vector_opts, source, meta = retrieve_with_source(
                query_text=query,
                student_profile_data=profile,
                k=k,
                pool=20,
                return_metadata=True,
            )
            api_calls_count += 1

            vector_ranked_ids = [opt["id"] for opt in vector_opts[:k]]
            vector_rank: Optional[int] = None
            for r_idx, oid in enumerate(vector_ranked_ids, start=1):
                if oid in target_ids:
                    vector_rank = r_idx
                    break

            top_sim = meta.get("top_similarity")

            results.append({
                "query": query,
                "old_rank": old_rank,
                "keyword_rank": keyword_rank,
                "vector_rank": vector_rank,
                "top_sim": top_sim,
                "source": source,
            })

        # Render Per-query Table
        self.stdout.write("\n" + "=" * 90)
        self.stdout.write("PER-QUERY RETRIEVAL EVALUATION")
        self.stdout.write("=" * 90)
        header = f"{'#':<3} | {'Query':<40} | {'Old':<5} | {'Keyword':<7} | {'Vector':<6} | {'TopSim':<7} | {'Path':<8}"
        self.stdout.write(header)
        self.stdout.write("-" * 90)

        for idx, res in enumerate(results, start=1):
            q_str = res["query"][:40]
            old_str = str(res["old_rank"]) if res["old_rank"] is not None else "-"
            kw_str = str(res["keyword_rank"]) if res["keyword_rank"] is not None else "-"
            vec_str = str(res["vector_rank"]) if res["vector_rank"] is not None else "-"
            sim_str = f"{res['top_sim']:.3f}" if res["top_sim"] is not None else "-"
            path_str = res["source"]

            row = f"{idx:<3} | {q_str:<40} | {old_str:<5} | {kw_str:<7} | {vec_str:<6} | {sim_str:<7} | {path_str:<8}"
            self.stdout.write(row)

        self.stdout.write("=" * 90)

        # Compute Aggregated Metrics
        total_queries = len(results)

        def calc_metrics(rank_key: str):
            ranks = [r[rank_key] for r in results]
            hit_3 = sum(1 for r in ranks if r is not None and r <= 3)
            hit_k = sum(1 for r in ranks if r is not None and r <= k)
            mrr = sum((1.0 / r if r is not None else 0.0) for r in ranks) / total_queries if total_queries else 0.0
            return hit_3, hit_k, mrr

        old_h3, old_hk, old_mrr = calc_metrics("old_rank")
        kw_h3, kw_hk, kw_mrr = calc_metrics("keyword_rank")
        vec_h3, vec_hk, vec_mrr = calc_metrics("vector_rank")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"AGGREGATED METRICS SUMMARY (Total Cases: {total_queries}, k={k})")
        self.stdout.write("=" * 80)
        sum_header = f"{'Method':<20} | {'Hit@3':<18} | {f'Hit@{k}':<18} | {'MRR':<10}"
        self.stdout.write(sum_header)
        self.stdout.write("-" * 80)

        def fmt_row(name, h3, hk, mrr):
            h3_pct = (h3 / total_queries) * 100 if total_queries else 0.0
            hk_pct = (hk / total_queries) * 100 if total_queries else 0.0
            h3_str = f"{h3}/{total_queries} ({h3_pct:.1f}%)"
            hk_str = f"{hk}/{total_queries} ({hk_pct:.1f}%)"
            return f"{name:<20} | {h3_str:<18} | {hk_str:<18} | {mrr:.3f}"

        self.stdout.write(fmt_row("Old Heuristic", old_h3, old_hk, old_mrr))
        self.stdout.write(fmt_row("Keyword Baseline", kw_h3, kw_hk, kw_mrr))
        self.stdout.write(fmt_row("Vector Retrieval", vec_h3, vec_hk, vec_mrr))
        self.stdout.write("=" * 80)

        self.stdout.write(f"\nReal embedding API calls made: {api_calls_count}\n")
