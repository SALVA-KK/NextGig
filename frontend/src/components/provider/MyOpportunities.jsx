import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { opportunityService } from '../../services/opportunityService';
import { authService } from '../../services/authService';
import PaginationControl from '../common/PaginationControl';

export default function MyOpportunities({ onAddNew }) {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const currentUser = authService.getCurrentUser();

  const loadMyOpportunities = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch all status listings (open, closed, draft)
      const data = await opportunityService.getOpportunities({ status: 'all', page: currentPage });
      const allOpps = data.results || [];

      // Filter for opportunities posted by current user
      const myOpps = allOpps.filter((opp) => {
        if (!currentUser) return false;
        return (
          opp.poster?.id === currentUser.id ||
          opp.poster?.email === currentUser.email ||
          opp.poster === currentUser.id
        );
      });

      setOpportunities(myOpps);
      setTotalCount(data.count ?? myOpps.length);
    } catch (err) {
      console.error('Error fetching posted opportunities:', err);
      setError('Failed to load your posted opportunities. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMyOpportunities();
  }, [currentPage]);

  if (loading) {
    return <div className="discovery-loading">Loading your posted opportunities...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700' }}>My Posted Opportunities</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            Overview of your active and past opportunity listings. Click any card to view details, review applicants, edit, or update listing status.
          </p>
        </div>
        <button onClick={onAddNew} className="btn-primary-sm">
          + Post New Opportunity
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            backgroundColor: '#fef2f2',
            color: '#b91c1c',
            border: '1px solid #fecaca',
          }}
        >
          {error}
        </div>
      )}

      {opportunities.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm text-center p-8 sm:p-12">
          <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '8px' }}>No Opportunities Posted Yet</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '20px' }}>
            You have not posted any opportunities yet. Create your first job or internship listing to start receiving applications.
          </p>
          <button onClick={onAddNew} className="btn-primary-lg">
            Post Your First Opportunity
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {opportunities.map((opp) => (
            <div
              key={opp.id}
              onClick={() => navigate(`/provider-dashboard/opportunities/${opp.id}`)}
              className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4 sm:p-6 cursor-pointer transition-colors active:bg-slate-50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                    {opp.title}
                  </h3>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                      opp.status === 'open'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-slate-100 text-slate-600 border border-slate-200'
                    }`}
                  >
                    {opp.status?.toUpperCase()}
                  </span>
                </div>
                <div className="text-xs font-medium text-slate-500 flex flex-wrap gap-x-4 gap-y-1">
                  <span>
                    <strong className="text-slate-700">Category:</strong> {opp.category?.replace('_', ' ')}
                  </span>
                  <span>
                    <strong className="text-slate-700">Posted:</strong> {new Date(opp.created_at).toLocaleDateString()}
                  </span>
                  <span>
                    <strong className="text-slate-700">Applicants:</strong> {opp.applicants_count ?? 0}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* PAGINATION CONTROL */}
      {!loading && !error && (
        <PaginationControl
          currentPage={currentPage}
          totalItems={totalCount}
          pageSize={20}
          onPageChange={(newPage) => setCurrentPage(newPage)}
        />
      )}
    </div>
  );
}
