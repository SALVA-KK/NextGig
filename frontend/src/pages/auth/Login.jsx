import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function Login() {
  // Method state: 'email' | 'phone'
  const [method, setMethod] = useState('email');

  // Email form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  // Phone form state
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);

  // Status message state for UI feedback
  const [message, setMessage] = useState(null);

  // Handle tab switching
  const handleMethodChange = (newMethod) => {
    setMethod(newMethod);
    setMessage(null);
  };

  // Real Email Login Handler via Django REST API
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    setLoading(true);

    try {
      const data = await authService.loginEmail(email, password);
      setMessage({
        type: 'success',
        text: data.message || 'Login successful! Welcome back.',
      });
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Invalid email or password.',
      });
    } finally {
      setLoading(false);
    }
  };

  // Simulated Send OTP Handler (Phone OTP API integration pending)
  const handleSendOtp = (e) => {
    e.preventDefault();
    if (!phone.trim()) return;
    setOtpSent(true);
    setMessage({
      type: 'success',
      text: `[Demo] OTP sent to ${phone}. Enter 6-digit code below.`,
    });
  };

  // Simulated Verify OTP & Login Handler (Phone OTP API integration pending)
  const handleVerifyOtp = (e) => {
    e.preventDefault();
    setMessage({
      type: 'info',
      text: `[Demo] Verifying OTP ${otp} for ${phone}...`,
    });
  };

  // Reset OTP state to re-enter phone
  const handleResetPhone = () => {
    setOtpSent(false);
    setOtp('');
    setMessage(null);
  };

  return (
    <AuthLayout
      title="Welcome Back"
      subtitle="Sign in to access your NextGig workspace"
    >
      {/* Login Method Toggle (Email / Phone) */}
      <div className="auth-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={method === 'email'}
          className={`tab-btn ${method === 'email' ? 'active' : ''}`}
          onClick={() => handleMethodChange('email')}
        >
          Email
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={method === 'phone'}
          className={`tab-btn ${method === 'phone' ? 'active' : ''}`}
          onClick={() => handleMethodChange('phone')}
        >
          Phone Number
        </button>
      </div>

      {/* Feedback Banner */}
      {message && (
        <div className={`alert-banner alert-${message.type}`}>
          {message.text}
        </div>
      )}

      {/* METHOD 1: EMAIL & PASSWORD */}
      {method === 'email' && (
        <form onSubmit={handleEmailSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              className={`form-input ${loading ? 'disabled' : ''}`}
            />
          </div>

          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="password">Password</label>
              <Link to="/forgot-password" className="link-secondary">
                Forgot password?
              </Link>
            </div>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              className={`form-input ${loading ? 'disabled' : ''}`}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In with Email'}
          </button>
        </form>
      )}

      {/* METHOD 2: PHONE & OTP */}
      {method === 'phone' && (
        <div className="auth-form-wrapper">
          {!otpSent ? (
            /* STEP 1: Enter Phone Number & Send OTP */
            <form onSubmit={handleSendOtp} className="auth-form">
              <div className="form-group">
                <label htmlFor="phone">Phone Number</label>
                <input
                  id="phone"
                  type="tel"
                  placeholder="+91 98765 43210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                  className="form-input"
                />
              </div>

              <button type="submit" className="btn-primary">
                Send OTP
              </button>
            </form>
          ) : (
            /* STEP 2: Enter 6-Digit OTP & Verify */
            <form onSubmit={handleVerifyOtp} className="auth-form">
              <div className="form-group">
                <div className="form-label-row">
                  <label htmlFor="phone-disabled">Phone Number</label>
                  <button
                    type="button"
                    onClick={handleResetPhone}
                    className="link-secondary"
                  >
                    Change Phone
                  </button>
                </div>
                <input
                  id="phone-disabled"
                  type="tel"
                  value={phone}
                  disabled
                  className="form-input disabled"
                />
              </div>

              <div className="form-group">
                <label htmlFor="otp">6-Digit OTP Code</label>
                <input
                  id="otp"
                  type="text"
                  maxLength={6}
                  placeholder="123456"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  required
                  className="form-input otp-input"
                />
              </div>

              <button type="submit" className="btn-primary">
                Verify OTP & Sign In
              </button>

              <div className="resend-wrapper">
                <button
                  type="button"
                  onClick={handleSendOtp}
                  className="btn-text"
                >
                  Resend OTP
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Footer Link to Registration */}
      <div className="auth-footer">
        Don't have an account?{' '}
        <Link to="/register" className="link-primary">
          Create one now
        </Link>
      </div>
    </AuthLayout>
  );
}
