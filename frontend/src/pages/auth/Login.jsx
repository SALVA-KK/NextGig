import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function Login() {
  const navigate = useNavigate();

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
  const [phoneLoading, setPhoneLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  // Status message state for UI feedback
  const [message, setMessage] = useState(null);

  // 15-second resend cooldown timer with automatic cleanup
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  // Handle tab switching
  const handleMethodChange = (newMethod) => {
    setMethod(newMethod);
    setMessage(null);
  };

  // Helper to redirect based on user role
  const redirectBasedOnRole = (userData) => {
    const role = userData?.role || authService.getUserRole();
    if (role === 'admin') {
      navigate('/admin');
    } else {
      navigate('/dashboard');
    }
  };

  // Real Email Login Handler via Django REST API
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    setLoading(true);

    try {
      const data = await authService.loginEmail(email, password);
      if (data.mfa_required && data.mfa_token) {
        sessionStorage.setItem('admin_mfa_token', data.mfa_token);
        navigate('/admin/mfa-verify');
        return;
      }
      setMessage({
        type: 'success',
        text: data.message || 'Login successful! Welcome back.',
      });
      redirectBasedOnRole(data.user);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Invalid email or password.',
      });
    } finally {
      setLoading(false);
    }
  };

  // Real Phone Login Request OTP Handler via Django REST API
  const handleSendOtp = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    // Synchronous request guard: prevent duplicate calls while loading or during cooldown
    if (phoneLoading || cooldown > 0 || !phone.trim()) return;

    setMessage(null);
    setPhoneLoading(true);

    try {
      const data = await authService.requestPhoneLoginOTP(phone.trim());
      setOtpSent(true);
      setCooldown(15);
      setMessage({
        type: 'success',
        text: data.message || 'If the phone number is registered, an OTP has been sent.',
      });
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Failed to send OTP. Please check the phone number.',
      });
    } finally {
      setPhoneLoading(false);
    }
  };

  // Real Phone Login Verify OTP Handler via Django REST API
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otp.trim()) return;

    setMessage(null);
    setPhoneLoading(true);

    try {
      const data = await authService.verifyPhoneLoginOTP(phone.trim(), otp.trim());
      setMessage({
        type: 'success',
        text: 'Phone login successful! Welcome back.',
      });
      redirectBasedOnRole(data?.user);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Invalid or expired OTP.',
      });
    } finally {
      setPhoneLoading(false);
    }
  };

  // Reset OTP state to re-enter phone number
  const handleResetPhone = () => {
    setOtpSent(false);
    setOtp('');
    setCooldown(0);
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
                  disabled={phoneLoading}
                  className={`form-input ${phoneLoading ? 'disabled' : ''}`}
                />
              </div>

              <button type="submit" className="btn-primary" disabled={phoneLoading || cooldown > 0}>
                {phoneLoading ? 'Sending OTP...' : cooldown > 0 ? `Resend in ${cooldown}s` : 'Send OTP'}
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
                    disabled={phoneLoading}
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
                  disabled={phoneLoading}
                  className={`form-input otp-input ${phoneLoading ? 'disabled' : ''}`}
                />
              </div>

              <button type="submit" className="btn-primary" disabled={phoneLoading}>
                {phoneLoading ? 'Verifying...' : 'Verify OTP & Sign In'}
              </button>

              <div className="resend-wrapper">
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={phoneLoading || cooldown > 0}
                  className="btn-text"
                >
                  {cooldown > 0 ? `Resend OTP (${cooldown}s)` : 'Resend OTP'}
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
