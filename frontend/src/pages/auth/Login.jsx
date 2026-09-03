import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';
import { auth } from '../../firebase';
import { RecaptchaVerifier, signInWithPhoneNumber } from 'firebase/auth';
import { GoogleLogin } from '@react-oauth/google';
import { useGoogleReCaptcha } from 'react-google-recaptcha-v3';
import { getReCaptchaToken } from '../../utils/recaptcha';

export default function Login() {
  const navigate = useNavigate();
  const { executeRecaptcha } = useGoogleReCaptcha();

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
  const [confirmationResult, setConfirmationResult] = useState(null);

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

  // Auto-redirect already-authenticated users away from /login
  useEffect(() => {
    if (authService.isAuthenticated()) {
      const role = authService.getUserRole();
      if (role === 'admin') {
        navigate('/admin', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    }
  }, [navigate]);

  // Clean up RecaptchaVerifier on unmount
  useEffect(() => {
    return () => {
      if (window.recaptchaVerifier) {
        try {
          window.recaptchaVerifier.clear();
        } catch (e) {
          // ignore
        }
        window.recaptchaVerifier = null;
      }
    };
  }, []);

  // Handle tab switching
  const handleMethodChange = (newMethod) => {
    setMethod(newMethod);
    setMessage(null);
  };

  // Helper to redirect based on user role
  const redirectBasedOnRole = (user) => {
    const role = user?.role || authService.getUserRole();
    console.log('[LOGIN DIAGNOSTIC] redirectBasedOnRole computed role:', role);
    if (role === 'admin') {
      console.log('[LOGIN DIAGNOSTIC] Navigating to /admin with replace: true');
      navigate('/admin', { replace: true });
    } else {
      console.log('[LOGIN DIAGNOSTIC] Navigating to /dashboard with replace: true');
      navigate('/dashboard', { replace: true });
    }
  };

  // Google OAuth Login Handler
  const handleGoogleSuccess = async (credentialResponse) => {
    if (!credentialResponse?.credential) return;
    setMessage(null);
    setLoading(true);

    try {
      const data = await authService.loginGoogle(credentialResponse.credential);
      if (data.mfa_required && data.mfa_token) {
        sessionStorage.setItem('admin_mfa_token', data.mfa_token);
        navigate('/admin/mfa-verify', { replace: true });
        return;
      }
      setMessage({
        type: 'success',
        text: 'Google login successful! Redirecting...',
      });
      redirectBasedOnRole(data?.user);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Google authentication failed.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleError = () => {
    setMessage({
      type: 'error',
      text: 'Google sign-in was cancelled or failed.',
    });
  };

  // Real Email Login Handler via Django REST API
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    setMessage(null);
    setLoading(true);

    try {
      const recaptchaToken = await getReCaptchaToken(executeRecaptcha, 'login');
      if (!recaptchaToken) {
        setMessage({
          type: 'error',
          text: 'Verification is taking longer than expected — please refresh and try again.',
        });
        setLoading(false);
        return;
      }

      const data = await authService.loginEmail(email.trim(), password, recaptchaToken);
      console.log('[LOGIN DIAGNOSTIC] handleEmailSubmit success response:', data);

      if (data?.mfa_required && data?.mfa_token) {
        console.log('[LOGIN DIAGNOSTIC] MFA required for admin login. Navigating to /admin/mfa-verify');
        sessionStorage.setItem('admin_mfa_token', data.mfa_token);
        navigate('/admin/mfa-verify', { replace: true });
        return;
      }

      setMessage({
        type: 'success',
        text: 'Login successful! Redirecting...',
      });

      console.log('[LOGIN DIAGNOSTIC] Executing redirectBasedOnRole with user:', data?.user);
      redirectBasedOnRole(data?.user);
    } catch (err) {
      console.error('[LOGIN DIAGNOSTIC] handleEmailSubmit caught error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Login failed. Please check your credentials.',
      });
    } finally {
      setLoading(false);
    }
  };

  // Firebase Phone Login Request OTP Handler
  const handleSendOtp = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (phoneLoading || cooldown > 0 || !phone.trim()) return;

    setMessage(null);
    setPhoneLoading(true);

    try {
      let formattedPhone = phone.trim();
      if (!formattedPhone.startsWith('+')) {
        const digits = formattedPhone.replace(/\D/g, '');
        formattedPhone = digits.length === 10 ? `+91${digits}` : `+${digits}`;
      }

      if (!window.recaptchaVerifier) {
        window.recaptchaVerifier = new RecaptchaVerifier(auth, 'recaptcha-container', {
          size: 'invisible',
          callback: () => {},
        });
      }

      const confirmation = await signInWithPhoneNumber(auth, formattedPhone, window.recaptchaVerifier);
      setConfirmationResult(confirmation);
      setOtpSent(true);
      setCooldown(15);
      setMessage({
        type: 'success',
        text: 'Firebase SMS OTP dispatched to your phone.',
      });
    } catch (err) {
      if (window.recaptchaVerifier) {
        try {
          window.recaptchaVerifier.clear();
        } catch (clearErr) {
          // ignore
        }
        window.recaptchaVerifier = null;
      }
      setMessage({
        type: 'error',
        text: err.message || 'Failed to send SMS OTP via Firebase. Please check phone format or try again.',
      });
    } finally {
      setPhoneLoading(false);
    }
  };

  // Firebase Phone Login Verify OTP Handler
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otp.trim()) return;

    setMessage(null);
    setPhoneLoading(true);

    try {
      let idToken = null;
      if (confirmationResult) {
        const userCredential = await confirmationResult.confirm(otp.trim());
        idToken = await userCredential.user.getIdToken();
      }

      const data = await authService.verifyPhoneLoginOTP(
        idToken || phone.trim(),
        idToken ? null : otp.trim()
      );

      if (data.mfa_required && data.mfa_token) {
        sessionStorage.setItem('admin_mfa_token', data.mfa_token);
        navigate('/admin/mfa-verify', { replace: true });
        return;
      }

      setMessage({
        type: 'success',
        text: 'Phone login successful! Welcome back.',
      });
      redirectBasedOnRole(data?.user);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Invalid or expired OTP token.',
      });
    } finally {
      setPhoneLoading(false);
    }
  };

  // Reset OTP state to re-enter phone number
  const handleResetPhone = () => {
    setOtpSent(false);
    setOtp('');
    setConfirmationResult(null);
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

      {/* Google OAuth Login Section */}
      <div className="google-login-section" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '16px 0 20px 0' }}>
        <GoogleLogin
          onSuccess={handleGoogleSuccess}
          onError={handleGoogleError}
          shape="pill"
          text="signin_with"
        />
        <div style={{ display: 'flex', alignItems: 'center', width: '100%', margin: '16px 0 4px 0', color: '#9ca3af', fontSize: '0.85rem' }}>
          <div style={{ flex: 1, height: '1px', backgroundColor: '#e5e7eb' }}></div>
          <span style={{ padding: '0 12px' }}>or continue with</span>
          <div style={{ flex: 1, height: '1px', backgroundColor: '#e5e7eb' }}></div>
        </div>
      </div>

      {/* METHOD 1: EMAIL & PASSWORD */}
      {method === 'email' && (
        <form onSubmit={handleEmailSubmit} className="auth-form" noValidate>
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
            <form onSubmit={handleSendOtp} className="auth-form" noValidate>
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

              <div id="recaptcha-container"></div>

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
