import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Reusable authentication layout wrapper for centering cards,
 * providing NextGig branding header, and consistent responsive design.
 */
export default function AuthLayout({ children, title, subtitle }) {
  return (
    <div className="auth-container">
      <div className="auth-card">
        {/* NextGig Branding Badge */}
        <Link to="/" className="auth-brand">
          <div className="brand-logo">N</div>
          <span className="brand-name">NextGig</span>
        </Link>


        {/* Dynamic Title & Subtitle */}
        {title && <h1 className="auth-title">{title}</h1>}
        {subtitle && <p className="auth-subtitle">{subtitle}</p>}

        {/* Main Content Area */}
        <div className="auth-body">{children}</div>
      </div>
    </div>
  );
}
