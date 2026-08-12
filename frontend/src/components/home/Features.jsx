import React from 'react';

export default function Features() {
  const featuresList = [
    {
      icon: '🔍',
      title: 'Discover Opportunities',
      description: 'Explore curated gigs, internships, and project positions tailored to your skill set.',
    },
    {
      icon: '👤',
      title: 'Build Your Profile',
      description: 'Showcase your credentials, past work, and experience with a professional profile.',
    },
    {
      icon: '🚀',
      title: 'Grow Your Career',
      description: 'Connect with verified employers, complete projects, and advance your professional journey.',
    },
  ];

  return (
    <section className="home-features" id="about">
      <div className="home-features-container">
        <div className="home-features-grid">
          {featuresList.map((feature, idx) => (
            <div key={idx} className="dashboard-stat-card home-feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-card-title">{feature.title}</h3>
              <p className="feature-card-desc">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
