"""
Launch Track URL configuration.

All routes are relative to /api/v1/launch/ (set in config/urls.py).
"""

from django.urls import path

from apps.launch import views

app_name = "launch"

urlpatterns = [
    # ── Project Endpoints ──
    # POST /api/v1/launch/projects/              → Create project (Admin)
    path(
        "projects/",
        views.CreateLaunchProjectView.as_view(),
        name="create-project",
    ),
    # GET  /api/v1/launch/projects/              → List projects (Authenticated)
    path(
        "projects/list/",
        views.LaunchProjectListView.as_view(),
        name="list-projects",
    ),
    # GET  /api/v1/launch/projects/{id}/         → Project detail (Authenticated)
    # DELETE /api/v1/launch/projects/{id}/       → Delete project (Admin)
    path(
        "projects/<int:project_id>/",
        views.LaunchProjectDetailView.as_view(),
        name="project-detail",
    ),
    # POST /api/v1/launch/projects/{id}/apply/   → Apply (Student, GI done)
    path(
        "projects/<int:project_id>/apply/",
        views.ApplyToProjectView.as_view(),
        name="apply",
    ),
    # GET  /api/v1/launch/projects/{id}/applicants/ → View applicants (Admin/Ops)
    path(
        "projects/<int:project_id>/applicants/",
        views.ProjectApplicantsView.as_view(),
        name="project-applicants",
    ),

    # ── Application Management (Admin/Ops) ──
    # POST /api/v1/launch/applications/filter/       → Bulk filter (Admin/Ops)
    path(
        "applications/filter/",
        views.FilterApplicationsView.as_view(),
        name="filter-applications",
    ),
    # POST /api/v1/launch/applications/send-to-team/ → Send to team (Admin/Ops)
    path(
        "applications/send-to-team/",
        views.SendToTeamView.as_view(),
        name="send-to-team",
    ),

    # ── Student Self-Service ──
    # GET /api/v1/launch/my-applications/  → View own apps (Student)
    path(
        "my-applications/",
        views.MyApplicationsView.as_view(),
        name="my-applications",
    ),

    # ── Launch Team Candidate Actions ──
    # GET  /api/v1/launch/candidates/              → View candidates (Launch Team)
    path(
        "candidates/",
        views.LaunchTeamCandidatesView.as_view(),
        name="candidates",
    ),
    # POST /api/v1/launch/candidates/{id}/select/  → Select (Launch Team)
    path(
        "candidates/<int:candidate_id>/select/",
        views.SelectCandidateView.as_view(),
        name="select-candidate",
    ),
    # POST /api/v1/launch/candidates/{id}/reject/  → Reject (Launch Team)
    path(
        "candidates/<int:candidate_id>/reject/",
        views.RejectCandidateView.as_view(),
        name="reject-candidate",
    ),
]