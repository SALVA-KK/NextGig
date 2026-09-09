/**
 * Navigation role permissions helper utility for NextGig frontend.
 * Provides a single source of truth for role checks across Sidebar and Header dropdown.
 */
export function getNavPermissions(userRole, isAdminFlag = false) {
  const role = userRole || 'student';
  const isAdmin = role === 'admin' || Boolean(isAdminFlag);
  const isProvider = role === 'provider';
  const isStudent = role === 'student' || (!isProvider && !isAdmin);

  return {
    role,
    isStudent,
    isProvider,
    isAdmin,

    // Navigation Item Visibility Flags
    canViewApplications: isStudent && !isAdmin,
    canViewSavedItems: (isStudent || isProvider) && !isAdmin,
    profileLabel: isStudent ? 'Profile & Resumes' : 'Profile',
  };
}
