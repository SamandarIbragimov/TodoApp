from django.contrib import admin

from .models import Project, ProjectInvitation, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    autocomplete_fields = ('user',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    inlines = [ProjectMemberInline]


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'joined_at')
    list_filter = ('role',)


@admin.register(ProjectInvitation)
class ProjectInvitationAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'status', 'invited_by', 'created_at')
    list_filter = ('status', 'role')
