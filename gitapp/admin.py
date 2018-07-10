# coding: utf-8

from django.contrib import admin
from .models import Project, Repo, Wiki, ProjectPermission


class ProjectAdmin(admin.ModelAdmin):
    search_fields = ['name', 'date_created', 'date_updated', 'repo']
    list_display = ['name', 'date_created', 'date_updated', 'repo']


class RepoAdmin(admin.ModelAdmin):
    search_fields = ['name', 'owner']
    list_display = ['name', 'owner']


class WikiAdmin(admin.ModelAdmin):
    search_fields = ['date_created', 'date_updated', 'project']
    list_display = ['date_created', 'date_updated', 'project']


class ProjectPermissionAdmin(admin.ModelAdmin):
    search_fields = ['permissions', 'project', 'user']
    list_display = ['permissions', 'project', 'user']


admin.site.register(Wiki, WikiAdmin)
admin.site.register(Repo, RepoAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectPermission, ProjectPermissionAdmin)
