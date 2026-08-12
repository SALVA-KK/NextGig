import React, { useState } from 'react';
import { authService } from '../../services/authService';

export default function InviteCard() {
  const [loading, setLoading] = useState(false);
  const [inviteUrl, setInviteUrl] = useState('');
  const [copySuccess, setCopySuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleGenerateInvite = async () => {
    setError(null);
    setCopySuccess(false);
    setLoading(true);

    try {
      const data = await authService.createInvitation();
      if (data && data.invite_url) {
        setInviteUrl(data.invite_url);
      } else {
        setError('Failed to generate invitation link.');
      }
    } catch (err) {
      setError(err.message || 'Error generating invitation link.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = async () => {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 3000);
    } catch (err) {
      setError('Failed to copy to clipboard.');
    }
  };

  const handleShareLink = async () => {
    if (!inviteUrl || !navigator.share) return;
    try {
      await navigator.share({
        title: 'NextGig Invitation',
        text: 'Join me on NextGig!',
        url: inviteUrl,
      });
    } catch (err) {
      // User cancelled share or browser error
    }
  };

  return (
    <div className="dashboard-stat-card" style={{ gridColumn: 'span 2' }}>
      <div className="stat-card-header" style={{ marginBottom: '12px' }}>
        <span className="stat-label" style={{ fontSize: '1rem', fontWeight: '600', color: '#fff' }}>
          Invite People
        </span>
        <span className="status-badge active">Platform Access</span>
      </div>

      <p className="subtitle" style={{ fontSize: '0.9rem', color: 'var(--text-secondary, #94a3b8)', marginBottom: '16px' }}>
        Generate a unique invitation link to invite friends or colleagues to join NextGig.
      </p>

      {error && (
        <div className="alert-banner alert-error" style={{ marginBottom: '16px', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {!inviteUrl ? (
        <button
          type="button"
          className="btn-primary"
          onClick={handleGenerateInvite}
          disabled={loading}
          style={{ width: 'auto', padding: '10px 20px' }}
        >
          {loading ? 'Generating Link...' : 'Generate Invite Link'}
        </button>
      ) : (
        <div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
              Your Invitation Link:
            </label>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                type="text"
                readOnly
                value={inviteUrl}
                className="form-input"
                style={{
                  flex: 1,
                  fontSize: '0.85rem',
                  fontFamily: 'monospace',
                  padding: '8px 12px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                }}
              />
              <button
                type="button"
                className="btn-primary"
                onClick={handleCopyLink}
                style={{ width: 'auto', padding: '8px 16px', whiteSpace: 'nowrap' }}
              >
                {copySuccess ? 'Copied!' : 'Copy Link'}
              </button>

              {typeof navigator !== 'undefined' && navigator.share && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleShareLink}
                  style={{
                    width: 'auto',
                    padding: '8px 16px',
                    whiteSpace: 'nowrap',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    color: '#fff',
                    borderRadius: '8px',
                    cursor: 'pointer',
                  }}
                >
                  Share
                </button>
              )}
            </div>
          </div>

          {copySuccess && (
            <p style={{ color: '#4ade80', fontSize: '0.85rem', marginTop: '6px' }}>
              ✓ Invitation link copied to clipboard!
            </p>
          )}

          <div style={{ marginTop: '12px' }}>
            <button
              type="button"
              onClick={handleGenerateInvite}
              disabled={loading}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: '0.8rem',
                textDecoration: 'underline',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              Generate new link
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
