from django.contrib import admin

from apps.core.admin_site import partonoor_admin_site

from .models import AboutSection, TeamMember, WorkshopSection


@admin.register(TeamMember, site=partonoor_admin_site)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "display_order", "published")
    list_editable = ("display_order", "published")
    search_fields = ("name", "role")


@admin.register(AboutSection, site=partonoor_admin_site)
class AboutSectionAdmin(admin.ModelAdmin):
    list_display = ("block_type", "title", "display_order", "published")
    list_editable = ("display_order", "published")


@admin.register(WorkshopSection, site=partonoor_admin_site)
class WorkshopSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "published")
    list_editable = ("display_order", "published")
