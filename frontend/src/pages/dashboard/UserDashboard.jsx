import React, { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import OpportunityFilters from '../../components/opportunities/OpportunityFilters';
import OpportunityCard from '../../components/opportunities/OpportunityCard';
import StudentCollabCard from '../../components/opportunities/StudentCollabCard';
import PaginationControl from '../../components/common/PaginationControl';
import { opportunityService } from '../../services/opportunityService';

export default function UserDashboard() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState('opportunities'); // 'opportunities' | 'saved' | 'applications'
  const [oppSubTab, setOppSubTab] = useState('all'); // 'all' | 'recommended' | 'collaborations'
  const [opportunities, setOpportunities] = useState([]);
  const [savedItems, setSavedItems] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedWorkMode, setSelectedWorkMode] = useState('');

  // Detail Modal state
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);

  // Sync URL search params for tab/subTab selection (e.g., from notifications)
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const subTabParam = searchParams.get('subTab') || searchParams.get('tab');
    if (subTabParam === 'recommended') {
      setActiveTab('opportunities');
      setOppSubTab('recommended');
    } else if (subTabParam === 'collaborations') {
      setActiveTab('opportunities');
      setOppSubTab('collaborations');
    } else if (subTabParam === 'all') {
      setActiveTab('opportunities');
      setOppSubTab('all');
    }
  }, [location.search]);

  // Reset page to 1 when filters or active subTab change
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, oppSubTab, selectedCategory, selectedWorkMode, locationQuery, searchQuery]);

  // Fetch initial opportunities and user state
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      let oppsData = { results: [], count: 0 };
      const [savedData, appsData] = await Promise.all([
        opportunityService.getSavedOpportunities({ page: activeTab === 'saved' ? currentPage : 1 }),
        opportunityService.getMyApplications({ page: activeTab === 'applications' ? currentPage : 1 })
      ]);

      if (activeTab === 'opportunities') {
        if (oppSubTab === 'recommended') {
          oppsData = await opportunityService.getRecommendedOpportunities({ page: currentPage });
          const recResults = (oppsData.results || []).map(r => r.opportunity || r);
          oppsData = { ...oppsData, results: recResults };
        } else {
          const categoryParam = (oppSubTab === 'collaborations')
            ? 'project_collaboration'
            : (selectedCategory || undefined);

          oppsData = await opportunityService.getOpportunities({
            page: currentPage,
            category: categoryParam,
            work_mode: selectedWorkMode || undefined,
            city: locationQuery || undefined
          });
        }
      }

      const oppsList = oppsData.results || [];
      const savedList = savedData.results || [];
      const appsList = appsData.results || [];

      setOpportunities(oppsList);
      setSavedItems(savedList);
      setApplications(appsList);

      if (activeTab === 'opportunities') {
        setTotalCount(oppsData.count ?? oppsList.length);
      } else if (activeTab === 'saved') {
        setTotalCount(savedData.count ?? savedList.length);
      } else if (activeTab === 'applications') {
        setTotalCount(appsData.count ?? appsList.length);
      }
    } catch (err) {
      console.error('Failed to load opportunities:', err);
      setError('Unable to load opportunities right now. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentPage, activeTab, oppSubTab, selectedCategory, selectedWorkMode, locationQuery]);

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
  }, [opportunities, searchQuery, locationQuery]);

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



        {/* SUB-TABS ON OPPORTUNITIES PAGE (All / Recommended / Collaborations) */}
        {activeTab === 'opportunities' && (
          <div className="flex space-x-2 border-b border-gray-200 dark:border-gray-700 mb-6">
            <button
              onClick={() => setOppSubTab('all')}
              className={`px-4 py-2.5 font-medium text-sm rounded-t-lg transition-colors ${
                oppSubTab === 'all'
                  ? 'bg-indigo-50 dark:bg-gray-800 text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 font-semibold'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              All
            </button>

            <button
              onClick={() => setOppSubTab('recommended')}
              className={`px-4 py-2.5 font-medium text-sm rounded-t-lg transition-colors flex items-center gap-1.5 ${
                oppSubTab === 'recommended'
                  ? 'bg-indigo-50 dark:bg-gray-800 text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 font-semibold'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
              </svg>
              Recommended
            </button>

            <button
              onClick={() => setOppSubTab('collaborations')}
              className={`px-4 py-2.5 font-medium text-sm rounded-t-lg transition-colors flex items-center gap-1.5 ${
                oppSubTab === 'collaborations'
                  ? 'bg-indigo-50 dark:bg-gray-800 text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 font-semibold'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              Collaborations
            </button>
          </div>
        )}

        {/* SEARCH & FILTERS (Active on Opportunities tab) */}
        {activeTab === 'opportunities' && (
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
              <div className="empty-state-box p-8 text-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm my-6">
                {oppSubTab === 'recommended' ? (
                  <>
                    <div className="text-4xl mb-3">🎯</div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
                      No recommended opportunities yet
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto mb-5">
                      To get personalized daily opportunity recommendations, please complete your profile with your current skills and location.
                    </p>
                    <Link
                      to="/profile"
                      className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg shadow-sm transition-colors"
                    >
                      Complete Profile in Settings
                    </Link>
                  </>
                ) : (
                  <>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
                      No opportunities found matching your criteria
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                      Try adjusting your search terms, work mode, or reset category filters.
                    </p>
                    <button onClick={resetFilters} className="btn-reset-filters">
                      Clear All Filters
                    </button>
                  </>
                )}
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

        {/* PAGINATION CONTROL */}
        {!loading && !error && (
          <PaginationControl
            currentPage={currentPage}
            totalItems={totalCount}
            pageSize={20}
            onPageChange={(newPage) => setCurrentPage(newPage)}
          />
        )}

      </div>
    </DashboardLayout>
  );
}

