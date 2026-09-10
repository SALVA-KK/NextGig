import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import PostOpportunity from '../../components/provider/PostOpportunity';
import ApplicantsView from '../../components/provider/ApplicantsView';
import { opportunityService } from '../../services/opportunityService';
import { authService } from '../../services/authService';

export default function ManageOpportunity() {
  const { id } = useParams();
  const navigate = useNavigate();
  const currentUser = authService.getCurrentUser();
  const isAdmin = authService.isAdmin();

  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'applicants' | 'edit'
  const [actionLoading, setActionLoading] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [bannerMessage, setBannerMessage] = useState(null);

  const fetchOpportunity = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await opportunityService.getOpportunityById(id);
      setOpportunity(data);
    } catch (err) {
      console.error('Error fetching opportunity for management:', err);
      if (err.response?.status === 404) {
        setError('Opportunity listing not found.');
      } else if (err.response?.status === 403) {
        setError('You are not authorized to view or manage this opportunity listing.');
      } else {
        setError('Failed to load opportunity details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchOpportunity();
    }
  }, [id]);

  // Ownership Check
  const isOwner =
    currentUser &&
    opportunity &&
    (opportunity.poster?.id === currentUser.id ||
      opportunity.poster?.email === currentUser.email ||
      opportunity.poster === currentUser.id);

  const isAuthorized = isAdmin || isOwner;

  const handleToggleStatus = async () => {
    if (!opportunity) return;
    const newStatus = opportunity.status === 'open' ? 'closed' : 'open';
    setActionLoading(true);
    try {
      const updated = await opportunityService.updateOpportunity(opportunity.id, { status: newStatus });
      setOpportunity((prev) => ({ ...prev, status: newStatus }));
      setBannerMessage({
        type: 'success',
        text: `Opportunity status changed to ${newStatus.toUpperCase()}.`,
      });
    } catch (err) {
      console.error('Error updating status:', err);
      setBannerMessage({ type: 'error', text: 'Failed to update opportunity status.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!opportunity) return;
    setActionLoading(true);
    try {
      await opportunityService.deleteOpportunity(opportunity.id);
      navigate('/provider-dashboard', { state: { successMessage: 'Opportunity deleted.' } });
    } catch (err) {
      console.error('Error deleting opportunity:', err);
      setBannerMessage({ type: 'error', text: 'Failed to delete opportunity.' });
      setShowDeleteModal(false);
    } finally {
      setActionLoading(false);
    }
  };

  const handleEditSuccess = async () => {
    setBannerMessage({ type: 'success', text: 'Opportunity listing updated successfully!' });
    await fetchOpportunity();
    setActiveTab('overview');
  };

  if (loading) {
    return (
      <DashboardLayout activeTab="my-opportunities">
        <div className="discovery-container" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div className="discovery-loading">Loading opportunity details...</div>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !opportunity || !isAuthorized) {
    return (
      <DashboardLayout activeTab="my-opportunities">
        <div className="discovery-container">
          <div
            className="empty-state-box"
            style={{
              padding: '48px 24px',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: '12px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '40px', marginBottom: '16px' }}>🔒</div>
            <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>
              {error || 'Access Denied'}
            </h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '24px', maxWidth: '480px', margin: '0 auto 24px' }}>
              {!isAuthorized && !error
                ? 'You do not have permission to manage this opportunity listing, or it belongs to another provider.'
                : error}
            </p>
            <Link to="/provider-dashboard" className="btn-primary-lg" style={{ display: 'inline-block' }}>
              ← Return to My Opportunities
            </Link>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const formatPay = () => {
    if (opportunity.pay_type === 'unpaid') return 'Unpaid';
    if (!opportunity.pay_amount) return opportunity.pay_type ? opportunity.pay_type.toUpperCase() : 'Not Specified';
    const amountStr = `₹${Number(opportunity.pay_amount).toLocaleString('en-IN')}`;
    if (opportunity.pay_type === 'hourly') return `${amountStr} / hr`;
    if (opportunity.pay_type === 'monthly') return `${amountStr} / month`;
    if (opportunity.pay_type === 'stipend') return `${amountStr} stipend`;
    return amountStr;
  };

  return (
    <DashboardLayout activeTab="my-opportunities">
      <div className="discovery-container">
        {/* TOP BACK BAR & TITLE */}
        <div style={{ marginBottom: '20px' }}>
          <button
            onClick={() => navigate('/provider-dashboard')}
            className="btn-secondary-link"
            style={{
              border: 'none',
              background: 'none',
              padding: '0 0 12px 0',
              color: 'var(--accent-indigo)',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            ← Back to My Opportunities
          </button>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <h1 style={{ fontSize: '24px', fontWeight: '800', color: 'var(--text-main)' }}>
                  {opportunity.title}
                </h1>
                <span className={`status-badge ${opportunity.status === 'open' ? 'enabled' : 'pending'}`}>
                  {opportunity.status?.toUpperCase()}
                </span>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Posted on {new Date(opportunity.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            </div>

            {/* ACTION BUTTONS */}
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                onClick={handleToggleStatus}
                disabled={actionLoading}
                className="btn-secondary-link"
                style={{
                  border: '1px solid var(--border-color)',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                {opportunity.status === 'open' ? 'Close Listing' : 'Reopen Listing'}
              </button>

              <button
                onClick={() => setShowDeleteModal(true)}
                disabled={actionLoading}
                className="btn-secondary-link"
                style={{
                  border: '1px solid #fecaca',
                  backgroundColor: '#fef2f2',
                  color: '#b91c1c',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                Delete Opportunity
              </button>
            </div>
          </div>
        </div>

        {/* BANNER NOTIFICATION */}
        {bannerMessage && (
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '20px',
              fontSize: '14px',
              backgroundColor: bannerMessage.type === 'success' ? '#ecfdf5' : '#fef2f2',
              color: bannerMessage.type === 'success' ? '#047857' : '#b91c1c',
              border: `1px solid ${bannerMessage.type === 'success' ? '#a7f3d0' : '#fecaca'}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>{bannerMessage.text}</span>
            <button
              onClick={() => setBannerMessage(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontWeight: 'bold' }}
            >
              ×
            </button>
          </div>
        )}

        {/* SUB NAVIGATION TABS */}
        <div className="discovery-tab-bar" style={{ marginBottom: '24px' }}>
          <button
            onClick={() => setActiveTab('overview')}
            className={`discovery-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          >
            Overview & Details
          </button>
          <button
            onClick={() => setActiveTab('applicants')}
            className={`discovery-tab-btn ${activeTab === 'applicants' ? 'active' : ''}`}
          >
            Applicants ({opportunity.applicants_count ?? 0})
          </button>
          <button
            onClick={() => setActiveTab('edit')}
            className={`discovery-tab-btn ${activeTab === 'edit' ? 'active' : ''}`}
          >
            Edit Listing
          </button>
        </div>

        {/* TAB CONTENTS */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
            {/* LEFT SPEC CARD */}
            <div
              className="dashboard-stat-card"
              style={{ padding: '24px', backgroundColor: 'var(--bg-surface)', borderRadius: '12px' }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>Listing Summary</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '14px' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>CATEGORY</span>
                  <strong>{opportunity.category?.replace('_', ' ').toUpperCase()}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>WORK MODE</span>
                  <strong style={{ textTransform: 'capitalize' }}>{opportunity.work_mode || 'Remote'}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>COMPENSATION</span>
                  <strong>{formatPay()}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>VACANCIES</span>
                  <strong>{opportunity.vacancies || 1} open slot(s)</strong>
                </div>
                {opportunity.deadline && (
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>DEADLINE</span>
                    <strong>{new Date(opportunity.deadline).toLocaleDateString()}</strong>
                  </div>
                )}
                {opportunity.city && (
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>LOCATION</span>
                    <strong>{opportunity.city} {opportunity.location_text ? `(${opportunity.location_text})` : ''}</strong>
                  </div>
                )}
                {opportunity.duration && (
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>DURATION</span>
                    <strong>{opportunity.duration}</strong>
                  </div>
                )}
                {opportunity.working_hours && (
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>WORKING HOURS</span>
                    <strong>{opportunity.working_hours}</strong>
                  </div>
                )}
              </div>
            </div>

            {/* RIGHT DETAILS CARD */}
            <div
              className="dashboard-stat-card"
              style={{ gridColumn: 'span 2', padding: '24px', backgroundColor: 'var(--bg-surface)', borderRadius: '12px' }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>Description & Requirements</h3>
              <div style={{ whiteSpace: 'pre-line', fontSize: '14px', lineHeight: '1.6', color: 'var(--text-main)', marginBottom: '24px' }}>
                {opportunity.description}
              </div>

              {opportunity.required_skills && opportunity.required_skills.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: '700', marginBottom: '10px' }}>Required Skills</h4>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {opportunity.required_skills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="skill-tag"
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '13px',
                          backgroundColor: 'var(--bg-surface-secondary)',
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {opportunity.contact_info && (
                <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: '700', marginBottom: '4px' }}>Contact Information</h4>
                  <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>{opportunity.contact_info}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'applicants' && (
          <div>
            <ApplicantsView selectedOpportunity={opportunity} />
          </div>
        )}

        {activeTab === 'edit' && (
          <div>
            <PostOpportunity initialData={opportunity} onSuccess={handleEditSuccess} />
          </div>
        )}

        {/* DELETE CONFIRMATION MODAL */}
        {showDeleteModal && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(15, 23, 42, 0.6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
            }}
          >
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderRadius: '12px',
                padding: '28px',
                maxWidth: '440px',
                width: '90%',
                boxShadow: 'var(--shadow-modal)',
              }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '800', color: '#b91c1c', marginBottom: '12px' }}>
                Delete Opportunity Listing?
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px', lineHeight: '1.5' }}>
                Are you sure you want to delete <strong>"{opportunity.title}"</strong>? This will permanently remove the listing and all associated applicant data. This action cannot be undone.
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  onClick={() => setShowDeleteModal(false)}
                  disabled={actionLoading}
                  className="btn-secondary-link"
                  style={{ border: '1px solid var(--border-color)', padding: '8px 16px', borderRadius: '8px' }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  disabled={actionLoading}
                  style={{
                    backgroundColor: '#dc2626',
                    color: '#ffffff',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontWeight: '700',
                    cursor: 'pointer',
                  }}
                >
                  {actionLoading ? 'Deleting...' : 'Delete Permanently'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
