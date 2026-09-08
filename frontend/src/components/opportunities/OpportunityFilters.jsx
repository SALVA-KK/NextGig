import React from 'react';

export default function OpportunityFilters({
  activeTab,
  searchQuery,
  setSearchQuery,
  locationQuery,
  setLocationQuery,
  selectedCategory,
  setSelectedCategory,
  selectedWorkMode,
  setSelectedWorkMode,
  onReset
}) {
  const categories = [
    { label: 'All Types', value: '' },
    { label: 'Internships', value: 'internship' },
    { label: 'Part-Time', value: 'part_time' },
    { label: 'Freelance', value: 'freelance' },
    { label: 'Startup Hiring', value: 'startup_hiring' },
    { label: 'Project Collab', value: 'project_collaboration' },
    { label: 'Tutoring', value: 'tutoring' },
    { label: 'Volunteer', value: 'volunteer' },
    { label: 'Events', value: 'event_based' }
  ];

  const workModes = [
    { label: 'All Modes', value: '' },
    { label: 'Remote', value: 'remote' },
    { label: 'Hybrid', value: 'hybrid' },
    { label: 'Onsite', value: 'onsite' }
  ];

  const hasActiveFilters = searchQuery || locationQuery || selectedCategory || selectedWorkMode;

  return (
    <div className="discovery-filter-container">
      {/* Search & Location Bar */}
      <div className="discovery-search-row">
        <div className="search-input-wrapper">
          <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder={
              activeTab === 'collaborations'
                ? "Search student projects, hackathons, or skills needed (e.g. Django, Figma)..."
                : "Search opportunities, roles, or skills (e.g. React, Tutoring, Internship)..."
            }
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="clear-search-btn" onClick={() => setSearchQuery('')}>×</button>
          )}
        </div>

        <div className="location-input-wrapper">
          <svg className="location-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
            <circle cx="12" cy="10" r="3"></circle>
          </svg>
          <input
            type="text"
            className="location-input"
            placeholder="Location or Remote"
            value={locationQuery}
            onChange={(e) => setLocationQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Categories & Work Mode Controls */}
      <div className="discovery-filter-controls">
        <div className="category-scroll-strip">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`filter-pill ${selectedCategory === cat.value ? 'active' : ''}`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="secondary-filters-row">
          <select
            value={selectedWorkMode}
            onChange={(e) => setSelectedWorkMode(e.target.value)}
            className="select-filter"
          >
            {workModes.map((wm) => (
              <option key={wm.value} value={wm.value}>
                {wm.label}
              </option>
            ))}
          </select>

          {hasActiveFilters && (
            <button onClick={onReset} className="btn-reset-filters">
              Reset Filters
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
