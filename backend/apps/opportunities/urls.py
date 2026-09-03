from django.urls import path

from .views import OpportunityDetailView, OpportunityListCreateView

app_name = "opportunities"

urlpatterns = [
    path("", OpportunityListCreateView.as_view(), name="opportunity-list-create"),
    path("<int:pk>/", OpportunityDetailView.as_view(), name="opportunity-detail"),
]
