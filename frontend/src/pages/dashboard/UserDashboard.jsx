import React, { useState, useEffect, useMemo } from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import OpportunityFilters from '../../components/opportunities/OpportunityFilters';
import OpportunityCard from '../../components/opportunities/OpportunityCard';
import StudentCollabCard from '../../components/opportunities/StudentCollabCard';
import OpportunityDetailModal from '../../components/opportunities/OpportunityDetailModal';
import { opportunityService } from '../../services/opportunityService';

export default function UserDashboard() {
  const [activeTab, setActiveTab] = useState('opportunities'); // 'opportunities' | 'collaborations' | 'saved' | 'applications'
  const [opportunities, setOpportunities] = useState([]);
  const [savedItems, setSavedItems] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedWorkMode, setSelectedWorkMode] = useState('');

  // Detail Modal state
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);

  // Fetch initial opportunities and user state
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [oppsData, savedData, appsData] = await Promise.all([
        opportunityService.getOpportunities({
          category: selectedCategory || undefined,
          work_mode: selectedWorkMode || undefined,
          city: locationQuery || undefined
        }),
        opportunityService.getSavedOpportunities(),
        opportunityService.getMyApplications()
      ]);

      setOpportunities(oppsData.results || []);
      setSavedItems(savedData || []);
      setApplications(appsData || []);
    } catch (err) {
      console.error('Failed to load opportunities:', err);
      setError('Unable to load opportunities right now. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedCategory, selectedWorkMode, locationQuery]);

  // Derived sets for quick O(1) checks
  const savedIdsSet = useMemo(() => {
    return new Set(savedItems.map(item => item.opportunity?.id || item.opportunity_id || item.id));
  }, [savedItems]);

  const appliedIdsSet = useMemo(() => {
    return new Set(applications.map(app => app.opportunity?.id || app.opportunity_id || app.id));
  }, [applications]);

  // Save / Bookmark handler
  const handleSaveToggle = async (oppId) => {
    const isCurrentlySaved = savedIdsSet.has(oppId);
    try {
      await opportunityService.toggleSaveOpportunity(oppId, isCurrentlySaved);
      if (isCurrentlySaved) {
        setSavedItems(prev => prev.filter(item => (item.opportunity?.id || item.id) !== oppId));
      } else {
        const foundOpp = opportunities.find(o => o.id === oppId);
        if (foundOpp) {
          setSavedItems(prev => [...prev, { id: oppId, opportunity: foundOpp }]);
        }
      }
    } catch (err) {
      console.error('Error toggling save status:', err);
    }
  };

  // Application submission handler
  const handleApplySubmit = async (oppId, coverNote) => {
    await opportunityService.applyToOpportunity(oppId, coverNote);
    const updatedApps = await opportunityService.getMyApplications();
    setApplications(updatedApps);
  };

  // Client-side text & category filtering
  const filteredOpportunities = useMemo(() => {
    return opportunities.filter(opp => {
      // Filter out student projects if on main 'opportunities' tab, or filter only student projects if on 'collaborations'
      if (activeTab === 'opportunities') {
        if (opp.category === 'project_collaboration' || opp.is_student_project) return false;
      } else if (activeTab === 'collaborations') {
        if (opp.category !== 'project_collaboration' && !opp.is_student_project) return false;
      }

      // Search query filter (matches title, description, skills, provider)
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const titleMatch = opp.title?.toLowerCase().includes(q);
        const descMatch = opp.description?.toLowerCase().includes(q);
        const providerMatch = opp.poster?.full_name?.toLowerCase().includes(q) || opp.poster?.email?.toLowerCase().includes(q);
        const skillsMatch = opp.required_skills?.some(s => s.toLowerCase().includes(q));
        if (!titleMatch && !descMatch && !providerMatch && !skillsMatch) return false;
      }

      // Location filter
      if (locationQuery.trim()) {
        const locQ = locationQuery.toLowerCase().trim();
        const cityMatch = opp.city?.toLowerCase().includes(locQ);
        const locMatch = opp.location_text?.toLowerCase().includes(locQ);
        const modeMatch = opp.work_mode?.toLowerCase().includes(locQ);
        if (!cityMatch && !locMatch && !modeMatch) return false;
      }

      return true;
    });
  }, [opportunities, activeTab, searchQuery, locationQuery]);

  const resetFilters = () => {
    setSearchQuery('');
    setLocationQuery('');
    setSelectedCategory('');
    setSelectedWorkMode('');
  };

  return (
    <DashboardLayout activeTab={activeTab} setActiveTab={setActiveTab}>
      <div className="discovery-container">
        
        {/* HERO INTRO */}
        <section className="discovery-hero-section">
          <div className="hero-badge">STUDENT OPPORTUNITY HUB</div>
          <h1 className="hero-heading">Find opportunities and people to build with.</h1>
          <p className="hero-subtext">
            Discover flexible part-time gigs, internships, freelance projects, or team up with fellow student creators for hackathons and technical projects.
          </p>
        </section>

        {/* MAIN DISCOVERY TABS */}
        <div className="discovery-tab-bar">
          <button
            onClick={() => setActiveTab('opportunities')}
            className={`discovery-tab-btn ${activeTab === 'opportunities' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
            </svg>
            Opportunities
          </button>

          <button
            onClick={() => setActiveTab('collaborations')}
            className={`discovery-tab-btn ${activeTab === 'collaborations' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 4 4H5a4 4 0 0 4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            Student Collaborations
          </button>

          <button
            onClick={() => setActiveTab('saved')}
            className={`discovery-tab-btn ${activeTab === 'saved' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
            </svg>
            Saved ({savedItems.length})
          </button>

          <button
            onClick={() => setActiveTab('applications')}
            className={`discovery-tab-btn ${activeTab === 'applications' ? 'active' : ''}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            Applications ({applications.length})
          </button>
        </div>

        {/* SEARCH & FILTERS (Active on Opportunities & Collaborations tabs) */}
        {(activeTab === 'opportunities' || activeTab === 'collaborations') && (
          <OpportunityFilters
            activeTab={activeTab}
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
        )}

        {/* LOADING STATE */}
        {loading && (
          <div className="discovery-loading-grid">
            {[1, 2, 3, 4, 5, 6].map(n => (
              <div key={n} className="skeleton-card">
                <div className="skeleton-line badge"></div>
                <div className="skeleton-line title"></div>
                <div className="skeleton-line subtitle"></div>
                <div className="skeleton-line tags"></div>
              </div>
            ))}
          </div>
        )}

        {/* ERROR STATE */}
        {!loading && error && (
          <div className="discovery-error-box">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <p>{error}</p>
            <button onClick={loadData} className="btn-retry">Retry Loading</button>
          </div>
        )}

        {/* CONTENT GRID: OPPORTUNITIES TAB */}
        {!loading && !error && activeTab === 'opportunities' && (
          <>
            {filteredOpportunities.length === 0 ? (
              <div className="empty-state-box">
                <h3>No opportunities found matching your criteria</h3>
                <p>Try adjusting your search terms, work mode, or reset category filters.</p>
                <button onClick={resetFilters} className="btn-reset-filters">Clear All Filters</button>
              </div>
            ) : (
              <div className="discovery-grid">
                {filteredOpportunities.map(opp => (
                  <OpportunityCard
                    key={opp.id}
                    opportunity={opp}
                    isSaved={savedIdsSet.has(opp.id)}
                    onSaveToggle={handleSaveToggle}
                    onSelect={(selected) => setSelectedOpportunity(selected)}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* CONTENT GRID: COLLABORATIONS TAB */}
        {!loading && !error && activeTab === 'collaborations' && (
          <>
            {filteredOpportunities.length === 0 ? (
              <div className="empty-state-box">
                <h3>No student projects found</h3>
                <p>Be the first student to post a project or clear your search filters.</p>
                <button onClick={resetFilters} className="btn-reset-filters">Clear All Filters</button>
              </div>
            ) : (
              <div className="discovery-grid">
                {filteredOpportunities.map(opp => (
                  <StudentCollabCard
                    key={opp.id}
                    opportunity={opp}
                    isSaved={savedIdsSet.has(opp.id)}
                    onSaveToggle={handleSaveToggle}
                    onSelect={(selected) => setSelectedOpportunity(selected)}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* CONTENT GRID: SAVED TAB */}
        {!loading && !error && activeTab === 'saved' && (
          <>
            {savedItems.length === 0 ? (
              <div className="empty-state-box">
                <h3>No saved opportunities yet</h3>
                <p>Click the bookmark icon on any opportunity or project card to save it for later.</p>
                <button onClick={() => setActiveTab('opportunities')} className="btn-reset-filters">
                  Explore Opportunities
                </button>
              </div>
            ) : (
              <div className="discovery-grid">
                {savedItems.map(item => {
                  const opp = item.opportunity || item;
                  return (
                    <OpportunityCard
                      key={opp.id}
                      opportunity={opp}
                      isSaved={true}
                      onSaveToggle={handleSaveToggle}
                      onSelect={(selected) => setSelectedOpportunity(selected)}
                    />
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* CONTENT GRID: APPLICATIONS TAB */}
        {!loading && !error && activeTab === 'applications' && (
          <>
            {applications.length === 0 ? (
              <div className="empty-state-box">
                <h3>No applications submitted yet</h3>
                <p>Browse available opportunities and click "View Details" to submit your application.</p>
                <button onClick={() => setActiveTab('opportunities')} className="btn-reset-filters">
                  Explore Opportunities
                </button>
              </div>
            ) : (
              <div className="discovery-grid">
                {applications.map(app => {
                  const opp = app.opportunity || app;
                  return (
                    <div key={app.id} className="application-card-wrapper">
                      <div className="app-status-bar">
                        <span className={`status-pill status-${app.status || 'applied'}`}>
                          Status: {(app.status || 'Applied').replace('_', ' ').toUpperCase()}
                        </span>
                        <span className="app-date">
                          Applied {app.applied_at ? new Date(app.applied_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Recently'}
                        </span>
                      </div>
                      <OpportunityCard
                        opportunity={opp}
                        isSaved={savedIdsSet.has(opp.id)}
                        onSaveToggle={handleSaveToggle}
                        onSelect={(selected) => setSelectedOpportunity(selected)}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

      </div>

      {/* DETAIL VIEW MODAL */}
      {selectedOpportunity && (
        <OpportunityDetailModal
          opportunity={selectedOpportunity}
          onClose={() => setSelectedOpportunity(null)}
          isSaved={savedIdsSet.has(selectedOpportunity.id)}
          onSaveToggle={handleSaveToggle}
          onApplySubmit={handleApplySubmit}
          hasApplied={appliedIdsSet.has(selectedOpportunity.id)}
        />
      )}
    </DashboardLayout>
  );
}
