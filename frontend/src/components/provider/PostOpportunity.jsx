import React, { useState } from 'react';
import { opportunityService } from '../../services/opportunityService';

export default function PostOpportunity({ initialData = null, onSuccess }) {
  const isEditing = !!initialData?.id;

  const [formData, setFormData] = useState({
    title: initialData?.title || '',
    description: initialData?.description || '',
    category: initialData?.category || 'internship',
    required_skills: Array.isArray(initialData?.required_skills)
      ? initialData.required_skills.join(', ')
      : initialData?.required_skills || '',
    pay_type: initialData?.pay_type || 'stipend',
    pay_amount: initialData?.pay_amount || '',
    duration: initialData?.duration || '',
    working_hours: initialData?.working_hours || '',
    work_mode: initialData?.work_mode || 'remote',
    location_text: initialData?.location_text || '',
    city: initialData?.city || '',
    vacancies: initialData?.vacancies || 1,
    deadline: initialData?.deadline || '',
    contact_info: initialData?.contact_info || '',
    status: initialData?.status || 'open',
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    // Format skills from comma-separated string to Array
    const skillsArray = formData.required_skills
      ? formData.required_skills
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

    const payload = {
      title: formData.title,
      description: formData.description,
      category: formData.category,
      required_skills: skillsArray,
      pay_type: formData.pay_type,
      pay_amount: formData.pay_amount ? parseFloat(formData.pay_amount) : null,
      duration: formData.duration,
      working_hours: formData.working_hours,
      work_mode: formData.work_mode,
      location_text: formData.location_text,
      city: formData.city,
      vacancies: parseInt(formData.vacancies, 10) || 1,
      deadline: formData.deadline || null,
      contact_info: formData.contact_info,
      status: formData.status,
    };

    try {
      if (isEditing) {
        await opportunityService.updateOpportunity(initialData.id, payload);
        setMessage({ type: 'success', text: 'Opportunity updated successfully!' });
      } else {
        await opportunityService.createOpportunity(payload);
        setMessage({ type: 'success', text: 'New opportunity posted successfully!' });
        // Reset form after creation
        setFormData({
          title: '',
          description: '',
          category: 'internship',
          required_skills: '',
          pay_type: 'stipend',
          pay_amount: '',
          duration: '',
          working_hours: '',
          work_mode: 'remote',
          location_text: '',
          city: '',
          vacancies: 1,
          deadline: '',
          contact_info: '',
          status: 'open',
        });
      }
      if (onSuccess) onSuccess();
    } catch (err) {
      console.error('Error saving opportunity:', err);
      const errDetail = err.response?.data
        ? typeof err.response.data === 'string'
          ? err.response.data
          : JSON.stringify(err.response.data)
        : 'Failed to save opportunity. Please check all fields.';
      setMessage({ type: 'error', text: errDetail });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-card" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px' }}>
        {isEditing ? 'Edit Opportunity Listing' : 'Post a New Opportunity'}
      </h2>

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
          <label htmlFor="opp-title">Opportunity Title *</label>
          <input
            id="opp-title"
            type="text"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
            className="form-input"
            placeholder="e.g. Frontend Developer Intern / Part-Time Tutor"
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="opp-category">Category *</label>
            <select
              id="opp-category"
              name="category"
              value={formData.category}
              onChange={handleChange}
              className="select-filter"
              required
            >
              <option value="part_time">Part Time</option>
              <option value="internship">Internship</option>
              <option value="freelance">Freelance</option>
              <option value="startup_hiring">Startup Hiring</option>
              <option value="project_collaboration">Project Collaboration</option>
              <option value="tutoring">Tutoring</option>
              <option value="volunteer">Volunteer</option>
              <option value="event_based">Event Based</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="opp-workmode">Work Mode *</label>
            <select
              id="opp-workmode"
              name="work_mode"
              value={formData.work_mode}
              onChange={handleChange}
              className="select-filter"
              required
            >
              <option value="remote">Remote</option>
              <option value="onsite">Onsite</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="opp-status">Listing Status</label>
            <select id="opp-status" name="status" value={formData.status} onChange={handleChange} className="select-filter">
              <option value="open">Open</option>
              <option value="closed">Closed</option>
              <option value="draft">Draft</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="opp-desc">Description *</label>
          <textarea
            id="opp-desc"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={5}
            required
            className="form-textarea"
            placeholder="Detailed description of responsibilities, requirements, and opportunity highlights..."
          />
        </div>

        <div className="form-group">
          <label htmlFor="opp-skills">Required Skills (comma-separated)</label>
          <input
            id="opp-skills"
            type="text"
            name="required_skills"
            value={formData.required_skills}
            onChange={handleChange}
            className="form-input"
            placeholder="e.g. React, Node.js, Python, Figma"
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="opp-paytype">Pay Type</label>
            <select id="opp-paytype" name="pay_type" value={formData.pay_type} onChange={handleChange} className="select-filter">
              <option value="hourly">Hourly</option>
              <option value="monthly">Monthly</option>
              <option value="stipend">Stipend</option>
              <option value="unpaid">Unpaid</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="opp-payamt">Pay Amount (INR / USD)</label>
            <input
              id="opp-payamt"
              type="number"
              step="0.01"
              name="pay_amount"
              value={formData.pay_amount}
              onChange={handleChange}
              className="form-input"
              placeholder="e.g. 500"
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="opp-duration">Duration</label>
            <input
              id="opp-duration"
              type="text"
              name="duration"
              value={formData.duration}
              onChange={handleChange}
              className="form-input"
              placeholder="e.g. 3 Months / Flexible"
            />
          </div>

          <div className="form-group">
            <label htmlFor="opp-hours">Working Hours</label>
            <input
              id="opp-hours"
              type="text"
              name="working_hours"
              value={formData.working_hours}
              onChange={handleChange}
              className="form-input"
              placeholder="e.g. 15-20 hrs/week"
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="opp-city">City</label>
            <input
              id="opp-city"
              type="text"
              name="city"
              value={formData.city}
              onChange={handleChange}
              className="form-input"
              placeholder="e.g. San Francisco"
            />
          </div>

          <div className="form-group">
            <label htmlFor="opp-vacancies">Vacancies Count</label>
            <input
              id="opp-vacancies"
              type="number"
              min="1"
              name="vacancies"
              value={formData.vacancies}
              onChange={handleChange}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="opp-deadline">Application Deadline</label>
            <input
              id="opp-deadline"
              type="date"
              name="deadline"
              value={formData.deadline}
              onChange={handleChange}
              className="form-input"
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="opp-loc">Location Address</label>
          <input
            id="opp-loc"
            type="text"
            name="location_text"
            value={formData.location_text}
            onChange={handleChange}
            className="form-input"
            placeholder="e.g. Building A, Tech Park, City Center"
          />
        </div>

        <div className="form-group">
          <label htmlFor="opp-contact">Contact Info / How to Apply</label>
          <input
            id="opp-contact"
            type="text"
            name="contact_info"
            value={formData.contact_info}
            onChange={handleChange}
            className="form-input"
            placeholder="e.g. jobs@acme.org or Contact Hiring Team"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary-lg"
          style={{ marginTop: '12px', alignSelf: 'flex-start' }}
        >
          {loading ? 'Submitting...' : isEditing ? 'Save Changes' : 'Post Opportunity'}
        </button>
      </form>

    </div>
  );
}
