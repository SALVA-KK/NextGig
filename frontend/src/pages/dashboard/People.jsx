import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, Users, MapPin, GraduationCap, Building2 } from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import PaginationControl from '../../components/common/PaginationControl';
import EmptyState from '../../components/common/EmptyState';
import { peopleService } from '../../services/peopleService';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const BACKEND_HOST = API_BASE_URL ? API_BASE_URL.replace(/\/api\/?$/, '') : '';

function PersonAvatar({ src, name }) {
  const [imgError, setImgError] = useState(false);
  const initial = (name || '?').charAt(0).toUpperCase();

  let avatarSrc = src;
  if (src && typeof src === 'string' && src.startsWith('/')) {
    avatarSrc = `${BACKEND_HOST}${src}`;
  }

  return (
    <div className="w-12 h-12 rounded-full overflow-hidden border border-slate-200 bg-indigo-50 flex items-center justify-center flex-shrink-0">
      {avatarSrc && !imgError ? (
        <img
          src={avatarSrc}
          alt={name}
          className="w-full h-full object-cover"
          onError={() => setImgError(true)}
        />
      ) : (
        <span className="text-base font-bold text-indigo-600">
          {initial}
        </span>
      )}
    </div>
  );
}

function StudentCard({ person }) {
  const name = person.full_name || person.display_name || 'Student';
  const skills = Array.isArray(person.skills) ? person.skills.slice(0, 5) : [];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div className="space-y-4">
        {/* Header: Avatar, Name, Role Badge */}
        <div className="flex items-start gap-3">
          <PersonAvatar src={person.profile_picture} name={name} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-slate-900 truncate" title={name}>
                {name}
              </h3>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-100">
                Student
              </span>
            </div>
            {person.profession && (
              <p className="text-xs font-medium text-slate-600 truncate mt-0.5" title={person.profession}>
                {person.profession}
              </p>
            )}
          </div>
        </div>

        {/* Details: Institution / Qualification, City, Availability */}
        <div className="space-y-2 pt-1 text-xs text-slate-600">
          {(person.institution || person.qualification_name) && (
            <div className="flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className="truncate" title={[person.qualification_name, person.institution].filter(Boolean).join(' • ')}>
                {[person.qualification_name, person.institution].filter(Boolean).join(' • ')}
              </span>
            </div>
          )}

          {person.city && (
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className="truncate">{person.city}</span>
            </div>
          )}

          {person.availability && (
            <div className="pt-1">
              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {person.availability}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Skills chips */}
      {skills.length > 0 && (
        <div className="pt-4 border-t border-slate-100 mt-4">
          <div className="flex flex-wrap gap-1.5">
            {skills.map((skill, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ProviderCard({ person }) {
  const orgName = person.organization_name || person.display_name || 'Organization';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div className="space-y-4">
        {/* Header: Avatar, Organization Name, Verified Badge, Role Badge */}
        <div className="flex items-start gap-3">
          <PersonAvatar src={person.profile_picture} name={orgName} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-slate-900 truncate" title={orgName}>
                {orgName}
              </h3>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-200">
                Provider
              </span>
            </div>

            {person.is_verified && (
              <div className="mt-1.5">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Verified
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Details: Organization Type, City */}
        <div className="space-y-2 pt-1 text-xs text-slate-600">
          {person.organization_type && (
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className="truncate capitalize">{person.organization_type.replace('_', ' ')}</span>
            </div>
          )}

          {person.city && (
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className="truncate">{person.city}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function People() {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [people, setPeople] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const requestIdRef = useRef(0);

  // Debounce search input by 400ms, trimmed, max 100 characters
  useEffect(() => {
    const handler = setTimeout(() => {
      const trimmed = searchTerm.trim().slice(0, 100);
      setDebouncedQ(trimmed);
    }, 400);

    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Reset to page 1 whenever debounced query changes
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedQ]);

  // Fetch people matching debounced query and page
  const fetchPeople = useCallback(async (q, page) => {
    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const params = { page };
      if (q) {
        params.q = q;
      }
      const data = await peopleService.searchPeople(params);

      // Ignore stale responses
      if (currentRequestId === requestIdRef.current) {
        setPeople(data.results || []);
        setTotalCount(data.count ?? (data.results || []).length);
      }
    } catch (err) {
      if (currentRequestId === requestIdRef.current) {
        console.error('Failed to load people:', err);
        setError('Unable to load people right now. Please check your connection and try again.');
      }
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchPeople(debouncedQ, currentPage);
  }, [debouncedQ, currentPage, fetchPeople]);

  const handleRetry = () => {
    fetchPeople(debouncedQ, currentPage);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <DashboardLayout activeTab="people">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">People</h1>
            <p className="text-sm text-slate-500 mt-1">
              Discover students, collaborators, and verified providers on NextGig.
            </p>
          </div>

          {/* Search Input */}
          <div className="relative w-full sm:w-80">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              maxLength={100}
              placeholder="Search people..."
              className="w-full pl-10 pr-10 py-2 bg-white border border-slate-200 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-xs"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                aria-label="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Feedback / Results Count */}
        {!loading && !error && people.length > 0 && debouncedQ && (
          <div className="text-xs font-medium text-slate-500">
            Found {totalCount} {totalCount === 1 ? 'person' : 'people'} matching &ldquo;{debouncedQ}&rdquo;
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div
                key={n}
                className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4 animate-pulse"
              >
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 rounded-full bg-slate-200 flex-shrink-0" />
                  <div className="space-y-2 flex-1 pt-1">
                    <div className="h-4 bg-slate-200 rounded w-3/4" />
                    <div className="h-3 bg-slate-200 rounded w-1/2" />
                  </div>
                </div>
                <div className="space-y-2 pt-2">
                  <div className="h-3 bg-slate-200 rounded w-2/3" />
                  <div className="h-3 bg-slate-200 rounded w-1/2" />
                </div>
                <div className="flex gap-2 pt-4 border-t border-slate-100">
                  <div className="h-5 bg-slate-200 rounded-md w-14" />
                  <div className="h-5 bg-slate-200 rounded-md w-16" />
                  <div className="h-5 bg-slate-200 rounded-md w-12" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 sm:p-12 text-center shadow-xs flex flex-col items-center justify-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-red-50 border border-red-100 flex items-center justify-center text-red-500">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div className="space-y-1.5 max-w-sm">
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                Unable to load people
              </h3>
              <p className="text-xs font-medium text-slate-500 leading-relaxed">
                {error}
              </p>
            </div>
            <button
              type="button"
              onClick={handleRetry}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-all"
            >
              Retry Loading
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && people.length === 0 && (
          <EmptyState
            icon={Users}
            title={debouncedQ ? 'No results found' : 'No people found'}
            subtitle={
              debouncedQ
                ? `No profiles match "${debouncedQ}". Try searching for another name, skill, or organization.`
                : 'There are currently no public profiles available.'
            }
            actionLabel={debouncedQ ? 'Clear Search' : undefined}
            onAction={debouncedQ ? () => setSearchTerm('') : undefined}
          />
        )}

        {/* Cards Grid */}
        {!loading && !error && people.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {people.map((person) =>
                person.role === 'provider' ? (
                  <ProviderCard key={`provider-${person.user_id}`} person={person} />
                ) : (
                  <StudentCard key={`student-${person.user_id}`} person={person} />
                )
              )}
            </div>

            <PaginationControl
              currentPage={currentPage}
              totalItems={totalCount}
              pageSize={20}
              onPageChange={handlePageChange}
            />
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
