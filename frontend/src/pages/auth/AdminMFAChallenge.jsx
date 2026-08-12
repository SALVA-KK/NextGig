import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function AdminMFAChallenge() {
  const navigate = useNavigate();
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const isSuccessRef = useRef(false);

  const mfaToken = sessionStorage.getItem('admin_mfa_token');

  useEffect(() => {
    if (!mfaToken && !isSuccessRef.current) {
      navigate('/login');
    }
  }, [mfaToken, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!otpCode.trim()) return;

    setMessage(null);
    setLoading(true);

    try {
      await authService.verifyAdminMFA(mfaToken, otpCode.trim());
      isSuccessRef.current = true;
      sessionStorage.removeItem('admin_mfa_token');
      navigate('/admin');
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Invalid verification code or recovery code.',
      });
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Admin MFA Security Check"
      subtitle="Enter the 6-digit code from your authenticator app (or 8-character recovery code)"
    >
      {message && (
        <div className={`alert-banner ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="otpCode" className="form-label">
            Authenticator / Recovery Code
          </label>
          <input
            id="otpCode"
            type="text"
            className="form-input"
            placeholder="123456 or Backup Code"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value)}
            required
            autoFocus
            maxLength={12}
            style={{ textAlign: 'center', letterSpacing: '2px', fontSize: '1.2rem' }}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Verifying MFA...' : 'Authenticate & Continue'}
        </button>
      </form>

      <div className="auth-footer">
        <p>
          <Link to="/login" onClick={() => sessionStorage.removeItem('admin_mfa_token')} className="link-primary">
            Cancel & Return to Login
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
