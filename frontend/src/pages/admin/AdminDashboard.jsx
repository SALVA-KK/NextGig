import React, { useState, useEffect } from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import ChangePasswordCard from '../../components/profile/ChangePasswordCard';
import PaginationControl from '../../components/common/PaginationControl';
import { adminService } from '../../services/adminService';
import { authService } from '../../services/authService';

export default function AdminDashboard() {
  const currentUser = authService.getCurrentUser();
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'providers' | 'users' | 'opportunities' | 'audit' | 'overview'

  // Platform Dashboard Summary state
  const [dashboardSummary, setDashboardSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

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

  // User Detail Drilldown & Delete Modal state
  const [selectedUserDetail, setSelectedUserDetail] = useState(null);
  const [userDetailLoading, setUserDetailLoading] = useState(false);
  const [showDeleteConfirmModal, setShowDeleteConfirmModal] = useState(false);
  const [confirmEmailInput, setConfirmEmailInput] = useState('');
  const [modalErrorMessage, setModalErrorMessage] = useState(null);

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

  // Admin MFA State
  const [mfaEnabled, setMfaEnabled] = useState(false);

  // Common Feedback State
  const [bannerMessage, setBannerMessage] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Load Dashboard Summary
  const loadDashboardSummary = async () => {
    setSummaryLoading(true);
    try {
      const data = await adminService.getDashboardSummary();
      setDashboardSummary(data);
    } catch (err) {
      console.error('Error loading dashboard summary:', err);
    } finally {
      setSummaryLoading(false);
    }
  };

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
    if (activeTab === 'dashboard') {
      loadDashboardSummary();
    } else if (activeTab === 'overview') {
      authService.getAdminMFAStatus()
        .then((res) => setMfaEnabled(Boolean(res?.is_enabled)))
        .catch((err) => console.error('Error loading MFA status:', err));
    } else if (activeTab === 'providers') {
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

  const handleViewUserDetail = async (user) => {
    setUserDetailLoading(true);
    setModalErrorMessage(null);
    try {
      const detail = await adminService.getUserDetail(user.id);
      setSelectedUserDetail(detail);
    } catch (err) {
      console.error('Error fetching user detail:', err);
      setBannerMessage({ type: 'error', text: 'Failed to fetch user details.' });
    } finally {
      setUserDetailLoading(false);
    }
  };

  const handleForceCloseOpp = async (opp) => {
    const oppId = typeof opp === 'object' ? opp.id : opp;
    const oppTitle = typeof opp === 'object' && opp.title ? opp.title : `Opportunity #${oppId}`;
    setActionLoading(true);
    try {
      await adminService.forceCloseOpportunity(oppId);
      setBannerMessage({
        type: 'success',
        text: `Opportunity "${oppTitle}" has been force-closed.`,
      });
      setOpportunities((prev) =>
        prev.map((o) => (o.id === oppId ? { ...o, status: 'closed' } : o))
      );
      if (selectedUserDetail) {
        setSelectedUserDetail((prev) =>
          prev
            ? {
                ...prev,
                opportunities: prev.opportunities?.map((o) => (o.id === oppId ? { ...o, status: 'closed' } : o)),
              }
            : null
        );
      }
    } catch (err) {
      console.error('Error force-closing opportunity:', err);
      setBannerMessage({ type: 'error', text: 'Failed to force-close opportunity.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDeleteUser = async () => {
    if (!selectedUserDetail) return;
    setActionLoading(true);
    setModalErrorMessage(null);
    try {
      await adminService.deleteUser(selectedUserDetail.id);
      setBannerMessage({
        type: 'success',
        text: `User account for ${selectedUserDetail.email} permanently deleted.`,
      });
      setShowDeleteConfirmModal(false);
      setSelectedUserDetail(null);
      setConfirmEmailInput('');
      await loadUsers();
    } catch (err) {
      console.error('Error deleting user:', err);
      const msg = err.response?.data?.detail || 'Failed to delete user account.';
      setModalErrorMessage(msg);
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
    <DashboardLayout activeTab={activeTab} setActiveTab={setActiveTab}>
      <div className="discovery-container">
        
        {/* HEADER INTRO */}
        <div className="dashboard-welcome-section" style={{ marginBottom: '20px' }}>
          <div className="hero-badge">ADMIN CONTROL PANEL</div>
          <h2 style={{ fontSize: '24px', fontWeight: '800', marginTop: '6px' }}>System Oversight & Moderation</h2>
          <p className="subtitle">
            Platform metrics, provider verifications, user management, and moderation controls.
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

        {/* TAB 0: PLATFORM DASHBOARD SUMMARY */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {summaryLoading ? (
              <div className="discovery-loading">Loading platform dashboard summary...</div>
            ) : dashboardSummary ? (
              <>
                {/* Metric Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Students Metric Card */}
                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Students</span>
                    <div className="text-2xl font-extrabold text-slate-900 mt-1">{dashboardSummary.total_students}</div>
                    <div className="flex gap-2 text-xs font-medium text-slate-500 mt-2">
                      <span className="text-emerald-600 font-semibold">{dashboardSummary.active_students} Active</span>
                      <span>•</span>
                      <span className="text-amber-600">{dashboardSummary.inactive_students} Inactive</span>
                    </div>
                  </div>

                  {/* Providers Metric Card */}
                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Providers</span>
                    <div className="text-2xl font-extrabold text-slate-900 mt-1">{dashboardSummary.total_providers}</div>
                    <div className="flex gap-2 text-xs font-medium text-slate-500 mt-2">
                      <span className="text-emerald-600 font-semibold">{dashboardSummary.active_providers} Active</span>
                      <span>•</span>
                      <span className="text-amber-600">{dashboardSummary.inactive_providers} Inactive</span>
                    </div>
                  </div>

                  {/* Opportunities Metric Card */}
                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Opportunities</span>
                    <div className="text-2xl font-extrabold text-slate-900 mt-1">
                      {dashboardSummary.total_opportunities_open + dashboardSummary.total_opportunities_closed}
                    </div>
                    <div className="flex gap-2 text-xs font-medium text-slate-500 mt-2">
                      <span className="text-indigo-600 font-semibold">{dashboardSummary.total_opportunities_open} Open</span>
                      <span>•</span>
                      <span className="text-slate-500">{dashboardSummary.total_opportunities_closed} Closed</span>
                    </div>
                  </div>

                  {/* Applications Metric Card */}
                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Applications</span>
                    <div className="text-2xl font-extrabold text-slate-900 mt-1">{dashboardSummary.total_applications}</div>
                    <div className="text-xs font-semibold text-emerald-600 mt-2">
                      +{dashboardSummary.applications_this_week} this week
                    </div>
                  </div>
                </div>

                {/* Secondary Row: Verifications & Signups */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200 flex justify-between items-center">
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Pending Provider Verifications</div>
                      <div className="text-xl font-bold text-slate-900 mt-1">{dashboardSummary.pending_provider_verifications_count}</div>
                    </div>
                    <button
                      onClick={() => setActiveTab('providers')}
                      className="px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
                    >
                      Review →
                    </button>
                  </div>

                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200 flex justify-between items-center">
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-500">New Providers (Last 7 Days)</div>
                      <div className="text-xl font-bold text-slate-900 mt-1">{dashboardSummary.new_provider_signups_last_7_days_count}</div>
                    </div>
                    <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
                      Recent Signups
                    </span>
                  </div>
                </div>

                {/* Categories Breakdown */}
                {dashboardSummary.opportunities_by_category && (
                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Opportunities by Category</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(dashboardSummary.opportunities_by_category).map(([cat, count]) => (
                        <span key={cat} className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-medium">
                          <strong className="text-slate-900">{cat.replace('_', ' ')}:</strong> {count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Administrative Actions Table */}
                <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200 space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Recent Administrative Actions</h4>
                    <button
                      onClick={() => setActiveTab('audit')}
                      className="text-xs font-bold text-indigo-600 hover:text-indigo-700"
                    >
                      View Full Audit Trail →
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase">
                          <th className="py-2.5 px-3">Time</th>
                          <th className="py-2.5 px-3">Admin</th>
                          <th className="py-2.5 px-3">Action</th>
                          <th className="py-2.5 px-3">Target</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {dashboardSummary.recent_admin_actions?.length === 0 ? (
                          <tr>
                            <td colSpan="4" className="py-4 text-center text-slate-500">No recent actions recorded.</td>
                          </tr>
                        ) : (
                          dashboardSummary.recent_admin_actions?.map((log) => (
                            <tr key={log.id} className="hover:bg-slate-50/50">
                              <td className="py-2.5 px-3 text-slate-500 whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</td>
                              <td className="py-2.5 px-3 font-semibold text-slate-800">{log.admin_email}</td>
                              <td className="py-2.5 px-3">
                                <span className="px-2 py-0.5 rounded-full font-bold uppercase text-[10px] bg-indigo-50 text-indigo-700 border border-indigo-200">
                                  {log.action_type_display || log.action_type}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-slate-600 max-w-xs truncate">{log.target_description}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            ) : null}
          </div>
        )}

        {/* TAB 1: OVERVIEW & STATUS */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Account Status Card */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Account Status</span>
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Active
                  </span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900">{currentUser?.full_name || 'System Administrator'}</h3>
                  <p className="text-sm font-medium text-slate-600">{currentUser?.email}</p>
                </div>
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-medium">
                  <span>Role: Administrator</span>
                  <span>Platform Superuser</span>
                </div>
              </div>

              {/* MFA Status Card */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">MFA Protection</span>
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                    mfaEnabled
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${mfaEnabled ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    {mfaEnabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900">
                    {mfaEnabled ? 'Multi-Factor Auth Active' : 'Multi-Factor Auth Optional'}
                  </h3>
                  <p className="text-sm font-medium text-slate-600">
                    {mfaEnabled
                      ? 'Admin endpoints protected via TOTP authenticator app.'
                      : 'Enhanced security available for administrative account.'}
                  </p>
                </div>
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-medium">
                  <span className="text-slate-500">Status: {mfaEnabled ? 'Enforced' : 'Not setup'}</span>
                  <a href="/admin/mfa-setup" className="font-bold text-indigo-600 hover:text-indigo-700">
                    {mfaEnabled ? 'Manage MFA' : 'Setup MFA'} →
                  </a>
                </div>
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
                            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', alignItems: 'center' }}>
                              <button
                                onClick={() => handleViewUserDetail(u)}
                                disabled={userDetailLoading}
                                style={{
                                  padding: '6px 12px',
                                  borderRadius: '6px',
                                  border: '1px solid #cbd5e1',
                                  backgroundColor: '#f8fafc',
                                  color: '#334155',
                                  fontWeight: '600',
                                  fontSize: '12px',
                                  cursor: 'pointer',
                                }}
                              >
                                View
                              </button>

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
                                    fontSize: '12px',
                                  }}
                                >
                                  {u.is_active ? 'Deactivate' : 'Activate'}
                                </button>
                              )}
                            </div>
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
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Administrative Audit Log</h3>
                <p className="text-xs text-slate-500">Immutable system action logs for compliance and security auditing.</p>
              </div>
              <span className="text-xs font-bold text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                Total Records: {auditTotalCount}
              </span>
            </div>

            {auditLoading ? (
              <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 text-slate-500 font-medium">
                Loading audit logs...
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs font-bold uppercase tracking-wider">
                      <th className="px-6 py-4">Timestamp</th>
                      <th className="px-6 py-4">Admin Email</th>
                      <th className="px-6 py-4">Action</th>
                      <th className="px-6 py-4">Target Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {auditLogs.length === 0 ? (
                      <tr>
                        <td colSpan="4" className="px-6 py-12 text-center text-slate-500 font-medium">
                          No administrative actions recorded yet.
                        </td>
                      </tr>
                    ) : (
                      auditLogs.map((log) => {
                        const isPositive = log.action_type.includes('verified') || log.action_type.includes('activated') || log.action_type.includes('create') || log.action_type.includes('reopen');
                        return (
                          <tr key={log.id} className="hover:bg-slate-50/50 transition-colors">
                            <td className="px-6 py-4 text-xs font-semibold text-slate-600 whitespace-nowrap">
                              {new Date(log.timestamp).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 font-bold text-slate-900">
                              {log.admin_email}
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                                  isPositive
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : 'bg-amber-50 text-amber-800 border-amber-200'
                                }`}
                              >
                                {log.action_type_display || log.action_type}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-xs text-slate-700 font-medium">
                              {log.target_description}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {!auditLoading && auditTotalCount > 20 && (
              <PaginationControl
                currentPage={auditPage}
                totalItems={auditTotalCount}
                pageSize={20}
                onPageChange={(newPage) => setAuditPage(newPage)}
              />
            )}
          </div>
        )}

        {/* USER DETAIL MODAL */}
        {selectedUserDetail && (
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
              padding: '16px',
            }}
          >
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderRadius: '16px',
                padding: '24px',
                maxWidth: '640px',
                width: '100%',
                maxHeight: '90vh',
                overflowY: 'auto',
                boxShadow: 'var(--shadow-modal)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--text-main)' }}>
                    {selectedUserDetail.full_name || 'User Profile'}
                  </h3>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{selectedUserDetail.email}</div>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className="status-badge" style={{ textTransform: 'uppercase' }}>{selectedUserDetail.role}</span>
                  <span className={`status-badge ${selectedUserDetail.is_active ? 'enabled' : 'pending'}`}>
                    {selectedUserDetail.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                  <button
                    onClick={() => setSelectedUserDetail(null)}
                    style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: 'var(--text-muted)' }}
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* Profile Overview Card */}
              <div style={{ backgroundColor: 'var(--bg-surface-secondary)', padding: '16px', borderRadius: '12px', marginBottom: '20px', fontSize: '13px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                  <div><strong>User ID:</strong> #{selectedUserDetail.id}</div>
                  <div><strong>Date Joined:</strong> {new Date(selectedUserDetail.date_joined).toLocaleDateString()}</div>
                  <div>
                    <strong>Phone Number:</strong>{' '}
                    {selectedUserDetail.phone_number ? (
                      <span style={{ color: '#047857', fontWeight: '600' }}>{selectedUserDetail.phone_number}</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided or opted out</span>
                    )}
                  </div>
                  <div>
                    <strong>WhatsApp Number:</strong>{' '}
                    {selectedUserDetail.whatsapp_number ? (
                      <span style={{ color: '#047857', fontWeight: '600' }}>{selectedUserDetail.whatsapp_number}</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided or opted out</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Provider Opportunities List */}
              {selectedUserDetail.role === 'provider' && (
                <div style={{ marginBottom: '20px' }}>
                  <h4 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px' }}>
                    Posted Opportunities ({selectedUserDetail.opportunities?.length || 0})
                  </h4>
                  {selectedUserDetail.opportunities?.length === 0 ? (
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>No opportunities posted yet.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {selectedUserDetail.opportunities.map((opp) => (
                        <div
                          key={opp.id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px 14px',
                            borderRadius: '8px',
                            border: '1px solid var(--border-color)',
                            backgroundColor: 'var(--bg-surface)',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: '600', fontSize: '14px' }}>{opp.title}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                              Status: <strong style={{ textTransform: 'uppercase' }}>{opp.status}</strong> • {opp.applicants_count} Applicants
                            </div>
                          </div>
                          {opp.status !== 'closed' && (
                            <button
                              onClick={() => handleForceCloseOpp(opp)}
                              disabled={actionLoading}
                              style={{
                                padding: '4px 10px',
                                borderRadius: '6px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: '#fef2f2',
                                color: '#b91c1c',
                                fontSize: '12px',
                                fontWeight: '600',
                                cursor: 'pointer',
                              }}
                            >
                              Force Close
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Student Applications List (View-Only) */}
              {selectedUserDetail.role === 'student' && (
                <div style={{ marginBottom: '20px' }}>
                  <h4 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px' }}>
                    Submitted Applications ({selectedUserDetail.applications?.length || 0})
                  </h4>
                  {selectedUserDetail.applications?.length === 0 ? (
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>No applications submitted yet.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {selectedUserDetail.applications.map((app) => (
                        <div
                          key={app.id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px 14px',
                            borderRadius: '8px',
                            border: '1px solid var(--border-color)',
                            backgroundColor: 'var(--bg-surface)',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: '600', fontSize: '14px' }}>{app.opportunity_title}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                              Applied: {new Date(app.applied_at).toLocaleDateString()}
                            </div>
                          </div>
                          <span className="status-badge" style={{ textTransform: 'uppercase', fontSize: '11px' }}>
                            {app.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Modal Footer Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                <button
                  onClick={() => {
                    setShowDeleteConfirmModal(true);
                    setConfirmEmailInput('');
                    setModalErrorMessage(null);
                  }}
                  style={{
                    backgroundColor: '#dc2626',
                    color: '#ffffff',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontWeight: '700',
                    fontSize: '13px',
                    cursor: 'pointer',
                  }}
                >
                  Delete Account
                </button>

                <button
                  onClick={() => setSelectedUserDetail(null)}
                  style={{
                    border: '1px solid var(--border-color)',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    backgroundColor: 'var(--bg-surface)',
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* DELETE ACCOUNT CONFIRMATION MODAL */}
        {showDeleteConfirmModal && selectedUserDetail && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(15, 23, 42, 0.75)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1100,
              padding: '16px',
            }}
          >
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderRadius: '16px',
                padding: '28px',
                maxWidth: '460px',
                width: '100%',
                boxShadow: 'var(--shadow-modal)',
              }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '800', color: '#b91c1c', marginBottom: '12px' }}>
                Permanently Delete User Account?
              </h3>
              
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: '1.5' }}>
                This action will <strong>permanently delete</strong> the account for{' '}
                <strong style={{ color: 'var(--text-main)' }}>{selectedUserDetail.email}</strong> and cascade delete all associated profile data, listings, and records. This action <strong>CANNOT BE UNDONE</strong>.
              </p>

              {modalErrorMessage && (
                <div style={{ padding: '10px 14px', borderRadius: '8px', backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '13px', marginBottom: '16px' }}>
                  {modalErrorMessage}
                </div>
              )}

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: 'var(--text-muted)', marginBottom: '6px' }}>
                  To confirm, type <strong>{selectedUserDetail.email}</strong> below:
                </label>
                <input
                  type="text"
                  value={confirmEmailInput}
                  onChange={(e) => setConfirmEmailInput(e.target.value)}
                  placeholder="Enter email to confirm..."
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  onClick={() => setShowDeleteConfirmModal(false)}
                  disabled={actionLoading}
                  style={{
                    border: '1px solid var(--border-color)',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    backgroundColor: 'var(--bg-surface)',
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDeleteUser}
                  disabled={actionLoading || confirmEmailInput.trim() !== selectedUserDetail.email}
                  style={{
                    backgroundColor: confirmEmailInput.trim() === selectedUserDetail.email ? '#dc2626' : '#fca5a5',
                    color: '#ffffff',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontWeight: '700',
                    fontSize: '13px',
                    cursor: confirmEmailInput.trim() === selectedUserDetail.email ? 'pointer' : 'not-allowed',
                  }}
                >
                  {actionLoading ? 'Deleting Account...' : 'Delete User Account'}
                </button>
              </div>
            </div>
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

