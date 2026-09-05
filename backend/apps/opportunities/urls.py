from django.urls import path

from .views import (
    ApplicationCreateView,
    ApplicationStatusUpdateView,
    MyApplicationsListView,
    OpportunityApplicantsListView,
    OpportunityDetailView,
    OpportunityListCreateView,
    OpportunitySaveView,
    SavedOpportunityListView,
)

app_name = "opportunities"

urlpatterns = [
    path("", OpportunityListCreateView.as_view(), name="opportunity-list-create"),
    path("<int:pk>/", OpportunityDetailView.as_view(), name="opportunity-detail"),
    path("<int:pk>/save/", OpportunitySaveView.as_view(), name="opportunity-save"),
    path("<int:pk>/apply/", ApplicationCreateView.as_view(), name="opportunity-apply"),
    path("<int:pk>/applicants/", OpportunityApplicantsListView.as_view(), name="opportunity-applicants"),
    path("saved-opportunities/", SavedOpportunityListView.as_view(), name="saved-opportunity-list"),
]
