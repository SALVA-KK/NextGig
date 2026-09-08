import React, { useState, useEffect } from 'react';
import { opportunityService } from '../../services/opportunityService';
import { authService } from '../../services/authService';

export default function MyOpportunities({ onViewApplicants, onEditOpportunity, onAddNew }) {
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const currentUser = authService.getCurrentUser();

  const loadMyOpportunities = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch all status listings (open, closed, draft)
      const data = await opportunityService.getOpportunities({ status: 'all' });
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
    } catch (err) {
      console.error('Error fetching posted opportunities:', err);
      setError('Failed to load your posted opportunities. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMyOpportunities();
  }, []);

  const handleToggleStatus = async (opp) => {
    const newStatus = opp.status === 'open' ? 'closed' : 'open';
    try {
      await opportunityService.updateOpportunity(opp.id, { status: newStatus });
      setOpportunities((prev) =>
        prev.map((item) => (item.id === opp.id ? { ...item, status: newStatus } : item))
      );
    } catch (err) {
      console.error('Error updating status:', err);
      alert('Failed to update opportunity status.');
    }
  };

  const handleDelete = async (oppId) => {
    if (!window.confirm('Are you sure you want to delete this opportunity listing? This action cannot be undone.')) {
      return;
    }
    try {
      await opportunityService.deleteOpportunity(oppId);
      setOpportunities((prev) => prev.filter((item) => item.id !== oppId));
    } catch (err) {
      console.error('Error deleting opportunity:', err);
      alert('Failed to delete opportunity listing.');
    }
  };

  if (loading) {
    return <div className="discovery-loading">Loading your posted opportunities...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700' }}>My Posted Opportunities</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            Manage your listings, review applicants, and toggle listing status.
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
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>📋</div>
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
                  <span>🏷️ {opp.category?.replace('_', ' ')}</span>
                  <span>📍 {opp.city || opp.work_mode}</span>
                  <span>💰 {opp.pay_type} {opp.pay_amount ? `$${opp.pay_amount}` : ''}</span>
                  <span>📅 Posted: {new Date(opp.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  onClick={() => onViewApplicants(opp)}
                  className="btn-primary-sm"
                  style={{ backgroundColor: 'var(--accent-indigo)' }}
                >
                  👥 View Applicants
                </button>
                <button
                  onClick={() => onEditOpportunity(opp)}
                  className="btn-secondary-link"
                  style={{ border: '1px solid var(--border-color)', padding: '6px 12px' }}
                >
                  ✏️ Edit
                </button>
                <button
                  onClick={() => handleToggleStatus(opp)}
                  className="btn-secondary-link"
                  style={{ border: '1px solid var(--border-color)', padding: '6px 12px' }}
                >
                  {opp.status === 'open' ? '🔒 Close' : '🔓 Reopen'}
                </button>
                <button
                  onClick={() => handleDelete(opp.id)}
                  className="btn-secondary-link"
                  style={{ border: '1px solid #fecaca', color: '#b91c1c', padding: '6px 12px' }}
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
