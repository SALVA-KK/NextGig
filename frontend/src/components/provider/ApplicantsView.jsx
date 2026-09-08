import React, { useState, useEffect } from 'react';
import { opportunityService } from '../../services/opportunityService';
import { api } from '../../services/authService';

export default function ApplicantsView({ selectedOpportunity = null, onSelectOpportunity }) {
  const [opportunities, setOpportunities] = useState([]);
  const [activeOpp, setActiveOpp] = useState(selectedOpportunity);
  const [applicants, setApplicants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);
  const [error, setError] = useState(null);

  // Sync selectedOpportunity prop when changed by parent
  useEffect(() => {
    if (selectedOpportunity) {
      setActiveOpp(selectedOpportunity);
    }
  }, [selectedOpportunity]);

  // Load opportunities posted by this provider to populate dropdown selection
  useEffect(() => {
    const loadMyOpps = async () => {
      try {
        const currentUser = api.defaults.headers.common?.Authorization ? authService.getCurrentUser() : null;
        const data = await opportunityService.getOpportunities({ status: 'all' });
        const allOpps = data.results || [];
        const myOpps = currentUser
          ? allOpps.filter(
              (opp) =>
                opp.poster?.id === currentUser.id ||
                opp.poster?.email === currentUser.email ||
                opp.poster === currentUser.id
            )
          : allOpps;
        setOpportunities(myOpps);
        if (!activeOpp && myOpps.length > 0) {
          setActiveOpp(myOpps[0]);
        }
      } catch (err) {
        console.error('Error fetching opportunities for dropdown:', err);
      }
    };
    loadMyOpps();
  }, []);


  // Fetch applicants whenever activeOpp changes
  useEffect(() => {
    if (!activeOpp?.id) return;
    const fetchApplicants = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await opportunityService.getOpportunityApplicants(activeOpp.id);
        setApplicants(data);
      } catch (err) {
        console.error('Error fetching applicants:', err);
        setError('Failed to load applicants for this opportunity.');
      } finally {
        setLoading(false);
      }
    };
    fetchApplicants();
  }, [activeOpp]);

  const handleStatusUpdate = async (applicationId, newStatus) => {
    setUpdatingId(applicationId);
    try {
      await opportunityService.updateApplicationStatus(applicationId, newStatus);
      setApplicants((prev) =>
        prev.map((app) => (app.id === applicationId ? { ...app, status: newStatus } : app))
      );
    } catch (err) {
      console.error('Error updating status:', err);
      alert('Failed to update application status.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDownloadResume = async (resumeUrl, applicantName) => {
    if (!resumeUrl) return;
    try {
      const response = await api.get(resumeUrl, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: response.headers['content-type'] || 'application/pdf' });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      const safeName = (applicantName || 'Applicant').replace(/\s+/g, '_');
      link.setAttribute('download', `${safeName}_Resume.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Failed to download resume:', err);
      alert('Failed to download resume file.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Review Applicants</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            View candidate resumes, review cover notes, and update application status.
          </p>
        </div>

        {opportunities.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label style={{ fontSize: '14px', fontWeight: '600' }}>Opportunity:</label>
            <select
              value={activeOpp?.id || ''}
              onChange={(e) => {
                const found = opportunities.find((o) => o.id === parseInt(e.target.value, 10));
                if (found) {
                  setActiveOpp(found);
                  if (onSelectOpportunity) onSelectOpportunity(found);
                }
              }}
              className="auth-input"
              style={{ minWidth: '240px' }}
            >
              {opportunities.map((opp) => (
                <option key={opp.id} value={opp.id}>
                  {opp.title} ({opp.status})
                </option>
              ))}
            </select>
          </div>
        )}
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

      {loading ? (
        <div className="discovery-loading">Loading applicants...</div>
      ) : !activeOpp ? (
        <div className="dashboard-stat-card" style={{ textAlign: 'center', padding: '36px' }}>
          Select an opportunity above to view applicants.
        </div>
      ) : applicants.length === 0 ? (
        <div className="dashboard-stat-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>👥</div>
          <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '8px' }}>No Applicants Yet</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            No candidates have applied to <strong>"{activeOpp.title}"</strong> yet.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {applicants.map((app) => {
            const applicantName = app.applicant?.full_name || app.applicant?.email || 'Applicant';
            return (
              <div
                key={app.id}
                className="dashboard-stat-card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  padding: '20px 24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>
                      {applicantName}
                    </h3>
                    <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                      Email: {app.applicant?.email} • Applied: {new Date(app.applied_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      className={`status-badge ${
                        app.status === 'accepted'
                          ? 'enabled'
                          : app.status === 'rejected'
                          ? 'pending'
                          : 'active'
                      }`}
                    >
                      {app.status?.toUpperCase().replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {app.cover_note && (
                  <div
                    style={{
                      padding: '12px 16px',
                      backgroundColor: 'var(--bg-canvas)',
                      borderRadius: '8px',
                      fontSize: '14px',
                      color: 'var(--text-main)',
                      lineHeight: '1.5',
                    }}
                  >
                    <strong>Cover Note:</strong> {app.cover_note}
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginTop: '4px' }}>
                  <div>
                    {app.has_resume && app.resume_download_url ? (
                      <button
                        onClick={() => handleDownloadResume(app.resume_download_url, applicantName)}
                        className="btn-secondary-link"
                        style={{ border: '1px solid var(--accent-indigo)', color: 'var(--accent-indigo)', padding: '6px 14px' }}
                      >
                        📄 Download Resume
                      </button>
                    ) : (
                      <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No resume attached</span>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      disabled={updatingId === app.id || app.status === 'under_review'}
                      onClick={() => handleStatusUpdate(app.id, 'under_review')}
                      className="btn-secondary-link"
                      style={{ border: '1px solid var(--border-color)', padding: '6px 12px' }}
                    >
                      ⏳ Under Review
                    </button>
                    <button
                      disabled={updatingId === app.id || app.status === 'accepted'}
                      onClick={() => handleStatusUpdate(app.id, 'accepted')}
                      className="btn-primary-sm"
                      style={{ backgroundColor: '#10b981', padding: '6px 14px' }}
                    >
                      ✓ Accept
                    </button>
                    <button
                      disabled={updatingId === app.id || app.status === 'rejected'}
                      onClick={() => handleStatusUpdate(app.id, 'rejected')}
                      className="btn-secondary-link"
                      style={{ border: '1px solid #fecaca', color: '#b91c1c', padding: '6px 12px' }}
                    >
                      ✕ Reject
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
