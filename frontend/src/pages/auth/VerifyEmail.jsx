import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get('uid');
  const token = searchParams.get('token');

  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null); // { type: 'success' | 'error', text: string }

  // Use a ref to prevent double API invocation in React 18 StrictMode
  const verificationAttempted = useRef(false);

  useEffect(() => {
    if (verificationAttempted.current) return;
    verificationAttempted.current = true;

    if (!uid || !token) {
      setLoading(false);
      setStatus({
        type: 'error',
        text: 'Invalid verification link. Please check the link or request a new verification email.',
      });
      return;
    }

    const performVerification = async () => {
      setLoading(true);
      try {
        const data = await authService.verifyEmail(uid, token);
        setStatus({
          type: 'success',
          text: data.message || 'Email verified successfully! You can now log in to your NextGig account.',
        });
      } catch (err) {
        console.error('[VerifyEmail] performVerification error:', err);
        setStatus({
          type: 'error',
          text: err.message || 'Invalid or expired verification link. Please request a new verification link.',
        });
      } finally {
        setLoading(false);
      }
    };

    performVerification();
  }, [uid, token]);

  return (
    <AuthLayout
      title="Email Verification"
      subtitle={loading ? "Verifying your email address..." : status?.type === 'success' ? "Verification Complete" : "Verification Failed"}
    >
      <div style={{ textAlign: 'center', padding: '8px 0' }}>
        {loading && (
          <div style={{ margin: '20px 0' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '15px' }}>
              Please wait while we verify your email credentials...
            </p>
          </div>
        )}

        {!loading && status && (
          <>
            <div className={`alert-banner alert-${status.type}`} style={{ marginBottom: '24px' }}>
              {status.text}
            </div>

            {status.type === 'success' ? (
              <button
                type="button"
                className="btn-primary"
                onClick={() => navigate('/login')}
              >
                Continue to Login
              </button>
            ) : (
              <div style={{ marginTop: '16px' }}>
                <Link to="/login" className="link-primary">
                  Back to Login
                </Link>
              </div>
            )}
          </>
        )}
      </div>
    </AuthLayout>
  );
}
