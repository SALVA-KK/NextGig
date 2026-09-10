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
            Overview of your active and past opportunity listings. Click Manage to view details, review applicants, edit, or update listing status.
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
        <div
          className="dashboard-stat-card"
          style={{ textAlign: 'center', padding: '48px 24px', background: 'var(--bg-surface)' }}
        >
          <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '8px' }}>No Opportunities Posted Yet</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '20px' }}>
            You have not posted any opportunities yet. Create your first job or internship listing to start receiving applications.
          </p>
          <button onClick={onAddNew} className="btn-primary-lg">
            Post Your First Opportunity
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {opportunities.map((opp) => (
            <div
              key={opp.id}
              className="dashboard-stat-card"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px',
                padding: '20px 24px',
              }}
            >
              <div style={{ flex: '1 1 300px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-main)' }}>{opp.title}</h3>
                  <span className={`status-badge ${opp.status === 'open' ? 'enabled' : 'pending'}`}>
                    {opp.status?.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  <span><strong>Category:</strong> {opp.category?.replace('_', ' ')}</span>
                  <span><strong>Posted:</strong> {new Date(opp.created_at).toLocaleDateString()}</span>
                  <span><strong>Applicants:</strong> {opp.applicants_count ?? 0}</span>
                </div>
              </div>

              <div>
                <button
                  onClick={() => navigate(`/provider-dashboard/opportunities/${opp.id}`)}
                  className="btn-primary-sm"
                  style={{ minWidth: '100px' }}
                >
                  Manage
                </button>
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
