import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import { authService } from '../../services/authService';

export default function AdminMFASetup() {
  const navigate = useNavigate();
  const [statusLoading, setStatusLoading] = useState(true);
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [setupData, setSetupData] = useState(null);
  const [confirmCode, setConfirmCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    checkMFAStatus();
  }, []);

  const checkMFAStatus = async () => {
    setStatusLoading(true);
    try {
      const res = await authService.getAdminMFAStatus();
      setMfaEnabled(Boolean(res.is_enabled));
    } catch (err) {
      console.error('[AdminMFASetup] checkMFAStatus error:', err);
      setMfaEnabled(false);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleStartSetup = async () => {
    setMessage(null);
    setLoading(true);
    try {
      const data = await authService.setupAdminMFA();
      setSetupData(data);
    } catch (err) {
      console.error('[AdminMFASetup] handleStartSetup error:', err);
      setMessage({ type: 'error', text: err.message || 'Failed to start MFA setup.' });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmSetup = async (e) => {
    e.preventDefault();
    if (!confirmCode.trim()) return;

    setMessage(null);
    setLoading(true);

    try {
      const data = await authService.confirmAdminMFA(confirmCode.trim());
      setMessage({ type: 'success', text: data.message || 'MFA successfully activated!' });
      setMfaEnabled(true);
      setSetupData(null);
      setConfirmCode('');
    } catch (err) {
      console.error('[AdminMFASetup] handleConfirmSetup error:', err);
      setMessage({ type: 'error', text: err.message || 'Failed to confirm MFA code.' });
    } finally {
      setLoading(false);
    }
  };

  const handleDisableMFA = async (e) => {
    e.preventDefault();
    if (!disablePassword || !disableCode) return;

    setMessage(null);
    setLoading(true);

    try {
      const data = await authService.disableAdminMFA(disablePassword, disableCode);
      setMessage({ type: 'success', text: data.message || 'MFA has been disabled.' });
      setMfaEnabled(false);
      setDisablePassword('');
      setDisableCode('');
    } catch (err) {
      console.error('[AdminMFASetup] handleDisableMFA error:', err);
      setMessage({ type: 'error', text: err.message || 'Failed to disable MFA.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout title="Admin Security">
      <div className="discovery-container max-w-4xl mx-auto space-y-6">
        
        {/* TOP BAR / NAVIGATION */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Multi-Factor Authentication (TOTP)
            </h1>
            <p className="text-xs font-medium text-slate-600 mt-1">
              Secure your administrator account using Google Authenticator, Microsoft Authenticator, Authy, or 1Password.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/admin')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-white hover:bg-slate-50 text-slate-700 shadow-sm border border-slate-200 transition-all flex-shrink-0 self-start sm:self-auto"
          >
            ← Back to Admin Console
          </button>
        </div>

        {/* FEEDBACK ALERT */}
        {message && (
          <div
            className={`p-4 rounded-xl border text-xs font-semibold flex items-center justify-between ${
              message.type === 'error'
                ? 'bg-red-50 text-red-800 border-red-200'
                : 'bg-emerald-50 text-emerald-800 border-emerald-200'
            }`}
          >
            <span>{message.text}</span>
            <button
              onClick={() => setMessage(null)}
              className="text-base font-bold leading-none hover:opacity-75"
            >
              ×
            </button>
          </div>
        )}

        {statusLoading ? (
          <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200 text-center text-slate-500 font-medium text-xs">
            Checking MFA security status...
          </div>
        ) : mfaEnabled ? (
          /* MFA ACTIVE STATE */
          <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-6">
            <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">MFA Protection Active</h2>
                  <p className="text-xs font-medium text-slate-500">Logins require your password and a 6-digit TOTP authenticator code.</p>
                </div>
              </div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 flex-shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Active
              </span>
            </div>

            {/* DISABLE MFA COLLAPSIBLE */}
            <details className="group border border-slate-200 rounded-xl bg-slate-50/50 p-4 transition-all">
              <summary className="cursor-pointer text-xs font-bold text-red-600 hover:text-red-700 flex items-center justify-between select-none">
                <span>Disable Multi-Factor Authentication</span>
                <span className="text-xs font-normal text-slate-400 group-open:rotate-180 transition-transform">▼</span>
              </summary>

              <form onSubmit={handleDisableMFA} className="mt-4 pt-4 border-t border-slate-200 space-y-4">
                <p className="text-xs text-slate-600 font-medium">
                  Enter your current administrator password and a verification code to confirm disabling MFA.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                      Current Password
                    </label>
                    <input
                      type="password"
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-medium"
                      value={disablePassword}
                      onChange={(e) => setDisablePassword(e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                      Authenticator / Backup Code
                    </label>
                    <input
                      type="text"
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-medium tracking-wider text-center"
                      placeholder="123456"
                      value={disableCode}
                      onChange={(e) => setDisableCode(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-red-600 hover:bg-red-700 text-white shadow-sm transition-all disabled:opacity-50"
                  >
                    {loading ? 'Disabling MFA...' : 'Confirm & Disable MFA'}
                  </button>
                </div>
              </form>
            </details>
          </div>
        ) : setupData ? (
          /* MFA SETUP FLOW STEPS */
          <div className="space-y-6">

            {/* STEP 1: SCAN QR CODE */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-4 text-center">
              <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 mb-1">
                Step 1: Scan QR Code
              </div>
              <h2 className="text-lg font-extrabold text-slate-900">Scan QR Code</h2>
              <p className="text-xs font-medium text-slate-600 max-w-md mx-auto">
                Open Google Authenticator or Microsoft Authenticator on your mobile device and scan the code below:
              </p>

              {setupData.qr_code && (
                <div className="w-48 h-48 sm:w-52 sm:h-52 p-3 bg-white border border-slate-200 rounded-2xl shadow-sm flex items-center justify-center mx-auto my-3">
                  <img
                    src={setupData.qr_code}
                    alt="MFA Provisioning QR Code"
                    className="w-full h-full object-contain"
                  />
                </div>
              )}

              <div className="pt-1">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  Secret Key (Manual Entry):
                </span>
                <code className="inline-block bg-slate-50 border border-slate-200 px-4 py-2 rounded-xl text-indigo-700 font-mono text-sm font-bold tracking-widest shadow-xs">
                  {setupData.secret}
                </code>
              </div>
            </div>

            {/* STEP 2: EMERGENCY RECOVERY CODES */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-4">
              <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 mb-1">
                Step 2: Backup Codes
              </div>
              <h2 className="text-lg font-extrabold text-slate-900">Save Emergency Recovery Codes</h2>
              <p className="text-xs font-medium text-slate-600">
                Save these 8 emergency recovery codes in a secure location. Each code can be used <strong>once</strong> to log in if you lose access to your authenticator app.
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                {setupData.backup_codes?.map((code, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono text-slate-900 font-bold text-xs text-center tracking-wider shadow-xs select-all"
                  >
                    {code}
                  </div>
                ))}
              </div>
            </div>

            {/* STEP 3: VERIFY & ACTIVATE */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-4">
              <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 mb-1">
                Step 3: Verify Setup
              </div>
              <h2 className="text-lg font-extrabold text-slate-900">Enter Verification Code</h2>
              <p className="text-xs font-medium text-slate-600">
                Enter the 6-digit verification code generated by your authenticator app to activate MFA protection.
              </p>

              <form onSubmit={handleConfirmSetup} className="space-y-4 pt-2">
                <div className="max-w-xs mx-auto space-y-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block text-center">
                    6-Digit Code
                  </label>
                  <input
                    type="text"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-center font-mono font-bold text-lg tracking-widest text-slate-900"
                    placeholder="123456"
                    value={confirmCode}
                    onChange={(e) => setConfirmCode(e.target.value)}
                    required
                    maxLength={6}
                  />
                </div>

                <div className="text-center pt-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-8 py-3 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all disabled:opacity-50"
                  >
                    {loading ? 'Activating MFA...' : 'Confirm & Activate MFA'}
                  </button>
                </div>
              </form>
            </div>

          </div>
        ) : (
          /* UNCONFIGURED PROMPT */
          <div className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm border border-slate-200 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto border border-indigo-100">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>

            <div className="space-y-1">
              <h2 className="text-lg font-extrabold text-slate-900">MFA is Not Yet Enabled</h2>
              <p className="text-xs font-medium text-slate-600 max-w-md mx-auto">
                Enhance platform security by enabling Time-based One-Time Password (TOTP) Multi-Factor Authentication for your admin account.
              </p>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={handleStartSetup}
                disabled={loading}
                className="px-6 py-3 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all disabled:opacity-50"
              >
                {loading ? 'Generating Secret...' : 'Set Up Authenticator MFA'}
              </button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
