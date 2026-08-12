import React from 'react';

export default function Footer() {
  return (
    <footer className="home-footer">
      <div className="home-footer-container">
        <div className="home-footer-brand">
          <div className="brand-logo">N</div>
          <span className="brand-name">NextGig</span>
        </div>
        <p className="home-footer-copy">
          © {new Date().getFullYear()} NextGig. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
