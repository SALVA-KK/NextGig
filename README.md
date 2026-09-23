# NextGig — Student Opportunity Hub

NextGig is a full-stack student opportunity hub designed to connect students and job seekers with recruiters, organizations, and other opportunity providers.

The platform allows users to create professional profiles, discover relevant opportunities, apply for them, and connect with other users. Recruiters and providers can create and manage opportunities and discover suitable candidates.

## Features

### 👤 User Features

- User registration and login
- Email verification
- Phone OTP verification
- JWT-based authentication
- Password reset and password change
- Professional user profiles
- Profile editing
- Profile sharing through invitation links
- Discover available opportunities
- Apply for opportunities

### 💼 Opportunity Management

- Providers can create opportunities
- Providers can edit and manage their opportunities
- Users can browse and apply for opportunities
- Opportunity status management
- Admin moderation of opportunities

### 🛡️ Admin Features

- Admin dashboard
- User management
- User activation and deactivation
- Role management
- Opportunity management and moderation
- Admin multi-factor authentication (MFA)
- Recovery codes for MFA

### 🔐 Security

- JWT authentication
- Role-based authorization
- Password hashing
- Email verification
- Phone OTP verification
- JWT token blacklisting
- Admin MFA using TOTP
- Protected API endpoints

### 🔗 Invitation System

Users can generate unique invitation links and share them with others.

The invitation system tracks:

- Who created the invitation
- Whether the invitation has been used
- Which user accepted it
- Invitation expiration

## Technology Stack

### Frontend

- React
- Vite
- React Router
- JavaScript
- CSS

### Backend

- Python
- Django
- Django REST Framework

### Database

- PostgreSQL

### Services

- MSG91 — SMS/OTP
- Email service — account verification and password recovery

## Project Structure

```text
NextGig/
├── frontend/
│   ├── src/
│   ├── public/
│   └── ...
│
├── backend/
│   ├── apps/
│   ├── config/
│   └── ...
│
└── README.md
