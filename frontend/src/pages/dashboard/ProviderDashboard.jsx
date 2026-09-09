import React, { useState, useEffect, useMemo } from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import MyOpportunities from '../../components/provider/MyOpportunities';
import PostOpportunity from '../../components/provider/PostOpportunity';
import ApplicantsView from '../../components/provider/ApplicantsView';
import ProviderProfileForm from '../../components/provider/ProviderProfileForm';
import OpportunityFilters from '../../components/opportunities/OpportunityFilters';
import OpportunityCard from '../../components/opportunities/OpportunityCard';
import StudentCollabCard from '../../components/opportunities/StudentCollabCard';
import PaginationControl from '../../components/common/PaginationControl';
import { opportunityService } from '../../services/opportunityService';

export default function ProviderDashboard() {
  const [activeTab, setActiveTab] = useState('my-opportunities'); // 'my-opportunities' | 'explore' | 'post-opportunity' | 'applicants' | 'profile'
  const [selectedOppForApplicants, setSelectedOppForApplicants] = useState(null);
  const [selectedOppForEditing, setSelectedOppForEditing] = useState(null);

  // Explore tab state
  const [exploreOpps, setExploreOpps] = useState([]);
  const [exploreLoading, setExploreLoading] = useState(false);
  const [exploreError, setExploreError] = useState(null);
  const [explorePage, setExplorePage] = useState(1);
  const [exploreTotalCount, setExploreTotalCount] = useState(0);

  // Explore filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedWorkMode, setSelectedWorkMode] = useState('');

  // Reset explore page when filters change
  useEffect(() => {
    setExplorePage(1);
  }, [selectedCategory, selectedWorkMode, locationQuery, searchQuery]);

  const loadExploreOpps = async () => {
    setExploreLoading(true);
    setExploreError(null);
    try {
      const data = await opportunityService.getOpportunities({
        page: explorePage,
        category: selectedCategory || undefined,
        work_mode: selectedWorkMode || undefined,
        city: locationQuery || undefined,
      });
      const results = data.results || [];
      setExploreOpps(results);
      setExploreTotalCount(data.count ?? results.length);
    } catch (err) {
      console.error('Error fetching explore opportunities:', err);
      setExploreError('Failed to load opportunities. Please check your connection.');
    } finally {
      setExploreLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'explore') {
      loadExploreOpps();
    }
  }, [activeTab, explorePage, selectedCategory, selectedWorkMode, locationQuery]);

  const filteredExploreOpps = useMemo(() => {
    return exploreOpps.filter((opp) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const titleMatch = opp.title?.toLowerCase().includes(q);
        const descMatch = opp.description?.toLowerCase().includes(q);
        const providerMatch =
          opp.poster?.full_name?.toLowerCase().includes(q) ||
          opp.poster?.email?.toLowerCase().includes(q);
        const skillsMatch = opp.required_skills?.some((s) => s.toLowerCase().includes(q));
        if (!titleMatch && !descMatch && !providerMatch && !skillsMatch) return false;
      }

      if (locationQuery.trim()) {
        const locQ = locationQuery.toLowerCase().trim();
        const cityMatch = opp.city?.toLowerCase().includes(locQ);
        const locMatch = opp.location_text?.toLowerCase().includes(locQ);
        const modeMatch = opp.work_mode?.toLowerCase().includes(locQ);
        if (!cityMatch && !locMatch && !modeMatch) return false;
      }

      return true;
    });
  }, [exploreOpps, searchQuery, locationQuery]);

  const resetFilters = () => {
    setSearchQuery('');
    setLocationQuery('');
    setSelectedCategory('');
    setSelectedWorkMode('');
  };

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
            Post new student gigs and internships, review applications and candidate resumes, explore the public opportunity feed, and keep your organization profile updated.
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
            onClick={() => setActiveTab('explore')}
            className={`discovery-tab-btn ${activeTab === 'explore' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            Explore Opportunities
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

          {activeTab === 'explore' && (
            <div>
              <OpportunityFilters
                activeTab="opportunities"
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                locationQuery={locationQuery}
                setLocationQuery={setLocationQuery}
                selectedCategory={selectedCategory}
                setSelectedCategory={setSelectedCategory}
                selectedWorkMode={selectedWorkMode}
                setSelectedWorkMode={setSelectedWorkMode}
                onReset={resetFilters}
              />

              {exploreLoading && (
                <div className="discovery-loading-grid">
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <div key={n} className="skeleton-card">
                      <div className="skeleton-line badge"></div>
                      <div className="skeleton-line title"></div>
                      <div className="skeleton-line subtitle"></div>
                      <div className="skeleton-line tags"></div>
                    </div>
                  ))}
                </div>
              )}

              {!exploreLoading && exploreError && (
                <div className="discovery-error-box">
                  <p>{exploreError}</p>
                  <button onClick={loadExploreOpps} className="btn-retry">
                    Retry Loading
                  </button>
                </div>
              )}

              {!exploreLoading && !exploreError && (
                <>
                  {filteredExploreOpps.length === 0 ? (
                    <div className="empty-state-box">
                      <h3>No opportunities found</h3>
                      <p>Try adjusting your search query, work mode, or category filters.</p>
                      <button onClick={resetFilters} className="btn-reset-filters">
                        Clear All Filters
                      </button>
                    </div>
                  ) : (
                    <div className="discovery-grid">
                      {filteredExploreOpps.map((opp) =>
                        opp.category === 'project_collaboration' || opp.is_student_project ? (
                          <StudentCollabCard key={opp.id} opportunity={opp} />
                        ) : (
                          <OpportunityCard key={opp.id} opportunity={opp} />
                        )
                      )}
                    </div>
                  )}

                  <PaginationControl
                    currentPage={explorePage}
                    totalItems={exploreTotalCount}
                    pageSize={20}
                    onPageChange={(newPage) => setExplorePage(newPage)}
                  />
                </>
              )}
            </div>
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
