import React, { useState } from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import MyOpportunities from '../../components/provider/MyOpportunities';
import PostOpportunity from '../../components/provider/PostOpportunity';
import ApplicantsView from '../../components/provider/ApplicantsView';
import ProviderProfileForm from '../../components/provider/ProviderProfileForm';

export default function ProviderDashboard() {
  const [activeTab, setActiveTab] = useState('my-opportunities'); // 'my-opportunities' | 'post-opportunity' | 'applicants' | 'profile'
  const [selectedOppForApplicants, setSelectedOppForApplicants] = useState(null);
  const [selectedOppForEditing, setSelectedOppForEditing] = useState(null);

  const handleViewApplicants = (opp) => {
    setSelectedOppForApplicants(opp);
    setActiveTab('applicants');
  };

  const handleEditOpportunity = (opp) => {
    setSelectedOppForEditing(opp);
    setActiveTab('post-opportunity');
  };

  const handleAddNewOpportunity = () => {
    setSelectedOppForEditing(null);
    setActiveTab('post-opportunity');
  };

  return (
    <DashboardLayout activeTab={activeTab} setActiveTab={setActiveTab}>
      <div className="discovery-container">
        
        {/* HERO INTRO */}
        <section className="discovery-hero-section">
          <div className="hero-badge">PROVIDER PORTAL</div>
          <h1 className="hero-heading">Manage Your Opportunities & Talent Pipeline</h1>
          <p className="hero-subtext">
            Post new student gigs and internships, review applications and candidate resumes, and keep your organization profile updated.
          </p>
        </section>

        {/* TAB NAVIGATION */}
        <div className="discovery-tab-bar">
          <button
            onClick={() => {
              setSelectedOppForEditing(null);
              setActiveTab('my-opportunities');
            }}
            className={`discovery-tab-btn ${activeTab === 'my-opportunities' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
            </svg>
            My Opportunities
          </button>

          <button
            onClick={() => {
              setSelectedOppForEditing(null);
              setActiveTab('post-opportunity');
            }}
            className={`discovery-tab-btn ${activeTab === 'post-opportunity' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            {selectedOppForEditing ? 'Edit Opportunity' : 'Post New Opportunity'}
          </button>

          <button
            onClick={() => setActiveTab('applicants')}
            className={`discovery-tab-btn ${activeTab === 'applicants' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            Applicants
          </button>

          <button
            onClick={() => setActiveTab('profile')}
            className={`discovery-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            Provider Profile
          </button>
        </div>

        {/* CONTENT AREA */}
        <div style={{ marginTop: '24px' }}>
          {activeTab === 'my-opportunities' && (
            <MyOpportunities
              onViewApplicants={handleViewApplicants}
              onEditOpportunity={handleEditOpportunity}
              onAddNew={handleAddNewOpportunity}
            />
          )}

          {activeTab === 'post-opportunity' && (
            <PostOpportunity
              key={selectedOppForEditing?.id || 'new'}
              initialData={selectedOppForEditing}
              onSuccess={() => {
                setSelectedOppForEditing(null);
                setActiveTab('my-opportunities');
              }}
            />
          )}

          {activeTab === 'applicants' && (
            <ApplicantsView
              selectedOpportunity={selectedOppForApplicants}
              onSelectOpportunity={(opp) => setSelectedOppForApplicants(opp)}
            />
          )}

          {activeTab === 'profile' && <ProviderProfileForm />}
        </div>
      </div>
    </DashboardLayout>
  );
}
