import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import AuthLayout from '../../components/auth/AuthLayout';
import { authService } from '../../services/authService';

export default function InvitePage() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [valid, setValid] = useState(false);
  const [inviterName, setInviterName] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    async function checkInvitation() {
      if (!token) {
        setValid(false);
        setErrorMsg('No invitation token provided.');
        setLoading(false);
        return;
      }

      try {
        const data = await authService.getInvitation(token);
        if (data && data.valid && data.inviter) {
          setValid(true);
          setInviterName(data.inviter.full_name || 'A NextGig user');
        } else {
          setValid(false);
          setErrorMsg(data.detail || 'This invitation link is invalid or has expired.');
        }
      } catch (err) {
        setValid(false);
        setErrorMsg(err.message || 'Unable to verify invitation link.');
      } finally {
        setLoading(false);
      }
    }

    checkInvitation();
  }, [token]);

  const handleJoin = () => {
    navigate(`/register?invite=${encodeURIComponent(token)}`);
  };

  return (
    <AuthLayout
      title="You've Been Invited!"
      subtitle="Join NextGig to access opportunities and workspace tools"
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '32px 0' }}>
          <p style={{ color: 'var(--text-secondary, #94a3b8)' }}>Verifying invitation link...</p>
        </div>
      ) : valid ? (
        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <div
            style={{
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              borderRadius: '12px',
              padding: '24px 16px',
              marginBottom: '24px',
            }}
          >
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '8px', color: '#fff' }}>
              Welcome to NextGig
            </h3>
            <p style={{ color: 'var(--text-secondary, #cbd5e1)', fontSize: '0.95rem' }}>
              <strong>{inviterName}</strong> invited you to join the NextGig platform.
            </p>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={handleJoin}
            style={{ width: '100%', marginBottom: '16px' }}
          >
            Join NextGig
          </button>
        </div>
      ) : (
        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <div className="alert-banner alert-error" style={{ marginBottom: '24px' }}>
            {errorMsg}
          </div>

          <p style={{ color: 'var(--text-secondary, #cbd5e1)', marginBottom: '20px', fontSize: '0.9rem' }}>
            You can still create an account on NextGig to explore available opportunities.
          </p>

          <Link to="/register" className="btn-primary" style={{ display: 'block', textDecoration: 'none' }}>
            Go to Registration
          </Link>
        </div>
      )}
    </AuthLayout>
  );
}
