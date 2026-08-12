import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: string }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;

    setMessage(null);
    setLoading(true);

    try {
      const data = await authService.forgotPassword(email.trim());
      setMessage({
        type: 'success',
        text: data.message || 'If an account with that email exists, a password reset link has been sent to your inbox.',
      });
      setEmail('');
    } catch (err) {
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
