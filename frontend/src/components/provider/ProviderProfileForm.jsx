import React, { useState, useEffect } from 'react';
import providerService from '../../services/providerService';

export default function ProviderProfileForm() {
  const [formData, setFormData] = useState({
    organization_name: '',
    organization_type: '',
    description: '',
    contact_person: '',
    website: '',
    address: '',
    city: '',
    is_verified: false,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: string }

  const loadProfile = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const data = await providerService.getProviderProfile();
      setFormData({
        organization_name: data.organization_name || '',
        organization_type: data.organization_type || '',
        description: data.description || '',
        contact_person: data.contact_person || '',
        website: data.website || '',
        address: data.address || '',
        city: data.city || '',
        is_verified: !!data.is_verified,
      });
    } catch (err) {
      console.error('Error loading provider profile:', err);
      setMessage({ type: 'error', text: 'Failed to load provider profile. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const updated = await providerService.updateProviderProfile({
        organization_name: formData.organization_name,
        organization_type: formData.organization_type,
        description: formData.description,
        contact_person: formData.contact_person,
        website: formData.website,
        address: formData.address,
        city: formData.city,
      });
      setFormData((prev) => ({
        ...prev,
        ...updated,
      }));
      setMessage({ type: 'success', text: 'Provider profile updated successfully!' });
    } catch (err) {
      console.error('Error updating provider profile:', err);
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to update provider profile. Please check your inputs.',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="discovery-loading">Loading provider profile...</div>;
  }

  return (
    <div className="auth-card" style={{ maxWidth: '720px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Organization / Provider Profile</h2>
        <span className={`status-badge ${formData.is_verified ? 'enabled' : 'pending'}`}>
          {formData.is_verified ? 'Verified Provider' : 'Unverified Provider'}
        </span>
      </div>

      {message && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            fontSize: '14px',
            backgroundColor: message.type === 'success' ? '#ecfdf5' : '#fef2f2',
            color: message.type === 'success' ? '#047857' : '#b91c1c',
            border: `1px solid ${message.type === 'success' ? '#a7f3d0' : '#fecaca'}`,
          }}
        >
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="auth-form" style={{ gap: '20px' }}>
        <div className="form-group">
          <label htmlFor="org-name">Organization Name *</label>
          <input
            id="org-name"
            type="text"
            name="organization_name"
            value={formData.organization_name}
            onChange={handleChange}
            required
            className="form-input"
            placeholder="e.g. Acme Tech Solutions"
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="org-type">Organization Type</label>
            <select
              id="org-type"
              name="organization_type"
              value={formData.organization_type}
              onChange={handleChange}
              className="select-filter"
            >
              <option value="company">Company</option>
              <option value="startup">Startup</option>
              <option value="cafe">Cafe</option>
              <option value="restaurant">Restaurant</option>
              <option value="shop">Shop / Retail</option>
              <option value="ngo">NGO / Non-Profit</option>
              <option value="educational_institution">Educational Institution</option>
              <option value="freelancer">Freelancer</option>
              <option value="individual">Individual</option>
              <option value="event_organizer">Event Organizer</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="org-contact">Contact Person</label>
            <input
              id="org-contact"
              type="text"
              name="contact_person"
              value={formData.contact_person}
              onChange={handleChange}
              className="form-input"
              placeholder="e.g. Jane Doe (Hiring Manager)"
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="org-desc">Organization Description</label>
          <textarea
            id="org-desc"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={4}
            className="form-textarea"
            placeholder="Brief overview of your organization and what you do..."
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="org-website">Website URL</label>
            <input
              id="org-website"
              type="url"
              name="website"
              value={formData.website}
              onChange={handleChange}
              className="form-input"
              placeholder="https://example.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="org-city">City</label>
            <input
              id="org-city"
              type="text"
              name="city"
              value={formData.city}
              onChange={handleChange}
              className="form-input"
              placeholder="e.g. San Francisco, CA"
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="org-address">Address / Office Location</label>
          <input
            id="org-address"
            type="text"
            name="address"
            value={formData.address}
            onChange={handleChange}
            className="form-input"
            placeholder="e.g. 100 Main St, Suite 400"
          />
        </div>

        <button
          type="submit"
          disabled={saving}
          className="btn-primary-lg"
          style={{ marginTop: '12px', alignSelf: 'flex-start' }}
        >
          {saving ? 'Saving...' : 'Save Profile Changes'}
        </button>
      </form>

    </div>
  );
}
