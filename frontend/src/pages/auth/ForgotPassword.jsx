import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';
import { useGoogleReCaptcha } from 'react-google-recaptcha-v3';
import { getReCaptchaToken } from '../../utils/recaptcha';

export default function ForgotPassword() {
  const { executeRecaptcha } = useGoogleReCaptcha();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: string }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;

    setMessage(null);
    setLoading(true);

    try {
      const recaptchaToken = await getReCaptchaToken(executeRecaptcha, 'forgot_password');
      if (!recaptchaToken) {
        setMessage({
          type: 'error',
          text: 'Verification is taking longer than expected — please refresh and try again.',
        });
        setLoading(false);
        return;
      }

      const data = await authService.forgotPassword(email.trim(), recaptchaToken);
      setMessage({
        type: 'success',
        text: data.message || 'If an account with that email exists, a password reset link has been sent to your inbox.',
      });
      setEmail('');
    } catch (err) {
      console.error('[ForgotPassword] Submit error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Failed to request password reset. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Forgot Password"
      subtitle="Enter your registered email address to receive a secure password reset link."
    >
      {message && (
        <div className={`alert-banner alert-${message.type}`} style={{ marginBottom: '20px' }}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="email">Email Address</label>
          <input
            id="email"
            type="email"
            className="form-input"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Sending Instructions...' : 'Send Password Reset Link'}
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
    </AuthLayout>
  );
}
