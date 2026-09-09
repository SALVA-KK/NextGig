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
      console.error('[InviteCard] handleGenerateInvite error:', err);
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
      console.error('[InviteCard] handleCopyLink error:', err);
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
      console.error('[InviteCard] handleShareLink error:', err);
      // User cancelled share or browser error
    }
  };

  return (
    <div className="invite-card-container">
      {error && (
        <div className="alert-banner alert-error" style={{ marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {!inviteUrl ? (
        <div>
          <button
            type="button"
            className="btn-primary"
            onClick={handleGenerateInvite}
            disabled={loading}
            style={{ width: 'auto', padding: '10px 24px' }}
          >
            {loading ? 'Generating Link...' : 'Generate Invite Link'}
          </button>
        </div>
      ) : (
        <div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '8px', fontWeight: '500' }}>
              Your Invitation Link:
            </label>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                readOnly
                value={inviteUrl}
                className="form-input"
                style={{
                  flex: 1,
                  minWidth: '260px',
                  fontSize: '0.9rem',
                  fontFamily: 'monospace',
                  padding: '10px 14px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  borderRadius: '8px',
                }}
              />
              <button
                type="button"
                className="btn-primary"
                onClick={handleCopyLink}
                style={{ width: 'auto', padding: '10px 20px', whiteSpace: 'nowrap' }}
              >
                {copySuccess ? 'Copied!' : 'Copy Link'}
              </button>

              {typeof navigator !== 'undefined' && navigator.share && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleShareLink}
                  style={{ width: 'auto', padding: '10px 20px', whiteSpace: 'nowrap' }}
                >
                  Share
                </button>
              )}
            </div>
          </div>

          {copySuccess && (
            <p style={{ color: '#4ade80', fontSize: '0.85rem', marginTop: '6px', fontWeight: '500' }}>
              Invitation link copied to clipboard!
            </p>
          )}

          <div style={{ marginTop: '12px' }}>
            <button
              type="button"
              className="btn-text"
              onClick={handleGenerateInvite}
              disabled={loading}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: '0.85rem',
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
