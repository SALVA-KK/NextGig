import React from 'react';
import { Link } from 'react-router-dom';

export default function CTA() {
  return (
    <section className="home-cta">
      <div className="home-cta-container">
        <h2 className="home-cta-title">Ready to Start Your Next Gig?</h2>
        <p className="home-cta-subtitle">
          Create your account today and unlock new career opportunities.
        </p>
        <Link to="/register" className="btn-primary-lg" id="cta-register-btn">
          Get Started Now
        </Link>
      </div>
    </section>
  );
}
