import React from 'react';
import { Link } from 'react-router-dom';

export default function Hero() {
  return (
    <section className="home-hero">
      <div className="home-hero-container">
        <h1 className="home-hero-title">
          Find Opportunities. Build Your Future.
        </h1>
        <p className="home-hero-subtitle">
          NextGig is the platform connecting talent with exciting opportunities, projects, and career milestones.
        </p>
        <div className="home-hero-actions">
          <Link to="/register" className="btn-primary-lg" id="hero-getstarted-btn">
            Get Started
          </Link>
          <Link to="/login" className="btn-secondary-lg" id="hero-login-btn">
            Sign In
          </Link>
        </div>
      </div>
    </section>
  );
}
