import React, { useState, useEffect } from 'react';
import { opportunityService } from '../../services/opportunityService';
import { api, authService } from '../../services/authService';
import PaginationControl from '../common/PaginationControl';

export default function ApplicantsView({ selectedOpportunity = null, onSelectOpportunity }) {
  const [opportunities, setOpportunities] = useState([]);
  const [activeOpp, setActiveOpp] = useState(selectedOpportunity || 'all');
  const [applicants, setApplicants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [updatingId, setUpdatingId] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [downloadError, setDownloadError] = useState({});
  const [error, setError] = useState(null);

  // Sync selectedOpportunity prop when changed by parent
  useEffect(() => {
    if (selectedOpportunity) {
      setActiveOpp(selectedOpportunity);
      setCurrentPage(1);
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
      } catch (err) {
        console.error('Error fetching opportunities for dropdown:', err);
      }
    };
    loadMyOpps();
  }, []);

  // Fetch applicants whenever activeOpp or currentPage changes
  useEffect(() => {
    const fetchApplicants = async () => {
      setLoading(true);
      setError(null);
      try {
        let data;
        if (!activeOpp || activeOpp === 'all') {
          data = await opportunityService.getReceivedApplications({ page: currentPage });
        } else if (activeOpp?.id) {
          data = await opportunityService.getOpportunityApplicants(activeOpp.id, { page: currentPage });
        }
        const results = data?.results || (Array.isArray(data) ? data : []);
        setApplicants(results);
        setTotalCount(data?.count ?? results.length);
      } catch (err) {
        console.error('Error fetching applicants:', err);
        setError('Failed to load applicants for this view.');
      } finally {
        setLoading(false);
      }
    };
    fetchApplicants();
  }, [activeOpp, currentPage]);

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

  const handleFetchAndAction = async (applicationId, resumeUrl, actionType, applicantName = 'Applicant') => {
    if (!resumeUrl) return;
    setDownloadingId(applicationId);
    setDownloadError((prev) => ({ ...prev, [applicationId]: null }));

    try {
      // Strip leading '/api' if present since Axios api instance baseURL already includes '/api'
      const endpoint = resumeUrl.replace(/^\/api/, '');
      const response = await api.get(endpoint, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: response.headers['content-type'] || 'application/pdf' });
      const blobUrl = window.URL.createObjectURL(blob);

      if (actionType === 'view') {
        window.open(blobUrl, '_blank');
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 10000);
      } else {
        const link = document.createElement('a');
        link.href = blobUrl;
        const safeName = (applicantName || 'Applicant').replace(/\s+/g, '_');
        link.setAttribute('download', `${safeName}_Resume.pdf`);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
      }
    } catch (err) {
      console.error('Failed to load resume:', err);
      setDownloadError((prev) => ({ ...prev, [applicationId]: 'Could not load resume' }));
    } finally {
      setDownloadingId(null);
    }
  };

  const selectedValue = activeOpp === 'all' || !activeOpp ? 'all' : (activeOpp.id || '');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Review Applicants</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            View candidate resumes, review cover notes, and update application status.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '14px', fontWeight: '600' }}>Filter Opportunity:</label>
          <select
            value={selectedValue}
            onChange={(e) => {
              const val = e.target.value;
              setCurrentPage(1);
              if (val === 'all') {
                setActiveOpp('all');
                if (onSelectOpportunity) onSelectOpportunity(null);
              } else {
                const found = opportunities.find((o) => o.id === parseInt(val, 10));
                if (found) {
                  setActiveOpp(found);
                  if (onSelectOpportunity) onSelectOpportunity(found);
                }
              }
            }}
            className="auth-input"
            style={{ minWidth: '260px' }}
          >
            <option value="all">All Applicants (Combined Overview)</option>
            {opportunities.map((opp) => (
              <option key={opp.id} value={opp.id}>
                {opp.title} ({opp.status})
              </option>
            ))}
          </select>
        </div>
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
      ) : applicants.length === 0 ? (
        <div className="dashboard-stat-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '8px' }}>No Applicants Found</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            {activeOpp === 'all' || !activeOpp
              ? 'No candidate applications received across any of your posted opportunities yet.'
              : `No candidates have applied to "${activeOpp.title}" yet.`}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {applicants.map((app) => {
            const applicantName = app.applicant?.full_name || app.applicant?.email || 'Applicant';
            const isDownloading = downloadingId === app.id;
            const errText = downloadError[app.id];

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
                    {app.opportunity?.title && (
                      <div
                        style={{
                          fontSize: '12px',
                          fontWeight: '700',
                          color: 'var(--accent-indigo, #6366f1)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          marginBottom: '4px',
                        }}
                      >
                        Applied For: {app.opportunity.title} ({app.opportunity.category?.replace('_', ' ')})
                      </div>
                    )}
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
                      <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                          <button
                            onClick={() => handleFetchAndAction(app.id, app.resume_download_url, 'view')}
                            disabled={isDownloading}
                            className="btn-secondary-link"
                            style={{ border: '1px solid var(--accent-indigo)', color: 'var(--accent-indigo)', padding: '6px 14px' }}
                          >
                            {isDownloading ? 'Loading Resume...' : 'View Resume'}
                          </button>
                          <button
                            onClick={() => handleFetchAndAction(app.id, app.resume_download_url, 'download', applicantName)}
                            disabled={isDownloading}
                            className="btn-secondary-link"
                            style={{ border: '1px solid var(--border-color)', color: 'var(--text-muted)', padding: '6px 10px', fontSize: '12px' }}
                            title="Download file to disk"
                          >
                            Save File
                          </button>
                        </div>
                        {errText && (
                          <span style={{ fontSize: '12px', color: '#b91c1c' }}>{errText}</span>
                        )}
                      </div>
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
                      Under Review
                    </button>
                    <button
                      disabled={updatingId === app.id || app.status === 'accepted'}
                      onClick={() => handleStatusUpdate(app.id, 'accepted')}
                      className="btn-primary-sm"
                      style={{ backgroundColor: '#10b981', padding: '6px 14px' }}
                    >
                      Accept
                    </button>
                    <button
                      disabled={updatingId === app.id || app.status === 'rejected'}
                      onClick={() => handleStatusUpdate(app.id, 'rejected')}
                      className="btn-secondary-link"
                      style={{ border: '1px solid #fecaca', color: '#b91c1c', padding: '6px 12px' }}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* PAGINATION CONTROL */}
      {!loading && !error && activeOpp && (
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
