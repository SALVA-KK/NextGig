import React, { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { Bookmark } from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import MyOpportunities from '../../components/provider/MyOpportunities';
import PostOpportunity from '../../components/provider/PostOpportunity';
import ApplicantsView from '../../components/provider/ApplicantsView';
import ProviderProfileForm from '../../components/provider/ProviderProfileForm';
import OpportunityFilters from '../../components/opportunities/OpportunityFilters';
import OpportunityCard from '../../components/opportunities/OpportunityCard';
import StudentCollabCard from '../../components/opportunities/StudentCollabCard';
import PaginationControl from '../../components/common/PaginationControl';
import EmptyState from '../../components/common/EmptyState';
import { opportunityService } from '../../services/opportunityService';

export default function ProviderDashboard() {
  const location = useLocation();
  const [toastMessage, setToastMessage] = useState(location.state?.successMessage || null);
  const [activeTab, setActiveTab] = useState('my-opportunities'); // 'my-opportunities' | 'explore' | 'post-opportunity' | 'applicants' | 'saved' | 'profile'

  useEffect(() => {
    if (location.state?.successMessage) {
      setToastMessage(location.state.successMessage);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);
  const [selectedOppForApplicants, setSelectedOppForApplicants] = useState(null);
  const [selectedOppForEditing, setSelectedOppForEditing] = useState(null);

  // Explore tab state
  const [exploreOpps, setExploreOpps] = useState([]);
  const [exploreSubTab, setExploreSubTab] = useState('all'); // 'all' | 'collaborations'
  const [exploreLoading, setExploreLoading] = useState(false);
  const [exploreError, setExploreError] = useState(null);
  const [explorePage, setExplorePage] = useState(1);
  const [exploreTotalCount, setExploreTotalCount] = useState(0);

  // Saved items state
  const [savedItems, setSavedItems] = useState([]);
  const [savedLoading, setSavedLoading] = useState(false);
  const [savedError, setSavedError] = useState(null);
  const [savedPage, setSavedPage] = useState(1);
  const [savedTotalCount, setSavedTotalCount] = useState(0);

  // Explore filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedWorkMode, setSelectedWorkMode] = useState('');

  // Reset explore page when filters or subTab change
  useEffect(() => {
    setExplorePage(1);
  }, [exploreSubTab, selectedCategory, selectedWorkMode, locationQuery, searchQuery]);

  const loadExploreOpps = async () => {
    setExploreLoading(true);
    setExploreError(null);
    try {
      const categoryParam = (exploreSubTab === 'collaborations')
        ? 'project_collaboration'
        : (selectedCategory || undefined);

      const data = await opportunityService.getOpportunities({
        page: explorePage,
        category: categoryParam,
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

  const loadSavedOpps = async () => {
    setSavedLoading(true);
    setSavedError(null);
    try {
      const data = await opportunityService.getSavedOpportunities({ page: savedPage });
      const results = data.results || [];
      setSavedItems(results);
      setSavedTotalCount(data.count ?? results.length);
    } catch (err) {
      console.error('Error fetching saved opportunities:', err);
      setSavedError('Failed to load saved items.');
    } finally {
      setSavedLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'explore') {
      loadExploreOpps();
    }
  }, [activeTab, explorePage, exploreSubTab, selectedCategory, selectedWorkMode, locationQuery]);

  useEffect(() => {
    loadSavedOpps();
  }, [activeTab, savedPage]);

  // Derived set of saved opportunity IDs for O(1) checks
  const savedIdsSet = useMemo(() => {
    return new Set(savedItems.map((item) => item.opportunity?.id || item.opportunity_id || item.id));
  }, [savedItems]);

  const handleSaveToggle = async (oppId) => {
    const isCurrentlySaved = savedIdsSet.has(oppId);
    try {
      await opportunityService.toggleSaveOpportunity(oppId, isCurrentlySaved);
      if (isCurrentlySaved) {
        setSavedItems((prev) => prev.filter((item) => (item.opportunity?.id || item.id) !== oppId));
      } else {
        await loadSavedOpps();
      }
    } catch (err) {
      console.error('Error toggling saved opportunity:', err);
    }
  };

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
        <div style={{ marginTop: '24px' }}>
          {toastMessage && (
            <div
              style={{
                padding: '12px 16px',
                borderRadius: '8px',
                marginBottom: '20px',
                fontSize: '14px',
                backgroundColor: '#ecfdf5',
                color: '#047857',
                border: '1px solid #a7f3d0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span>{toastMessage}</span>
              <button
                onClick={() => setToastMessage(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontWeight: 'bold' }}
              >
                ×
              </button>
            </div>
          )}

          {activeTab === 'my-opportunities' && (
            <MyOpportunities
              onAddNew={handleAddNewOpportunity}
            />
          )}

          {activeTab === 'explore' && (
            <div>
              <div className="flex space-x-2 border-b border-gray-200 dark:border-gray-700 mb-6">
                <button
                  onClick={() => setExploreSubTab('all')}
                  className={`px-4 py-2.5 font-medium text-sm rounded-t-lg transition-colors ${
                    exploreSubTab === 'all'
                      ? 'bg-indigo-50 dark:bg-gray-800 text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 font-semibold'
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                  }`}
                >
                  All
                </button>

                <button
                  onClick={() => setExploreSubTab('collaborations')}
                  className={`px-4 py-2.5 font-medium text-sm rounded-t-lg transition-colors flex items-center gap-1.5 ${
                    exploreSubTab === 'collaborations'
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
                          <StudentCollabCard
                            key={opp.id}
                            opportunity={opp}
                            isSaved={savedIdsSet.has(opp.id)}
                            onSaveToggle={handleSaveToggle}
                          />
                        ) : (
                          <OpportunityCard
                            key={opp.id}
                            opportunity={opp}
                            isSaved={savedIdsSet.has(opp.id)}
                            onSaveToggle={handleSaveToggle}
                          />
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

          {activeTab === 'saved' && (
            <div>
              {savedLoading && (
                <div className="discovery-loading-grid">
                  {[1, 2, 3].map((n) => (
                    <div key={n} className="skeleton-card">
                      <div className="skeleton-line badge"></div>
                      <div className="skeleton-line title"></div>
                      <div className="skeleton-line subtitle"></div>
                    </div>
                  ))}
                </div>
              )}

              {!savedLoading && savedError && (
                <div className="discovery-error-box">
                  <p>{savedError}</p>
                  <button onClick={loadSavedOpps} className="btn-retry">
                    Retry Loading
                  </button>
                </div>
              )}

              {!savedLoading && !savedError && (
                <>
                  {savedItems.length === 0 ? (
                    <EmptyState
                      icon={Bookmark}
                      title="No saved opportunities yet"
                      subtitle="Browse and save some!"
                      actionLabel="Explore Opportunities"
                      onAction={() => setActiveTab('explore')}
                    />
                  ) : (
                    <div className="discovery-grid">
                      {savedItems.map((item) => {
                        const opp = item.opportunity || item;
                        if (!opp || !opp.id) return null;
                        return opp.category === 'project_collaboration' || opp.is_student_project ? (
                          <StudentCollabCard
                            key={opp.id}
                            opportunity={opp}
                            isSaved={savedIdsSet.has(opp.id)}
                            onSaveToggle={handleSaveToggle}
                          />
                        ) : (
                          <OpportunityCard
                            key={opp.id}
                            opportunity={opp}
                            isSaved={savedIdsSet.has(opp.id)}
                            onSaveToggle={handleSaveToggle}
                          />
                        );
                      })}
                    </div>
                  )}

                  <PaginationControl
                    currentPage={savedPage}
                    totalItems={savedTotalCount}
                    pageSize={20}
                    onPageChange={(newPage) => setSavedPage(newPage)}
                  />
                </>
              )}
            </div>
          )}

          {activeTab === 'profile' && <ProviderProfileForm />}
        </div>
      </div>
    </DashboardLayout>
  );
}

