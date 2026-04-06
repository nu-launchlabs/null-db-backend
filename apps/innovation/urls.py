"""
Innovation Track URL routing.

All URLs are prefixed with /api/v1/innovation/ (from config/urls.py).
"""

from django.urls import path

from apps.innovation.views import (
    ApproveProposalView,
    AssignToInnovationView,
    InnovationProjectDetailView,
    InnovationProjectListView,
    MyPreferencesView,
    MyProposalView,
    ProjectPreferencesView,
    ProposalListView,
    RejectProposalView,
    SubmitPreferencesView,
    SubmitProposalView,
)

app_name = "innovation"

urlpatterns = [
    # Proposals
    path(
        "proposals/",
        SubmitProposalView.as_view(),
        name="submit-proposal",
    ),
    path(
        "proposals/list/",
        ProposalListView.as_view(),
        name="proposal-list",
    ),
    path(
        "proposals/<int:proposal_id>/approve/",
        ApproveProposalView.as_view(),
        name="approve-proposal",
    ),
    path(
        "proposals/<int:proposal_id>/reject/",
        RejectProposalView.as_view(),
        name="reject-proposal",
    ),
    path(
        "my-proposal/",
        MyProposalView.as_view(),
        name="my-proposal",
    ),
    # Projects
    path(
        "projects/",
        InnovationProjectListView.as_view(),
        name="project-list",
    ),
    path(
        "projects/<int:project_id>/",
        InnovationProjectDetailView.as_view(),
        name="project-detail",
    ),
    # Preferences
    path(
        "preferences/",
        SubmitPreferencesView.as_view(),
        name="submit-preferences",
    ),
    path(
        "my-preferences/",
        MyPreferencesView.as_view(),
        name="my-preferences",
    ),
    path(
        "projects/<int:project_id>/preferences/",
        ProjectPreferencesView.as_view(),
        name="project-preferences",
    ),
    # Assignment
    path(
        "assign/",
        AssignToInnovationView.as_view(),
        name="assign-to-innovation",
    ),
]