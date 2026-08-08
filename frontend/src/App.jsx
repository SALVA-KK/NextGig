import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/auth/Login';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        {/* Placeholder routes to prevent 404 links during demo */}
        <Route
          path="/register"
          element={
            <div style={{ padding: 40, textAlign: 'center' }}>
              <h2>Register Page Placeholder</h2>
              <p>Registration flow will be integrated here.</p>
              <a href="/login" style={{ color: '#a78bfa', marginTop: 16, display: 'inline-block' }}>
                Back to Login
              </a>
            </div>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <div style={{ padding: 40, textAlign: 'center' }}>
              <h2>Forgot Password Placeholder</h2>
              <p>Forgot password flow will be integrated here.</p>
              <a href="/login" style={{ color: '#a78bfa', marginTop: 16, display: 'inline-block' }}>
                Back to Login
              </a>
            </div>
          }
        />
        {/* Default Redirect to Login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
