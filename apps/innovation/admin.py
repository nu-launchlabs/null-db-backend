from django.contrib import admin

from apps.innovation.models import InnovationPreference, InnovationProject, Proposals


@admin.register(Proposals)
class ProposalsAdmin(admin.ModelAdmin):
    list_display = ["title", "proposer", "cycle", "status", "submitted_at"]
    list_filter = ["status", "cycle"]
    search_fields = ["title", "proposer__email"]
    readonly_fields = ["submitted_at"]


@admin.register(InnovationProject)
class InnovationProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "lead", "cycle", "max_members", "created_at"]
    list_filter = ["cycle"]
    search_fields = ["title", "lead__email"]
    readonly_fields = ["created_at"]


@admin.register(InnovationPreference)
class InnovationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "cycle", "rank", "submitted_at"]
    list_filter = ["cycle", "rank"]
    search_fields = ["user__email", "project__title"]
    readonly_fields = ["submitted_at"]