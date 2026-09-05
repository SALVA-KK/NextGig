import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
      setMfaEnabled(res.is_enabled);
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
    <div className="dashboard-container">
      <div className="dashboard-card" style={{ maxWidth: '800px' }}>
        {/* Header */}
        <div className="dashboard-header">
          <div className="auth-brand" style={{ marginBottom: 0 }}>
            <div className="brand-logo" style={{ background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' }}>A</div>
            <span className="brand-name">Admin Security</span>
          </div>
          <button onClick={() => navigate('/admin')} className="btn-logout" id="back-admin-btn">
            Back to Admin Console
          </button>
        </div>

        <div className="dashboard-welcome">
          <h1 className="dashboard-title">Multi-Factor Authentication (TOTP)</h1>
          <p className="dashboard-subtitle">
            Secure your administrator account using an authenticator app (Google Authenticator, Microsoft Authenticator, Authy, or 1Password).
          </p>
        </div>

        {message && (
          <div className={`alert-banner ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
            {message.text}
          </div>
        )}

        {statusLoading ? (
          <p className="dashboard-subtitle">Checking MFA status...</p>
        ) : mfaEnabled ? (
          /* MFA Active State */
          <div className="user-profile-card">
            <div className="user-profile-header">
              <span className="badge-authenticated" style={{ background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', border: '1px solid rgba(34, 197, 94, 0.3)' }}>
                ✓ MFA Currently Active
              </span>
            </div>
            <p style={{ fontSize: '0.9rem', color: '#9ca3af', marginTop: '12px', marginBottom: '20px' }}>
              Your admin account is protected with TOTP Multi-Factor Authentication. Every login requires your password and a 6-digit authenticator code.
            </p>

            <details style={{ marginTop: '16px' }}>
              <summary style={{ cursor: 'pointer', color: '#f87171', fontWeight: 500 }}>
                Disable Multi-Factor Authentication
              </summary>
              <form onSubmit={handleDisableMFA} className="auth-form" style={{ marginTop: '16px' }}>
                <div className="form-group">
                  <label className="form-label">Current Admin Password</label>
                  <input
                    type="password"
                    className="form-input"
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Authenticator / Backup Code</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="123456"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value)}
                    required
                  />
                </div>
                <button type="submit" className="btn-primary" style={{ background: '#dc2626' }} disabled={loading}>
                  {loading ? 'Disabling MFA...' : 'Confirm & Disable MFA'}
                </button>
              </form>
            </details>
          </div>
        ) : setupData ? (
          /* MFA Setup Step 2: QR Code & Confirmation */
          <div>
            <div className="user-profile-card" style={{ textAlign: 'center' }}>
              <h3 style={{ color: '#f3f4f6', marginBottom: '12px' }}>Step 1: Scan QR Code</h3>
              <p style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '16px' }}>
                Open Google Authenticator or Microsoft Authenticator on your mobile device and scan the QR code below:
              </p>

              {setupData.qr_code && (
                <div style={{ background: '#ffffff', padding: '16px', borderRadius: '12px', display: 'inline-block', marginBottom: '16px' }}>
                  <img src={setupData.qr_code} alt="MFA Provisioning QR Code" style={{ width: '180px', height: '180px' }} />
                </div>
              )}

              <div style={{ marginTop: '8px', marginBottom: '20px' }}>
                <span className="detail-label" style={{ display: 'block', marginBottom: '4px' }}>Secret Key (Manual Entry):</span>
                <code style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '6px 12px', borderRadius: '6px', color: '#fbbf24', letterSpacing: '2px', fontSize: '1.1rem' }}>
                  {setupData.secret}
                </code>
              </div>
            </div>

            {/* Step 2: Single-Use Backup Recovery Codes */}
            <div className="user-profile-card" style={{ marginTop: '20px' }}>
              <h3 style={{ color: '#f3f4f6', marginBottom: '8px' }}>Step 2: Save Emergency Recovery Codes</h3>
              <p style={{ fontSize: '0.85rem', color: '#9ca3af', marginBottom: '12px' }}>
                Save these 8 emergency recovery codes in a secure location. Each code can be used <strong>once</strong> to log in if you lose access to your phone or authenticator app:
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', background: 'rgba(0, 0, 0, 0.4)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                {setupData.backup_codes?.map((code, idx) => (
                  <code key={idx} style={{ color: '#60a5fa', fontWeight: 600, fontSize: '0.95rem' }}>{code}</code>
                ))}
              </div>
            </div>

            {/* Step 3: Confirm TOTP Code */}
            <form onSubmit={handleConfirmSetup} className="auth-form" style={{ marginTop: '20px' }}>
              <div className="form-group">
                <label className="form-label" style={{ fontSize: '1rem', fontWeight: 600 }}>
                  Step 3: Enter 6-Digit Verification Code to Activate
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="123456"
                  value={confirmCode}
                  onChange={(e) => setConfirmCode(e.target.value)}
                  required
                  maxLength={6}
                  style={{ textAlign: 'center', letterSpacing: '4px', fontSize: '1.2rem' }}
                />
              </div>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Activating MFA...' : 'Confirm & Activate MFA'}
              </button>
            </form>
          </div>
        ) : (
          /* MFA Setup Step 1: Start Setup Prompt */
          <div className="user-profile-card" style={{ textAlign: 'center', padding: '32px' }}>
            <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🔐</div>
            <h3 style={{ color: '#f3f4f6', marginBottom: '8px' }}>MFA is Not Yet Enabled</h3>
            <p style={{ fontSize: '0.9rem', color: '#9ca3af', maxWidth: '500px', margin: '0 auto 24px auto' }}>
              Enhance platform security by enabling Time-based One-Time Password (TOTP) Multi-Factor Authentication for your admin account.
            </p>
            <button onClick={handleStartSetup} className="btn-primary" style={{ maxWidth: '280px', margin: '0 auto' }} disabled={loading}>
              {loading ? 'Generating Secret...' : 'Set Up Authenticator MFA'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
