import React from 'react';
import { Link } from 'react-router-dom';

export default function Navbar() {
  return (
    <header className="home-navbar">
      <div className="home-navbar-container">
        {/* NextGig Branding Logo & Name */}
        <Link to="/" className="sidebar-brand" style={{ padding: 0 }}>
          <div className="brand-logo">N</div>
          <span className="brand-name">NextGig</span>
        </Link>

        {/* Minimal Navigation Links */}
        <nav className="home-nav-links">
          <Link to="/" className="home-nav-link active">
            Home
          </Link>
          <a href="#about" className="home-nav-link">
            About
          </a>
        </nav>

        {/* Action Buttons */}
        <div className="home-auth-actions">
          <Link to="/login" className="btn-secondary-link" id="nav-signin-btn">
            Sign In
          </Link>
          <Link to="/register" className="btn-primary-sm" id="nav-getstarted-btn">
            Get Started
          </Link>
        </div>
      </div>
    </header>
  );
}
