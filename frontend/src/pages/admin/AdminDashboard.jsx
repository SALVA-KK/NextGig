import React, { useState, useEffect } from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import ChangePasswordCard from '../../components/profile/ChangePasswordCard';
import PaginationControl from '../../components/common/PaginationControl';
import { adminService } from '../../services/adminService';
import { authService } from '../../services/authService';

export default function AdminDashboard() {
  const currentUser = authService.getCurrentUser();
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'providers' | 'users' | 'opportunities'

  // Provider Verification state
  const [pendingProviders, setPendingProviders] = useState([]);
  const [providersLoading, setProvidersLoading] = useState(false);
  const [providersPage, setProvidersPage] = useState(1);
  const [providersTotalCount, setProvidersTotalCount] = useState(0);
  const [selectedProviderToVerify, setSelectedProviderToVerify] = useState(null);

  // User Management state
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersPage, setUsersPage] = useState(1);
  const [usersTotalCount, setUsersTotalCount] = useState(0);
  const [userRoleFilter, setUserRoleFilter] = useState('');
  const [userSearchQuery, setUserSearchQuery] = useState('');

  // Opportunity Moderation state
  const [opportunities, setOpportunities] = useState([]);
  const [oppsLoading, setOppsLoading] = useState(false);
  const [oppsPage, setOppsPage] = useState(1);
  const [oppsTotalCount, setOppsTotalCount] = useState(0);
  const [oppStatusFilter, setOppStatusFilter] = useState('');
  const [oppSearchQuery, setOppSearchQuery] = useState('');
  const [selectedOppToDelete, setSelectedOppToDelete] = useState(null);

  // Audit Log state
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotalCount, setAuditTotalCount] = useState(0);

  // Common Feedback State
  const [bannerMessage, setBannerMessage] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Load Pending Providers
  const loadPendingProviders = async () => {
    setProvidersLoading(true);
    try {
      const data = await adminService.getPendingProviders({ page: providersPage });
      setPendingProviders(data.results || []);
      setProvidersTotalCount(data.count ?? data.results.length);
    } catch (err) {
      console.error('Error loading pending providers:', err);
    } finally {
      setProvidersLoading(false);
    }
  };

  // Load Users
  const loadUsers = async () => {
    setUsersLoading(true);
    try {
      const data = await adminService.getUsers({
        page: usersPage,
        role: userRoleFilter || undefined,
        search: userSearchQuery || undefined,
      });
      setUsers(data.results || []);
      setUsersTotalCount(data.count ?? data.results.length);
    } catch (err) {
      console.error('Error loading users:', err);
    } finally {
      setUsersLoading(false);
    }
  };

  // Load Opportunities
  const loadOpportunities = async () => {
    setOppsLoading(true);
    try {
      const data = await adminService.getOpportunities({
        page: oppsPage,
        status: oppStatusFilter || undefined,
        search: oppSearchQuery || undefined,
      });
      setOpportunities(data.results || []);
      setOppsTotalCount(data.count ?? data.results.length);
    } catch (err) {
      console.error('Error loading opportunities:', err);
    } finally {
      setOppsLoading(false);
    }
  };

  // Load Audit Logs
  const loadAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const data = await adminService.getAuditLog({ page: auditPage });
      setAuditLogs(data.results || []);
      setAuditTotalCount(data.count ?? data.results.length);
    } catch (err) {
      console.error('Error loading audit log:', err);
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'providers') {
      loadPendingProviders();
    } else if (activeTab === 'users') {
      loadUsers();
    } else if (activeTab === 'opportunities') {
      loadOpportunities();
    } else if (activeTab === 'audit') {
      loadAuditLogs();
    }
  }, [activeTab, providersPage, usersPage, userRoleFilter, userSearchQuery, oppsPage, oppStatusFilter, oppSearchQuery, auditPage]);

  // Actions
  const handleConfirmVerifyProvider = async () => {
    if (!selectedProviderToVerify) return;
    setActionLoading(true);
    try {
      await adminService.verifyProvider(selectedProviderToVerify.id, true);
      setBannerMessage({
        type: 'success',
        text: `Provider "${selectedProviderToVerify.organization_name}" verified successfully!`,
      });
      setSelectedProviderToVerify(null);
      await loadPendingProviders();
    } catch (err) {
      console.error('Error verifying provider:', err);
      setBannerMessage({ type: 'error', text: 'Failed to verify provider profile.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleUserActive = async (targetUser) => {
    if (targetUser.id === currentUser?.id) {
      setBannerMessage({ type: 'error', text: 'You cannot deactivate your own admin account.' });
      return;
    }
    setActionLoading(true);
    try {
      const res = await adminService.toggleUserActive(targetUser.id);
      setBannerMessage({
        type: 'success',
        text: `User account for ${targetUser.email} is now ${res.is_active ? 'Active' : 'Deactivated'}.`,
      });
      setUsers((prev) =>
        prev.map((u) => (u.id === targetUser.id ? { ...u, is_active: res.is_active } : u))
      );
    } catch (err) {
      console.error('Error toggling user active status:', err);
      const msg = err.response?.data?.detail || 'Failed to update user status.';
      setBannerMessage({ type: 'error', text: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleForceCloseOpp = async (opp) => {
    setActionLoading(true);
    try {
      await adminService.forceCloseOpportunity(opp.id);
      setBannerMessage({
        type: 'success',
        text: `Opportunity "${opp.title}" has been force-closed.`,
      });
      setOpportunities((prev) =>
        prev.map((o) => (o.id === opp.id ? { ...o, status: 'closed' } : o))
      );
    } catch (err) {
      console.error('Error force-closing opportunity:', err);
      setBannerMessage({ type: 'error', text: 'Failed to force-close opportunity.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReopenOpp = async (opp) => {
    setActionLoading(true);
    try {
      await adminService.reopenOpportunity(opp.id);
      setBannerMessage({
        type: 'success',
        text: `Opportunity "${opp.title}" has been reopened.`,
      });
      setOpportunities((prev) =>
        prev.map((o) => (o.id === opp.id ? { ...o, status: 'open', close_reason: null, closed_by: null } : o))
      );
    } catch (err) {
      console.error('Error reopening opportunity:', err);
      setBannerMessage({ type: 'error', text: 'Failed to reopen opportunity.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDeleteOpp = async () => {
    if (!selectedOppToDelete) return;
    setActionLoading(true);
    try {
      await adminService.deleteOpportunity(selectedOppToDelete.id);
      setBannerMessage({
        type: 'success',
        text: `Opportunity "${selectedOppToDelete.title}" deleted by admin moderation.`,
      });
      setSelectedOppToDelete(null);
      await loadOpportunities();
    } catch (err) {
      console.error('Error deleting opportunity:', err);
      setBannerMessage({ type: 'error', text: 'Failed to delete opportunity.' });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <DashboardLayout title="Admin Control Panel">
      <div className="discovery-container">
        
        {/* HEADER INTRO */}
        <div className="dashboard-welcome-section" style={{ marginBottom: '20px' }}>
          <div className="hero-badge">ADMIN CONTROL PANEL</div>
          <h2 style={{ fontSize: '24px', fontWeight: '800', marginTop: '6px' }}>System Oversight & Moderation</h2>
          <p className="subtitle">
            Manage provider organization verifications, user accounts, and platform opportunity listings.
          </p>
        </div>

        {/* FEEDBACK BANNER */}
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

        {/* TABS BAR */}
        <div className="discovery-tab-bar" style={{ marginBottom: '24px' }}>
          <button
            onClick={() => setActiveTab('overview')}
            className={`discovery-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          >
            Overview & Status
          </button>
          <button
            onClick={() => setActiveTab('providers')}
            className={`discovery-tab-btn ${activeTab === 'providers' ? 'active' : ''}`}
          >
            Provider Verification
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`discovery-tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          >
            User Management
          </button>
          <button
            onClick={() => setActiveTab('opportunities')}
            className={`discovery-tab-btn ${activeTab === 'opportunities' ? 'active' : ''}`}
          >
            Opportunity Moderation
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`discovery-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          >
            Audit Trail
          </button>
        </div>

        {/* TAB 1: OVERVIEW & STATUS */}
        {activeTab === 'overview' && (
          <div>
            <div className="dashboard-cards-grid" style={{ marginBottom: '24px' }}>
              <div className="dashboard-stat-card">
                <div className="stat-card-header">
                  <span className="stat-label">Account Status</span>
                  <span className="status-badge enabled">Active</span>
                </div>
                <p className="stat-value">{currentUser?.full_name || currentUser?.email}</p>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Role: Administrator
                </p>
              </div>

              <div className="dashboard-stat-card">
                <div className="stat-card-header">
                  <span className="stat-label">MFA Status</span>
                  <span className="status-badge enabled">Active</span>
                </div>
                <p className="stat-value">Multi-Factor Auth Enforced</p>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Admin endpoints protected
                </p>
              </div>
            </div>

            <ChangePasswordCard />
          </div>
        )}

        {/* TAB 2: PROVIDER VERIFICATION */}
        {activeTab === 'providers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Pending Provider Organizations</h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                Review unverified provider registrations and grant official organization verification.
              </p>
            </div>

            {providersLoading ? (
              <div className="discovery-loading">Loading pending providers...</div>
            ) : pendingProviders.length === 0 ? (
              <div
                className="dashboard-stat-card"
                style={{ textAlign: 'center', padding: '48px 24px', background: 'var(--bg-surface)' }}
              >
                <div style={{ fontSize: '36px', marginBottom: '12px' }}>✅</div>
                <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '4px' }}>No Pending Verifications</h3>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                  All provider organization profiles are currently verified.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {pendingProviders.map((profile) => (
                  <div
                    key={profile.id}
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
                        <h4 style={{ fontSize: '18px', fontWeight: '700' }}>{profile.organization_name}</h4>
                        <span className="status-badge pending">UNVERIFIED</span>
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                        <span><strong>Type:</strong> {profile.organization_type}</span>
                        <span><strong>Owner:</strong> {profile.owner_full_name} ({profile.owner_email})</span>
                        <span><strong>Submitted:</strong> {new Date(profile.created_at).toLocaleDateString()}</span>
                      </div>
                      {profile.description && (
                        <p style={{ fontSize: '13px', color: 'var(--text-main)', marginTop: '8px' }}>
                          {profile.description}
                        </p>
                      )}
                    </div>

                    <div>
                      <button
                        onClick={() => setSelectedProviderToVerify(profile)}
                        className="btn-primary-sm"
                        style={{ backgroundColor: '#059669', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}
                      >
                        Approve & Verify
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!providersLoading && (
              <PaginationControl
                currentPage={providersPage}
                totalItems={providersTotalCount}
                pageSize={20}
                onPageChange={(newPage) => setProvidersPage(newPage)}
              />
            )}
          </div>
        )}

        {/* TAB 3: USER MANAGEMENT */}
        {activeTab === 'users' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: '700' }}>User Accounts Registry</h3>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                  Inspect all platform accounts, filter by role, or toggle active account status.
                </p>
              </div>

              {/* FILTERS */}
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <select
                  value={userRoleFilter}
                  onChange={(e) => {
                    setUserRoleFilter(e.target.value);
                    setUsersPage(1);
                  }}
                  className="select-filter"
                  style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                >
                  <option value="">All Roles</option>
                  <option value="student">Student</option>
                  <option value="provider">Provider</option>
                  <option value="admin">Admin</option>
                </select>

                <input
                  type="text"
                  placeholder="Search email or name..."
                  value={userSearchQuery}
                  onChange={(e) => {
                    setUserSearchQuery(e.target.value);
                    setUsersPage(1);
                  }}
                  className="form-input"
                  style={{ width: '220px', padding: '8px 12px' }}
                />
              </div>
            </div>

            {usersLoading ? (
              <div className="discovery-loading">Loading user registry...</div>
            ) : (
              <div style={{ overflowX: 'auto', backgroundColor: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--bg-surface-secondary)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase' }}>
                      <th style={{ padding: '12px 16px' }}>User Details</th>
                      <th style={{ padding: '12px 16px' }}>Role</th>
                      <th style={{ padding: '12px 16px' }}>Status</th>
                      <th style={{ padding: '12px 16px' }}>Joined Date</th>
                      <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => {
                      const isSelf = u.id === currentUser?.id;
                      return (
                        <tr key={u.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ fontWeight: '700', color: 'var(--text-main)' }}>{u.full_name || 'No Name'}</div>
                            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{u.email}</div>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            <span className="status-badge" style={{ textTransform: 'uppercase', fontSize: '11px' }}>
                              {u.role}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            <span className={`status-badge ${u.is_active ? 'enabled' : 'pending'}`}>
                              {u.is_active ? 'ACTIVE' : 'INACTIVE'}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '13px' }}>
                            {new Date(u.date_joined).toLocaleDateString()}
                          </td>
                          <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                            {isSelf ? (
                              <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>Current User</span>
                            ) : (
                              <button
                                onClick={() => handleToggleUserActive(u)}
                                disabled={actionLoading}
                                className="btn-secondary-link"
                                style={{
                                  padding: '6px 12px',
                                  borderRadius: '6px',
                                  border: `1px solid ${u.is_active ? '#fecaca' : '#a7f3d0'}`,
                                  color: u.is_active ? '#b91c1c' : '#047857',
                                  backgroundColor: u.is_active ? '#fef2f2' : '#ecfdf5',
                                  cursor: 'pointer',
                                  fontWeight: '600',
                                }}
                              >
                                {u.is_active ? 'Deactivate' : 'Activate'}
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {!usersLoading && (
              <PaginationControl
                currentPage={usersPage}
                totalItems={usersTotalCount}
                pageSize={20}
                onPageChange={(newPage) => setUsersPage(newPage)}
              />
            )}
          </div>
        )}

        {/* TAB 4: OPPORTUNITY MODERATION */}
        {activeTab === 'opportunities' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Opportunity Moderation Feed</h3>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                  Monitor all platform opportunities, force-close expired listings, or delete policy-violating content.
                </p>
              </div>

              {/* FILTERS */}
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <select
                  value={oppStatusFilter}
                  onChange={(e) => {
                    setOppStatusFilter(e.target.value);
                    setOppsPage(1);
                  }}
                  className="select-filter"
                  style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                >
                  <option value="">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="closed">Closed</option>
                  <option value="draft">Draft</option>
                </select>

                <input
                  type="text"
                  placeholder="Search by title..."
                  value={oppSearchQuery}
                  onChange={(e) => {
                    setOppSearchQuery(e.target.value);
                    setOppsPage(1);
                  }}
                  className="form-input"
                  style={{ width: '220px', padding: '8px 12px' }}
                />
              </div>
            </div>

            {oppsLoading ? (
              <div className="discovery-loading">Loading opportunities for moderation...</div>
            ) : (
              <div style={{ overflowX: 'auto', backgroundColor: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--bg-surface-secondary)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase' }}>
                      <th style={{ padding: '12px 16px' }}>Opportunity Title</th>
                      <th style={{ padding: '12px 16px' }}>Poster</th>
                      <th style={{ padding: '12px 16px' }}>Status</th>
                      <th style={{ padding: '12px 16px' }}>Applicants</th>
                      <th style={{ padding: '12px 16px' }}>Posted Date</th>
                      <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunities.map((opp) => (
                      <tr key={opp.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontWeight: '700', color: 'var(--text-main)' }}>{opp.title}</div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{opp.category?.replace('_', ' ')}</div>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <div>{opp.poster?.full_name || 'Partner'}</div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{opp.poster?.email}</div>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span className={`status-badge ${opp.status === 'open' ? 'enabled' : 'pending'}`}>
                            {opp.status?.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', fontWeight: '600' }}>
                          {opp.applicants_count ?? 0}
                        </td>
                        <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '13px' }}>
                          {new Date(opp.created_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                            {opp.status !== 'closed' ? (
                              <button
                                onClick={() => handleForceCloseOpp(opp)}
                                disabled={actionLoading}
                                className="btn-secondary-link"
                                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', fontSize: '13px' }}
                              >
                                Force Close
                              </button>
                            ) : (
                              <button
                                onClick={() => handleReopenOpp(opp)}
                                disabled={actionLoading}
                                className="btn-secondary-link"
                                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #a7f3d0', backgroundColor: '#ecfdf5', color: '#047857', fontSize: '13px' }}
                              >
                                Reopen
                              </button>
                            )}
                            <button
                              onClick={() => setSelectedOppToDelete(opp)}
                              disabled={actionLoading}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                border: '1px solid #fecaca',
                                backgroundColor: '#fef2f2',
                                color: '#b91c1c',
                                fontWeight: '600',
                                fontSize: '13px',
                                cursor: 'pointer',
                              }}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {oppsTotalCount > 20 && (
              <PaginationControl
                currentPage={oppsPage}
                totalItems={oppsTotalCount}
                pageSize={20}
                onPageChange={(newPage) => setOppsPage(newPage)}
              />
            )}
          </div>
        )}

        {/* TAB 5: AUDIT TRAIL */}
        {activeTab === 'audit' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Administrative Audit Log</h3>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Total Action Records: {auditTotalCount}
              </span>
            </div>

            <div className="table-responsive">
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Admin Email</th>
                    <th>Action</th>
                    <th>Target Details</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLoading ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '24px' }}>Loading audit logs...</td>
                    </tr>
                  ) : auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                        No administrative actions recorded yet.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td style={{ fontSize: '13px', whiteSpace: 'nowrap' }}>
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td style={{ fontWeight: '600' }}>{log.admin_email}</td>
                        <td>
                          <span
                            className="status-badge"
                            style={{
                              backgroundColor: log.action_type.includes('verified') || log.action_type.includes('activated') ? '#ecfdf5' : '#fef2f2',
                              color: log.action_type.includes('verified') || log.action_type.includes('activated') ? '#047857' : '#b91c1c',
                              fontSize: '12px',
                            }}
                          >
                            {log.action_type_display}
                          </span>
                        </td>
                        <td style={{ fontSize: '13px' }}>{log.target_description}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {auditTotalCount > 20 && (
              <PaginationControl
                currentPage={auditPage}
                totalItems={auditTotalCount}
                pageSize={20}
                onPageChange={(newPage) => setAuditPage(newPage)}
              />
            )}
          </div>
        )}

        {/* VERIFY PROVIDER MODAL */}
        {selectedProviderToVerify && (
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
              <h3 style={{ fontSize: '18px', fontWeight: '800', color: '#047857', marginBottom: '12px' }}>
                Verify Provider Organization?
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px', lineHeight: '1.5' }}>
                Are you sure you want to verify <strong>"{selectedProviderToVerify.organization_name}"</strong> ({selectedProviderToVerify.owner_email})? This will mark the organization as officially verified on NextGig.
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  onClick={() => setSelectedProviderToVerify(null)}
                  disabled={actionLoading}
                  className="btn-secondary-link"
                  style={{ border: '1px solid var(--border-color)', padding: '8px 16px', borderRadius: '8px' }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmVerifyProvider}
                  disabled={actionLoading}
                  style={{
                    backgroundColor: '#059669',
                    color: '#ffffff',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontWeight: '700',
                    cursor: 'pointer',
                  }}
                >
                  {actionLoading ? 'Verifying...' : 'Approve & Verify'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* DELETE OPPORTUNITY MODAL */}
        {selectedOppToDelete && (
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
                Moderation Delete Opportunity?
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px', lineHeight: '1.5' }}>
                Are you sure you want to delete <strong>"{selectedOppToDelete.title}"</strong>? This action is permanent and cannot be undone.
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  onClick={() => setSelectedOppToDelete(null)}
                  disabled={actionLoading}
                  className="btn-secondary-link"
                  style={{ border: '1px solid var(--border-color)', padding: '8px 16px', borderRadius: '8px' }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDeleteOpp}
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
