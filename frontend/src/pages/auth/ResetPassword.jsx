import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get('uid');
  const token = searchParams.get('token');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'success' | 'error', text: string }

  const hasParams = Boolean(uid && token);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!hasParams) return;

    if (newPassword !== confirmPassword) {
      setStatus({
        type: 'error',
        text: 'New password and confirmation do not match.',
      });
      return;
    }

    setStatus(null);
    setLoading(true);

    try {
      const data = await authService.resetPassword(uid, token, newPassword, confirmPassword);
      setStatus({
        type: 'success',
        text: data.message || 'Your password has been reset successfully! You can now log in with your new password.',
      });
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setStatus({
        type: 'error',
        text: err.message || 'Invalid or expired password reset link. Please request a new reset link.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Reset Password"
      subtitle={hasParams ? "Set a new password for your account." : "Invalid Reset Link"}
    >
      {!hasParams ? (
        <div style={{ textAlign: 'center' }}>
          <div className="alert-banner alert-error" style={{ marginBottom: '20px' }}>
            Invalid or missing password reset link parameters (uid and token are required).
          </div>
          <Link to="/forgot-password" className="link-primary">
            Request a new password reset link
          </Link>
        </div>
      ) : status?.type === 'success' ? (
        <div style={{ textAlign: 'center' }}>
          <div className="alert-banner alert-success" style={{ marginBottom: '24px' }}>
            {status.text}
          </div>
          <button
            type="button"
            className="btn-primary"
            onClick={() => navigate('/login')}
          >
            Continue to Login
          </button>
        </div>
      ) : (
        <>
          {status?.type === 'error' && (
            <div className="alert-banner alert-error" style={{ marginBottom: '20px' }}>
              {status.text}
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="new_password">New Password</label>
              <input
                id="new_password"
                type="password"
                className="form-input"
                placeholder="Enter new password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirm_password">Confirm New Password</label>
              <input
                id="confirm_password"
                type="password"
                className="form-input"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Resetting Password...' : 'Reset Password'}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Remembered your password?{' '}
              <Link to="/login" className="link-primary">
                Back to Login
              </Link>
            </p>
          </div>
        </>
      )}
    </AuthLayout>
  );
}
