import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function Register() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteToken = searchParams.get('invite') || '';

  // Form state
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // UI state
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: string }
  const [registeredSuccess, setRegisteredSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setMessage(null);

    // Client-side validation for password match
    if (password !== confirmPassword) {
      setMessage({
        type: 'error',
        text: 'Passwords do not match. Please re-enter your passwords.',
      });
      setLoading(false);
      return;
    }

    try {
      const data = await authService.register({
        full_name: fullName.trim(),
        email: email.trim(),
        phone_number: phoneNumber.trim() || undefined,
        password,
        confirm_password: confirmPassword,
        invite_token: inviteToken || undefined,
      });

      setRegisteredSuccess(true);
      setMessage({
        type: 'success',
        text:
          data.message ||
          'Registration successful! Please check your email and verify your account before logging in.',
      });
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Registration failed. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create Account"
      subtitle="Join NextGig to access opportunities and workspace tools"
    >
      {/* Alert Banner */}
      {message && (
        <div className={`alert-banner alert-${message.type}`}>
          {message.text}
        </div>
      )}

      {registeredSuccess ? (
        /* Success View: Instruct user to check email and log in */
        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <button
            type="button"
            className="btn-primary"
            onClick={() => navigate('/login')}
          >
            Return to Login
          </button>
        </div>
      ) : (
        /* Registration Form */
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="fullName">Full Name</label>
            <input
              id="fullName"
              type="text"
              placeholder="Jane Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={loading}
              className={`form-input ${loading ? 'disabled' : ''}`}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              className={`form-input ${loading ? 'disabled' : ''}`}
            />
          </div>

          <div className="form-group">
            <label htmlFor="phoneNumber">Phone Number (Optional)</label>
            <input
              id="phoneNumber"
              type="tel"
              placeholder="+1 555 123 4567"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              disabled={loading}
              className={`form-input ${loading ? 'disabled' : ''}`}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className={`form-input ${loading ? 'disabled' : ''}`}
            />
            <small className="form-help-text" style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: '4px', display: 'block' }}>
              Password must be 8-128 characters long and include an uppercase letter, a lowercase letter, a number, and a special character (!@#$%^&*...).
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              className={`form-input ${loading ? 'disabled' : ''}`}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>
      )}

      {/* Footer Link to Login */}
      <div className="auth-footer">
        Already have an account?{' '}
        <Link to="/login" className="link-primary">
          Sign in
        </Link>
      </div>
    </AuthLayout>
  );
}
