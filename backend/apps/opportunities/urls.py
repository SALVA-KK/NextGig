from django.urls import path

from .views import (
    ApplicationCreateView,
    ApplicationResumeDownloadView,
    ApplicationStatusUpdateView,
    MyApplicationsListView,
    OpportunityApplicantsListView,
    OpportunityDetailView,
    OpportunityListCreateView,
    OpportunitySaveView,
    ReceivedApplicationsListView,
    RecommendedOpportunitiesListView,
    SavedOpportunityListView,
)

app_name = "opportunities"

urlpatterns = [
    path("", OpportunityListCreateView.as_view(), name="opportunity-list-create"),
    path("recommended/", RecommendedOpportunitiesListView.as_view(), name="recommended-opportunities-list"),
    path("<int:pk>/", OpportunityDetailView.as_view(), name="opportunity-detail"),
    path("<int:pk>/save/", OpportunitySaveView.as_view(), name="opportunity-save"),
    path("<int:pk>/apply/", ApplicationCreateView.as_view(), name="opportunity-apply"),
    path("<int:pk>/applicants/", OpportunityApplicantsListView.as_view(), name="opportunity-applicants"),
    path("applications/received/", ReceivedApplicationsListView.as_view(), name="received-applications-list"),
    path("applications/<int:pk>/resume/", ApplicationResumeDownloadView.as_view(), name="application-resume-download"),
    path("saved-opportunities/", SavedOpportunityListView.as_view(), name="saved-opportunity-list"),
]

