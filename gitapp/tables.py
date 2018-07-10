# coding: utf-8

from django.utils.translation import ugettext_lazy as _

import django_tables2 as tables

from .models import RepoFile


class EmailTable(tables.Table):
    email = tables.EmailColumn(accessor='email', verbose_name=_("Email"),)

    class Meta:
        attrs = {"class": "table table-bordered table-condensed content-box gs-profile"}


class ProjectTable(tables.Table):
    file_name = tables.Column(accessor="wrap_folder", verbose_name=_("files"), )
    commit = tables.Column(accessor="last_commit", verbose_name=_("Message"))
    last_modified = tables.Column(accessor="file_last_modified", verbose_name=_("Last Modified"))

    class Meta:
        attrs = {"class": "table table-bordered table-condensed content-box col-md-9"}


class ProjectFilesTable(tables.Table):
    file_name = tables.Column(accessor="file", verbose_name=_("files"),)

    class Meta:
        attrs = {"class": "table table-bordered table-condensed content-box col-md-9"}


class ProjectListTable(tables.Table):
    name = tables.Column(accessor="display_in_profile", verbose_name=_("Current Projects"),)

    class Meta:
        attrs = {"class": "table table-bordered col-md-3"}


class KeyTable(tables.Table):
    title = tables.Column(accessor="title", verbose_name=_("title"), )
    key = tables.Column(accessor="has_md_key", verbose_name=_("key"),
                        attrs={"th": {'class': 'muted'}})
    date_created = tables.DateColumn(accessor='date_created', verbose_name=_("Date Created"))
    delete_key = tables.Column(accessor='delete_btn', verbose_name=_("Delete"))

    class Meta:
        attrs = {"class": "table table-bordered table-condensed content-box gs-profile"}


def format_repo_2_table(project):
    wrapped_list_folder = project.wrapped_list_folder()
    repos = [RepoFile(cwd=project.working_dir, file_n_folder=file_n_folder)
             for file_n_folder in wrapped_list_folder]
    return ProjectTable(repos)


def dynamic_format_repo_2_table(project, current_path):
    cwd = project.working_dir

    repos = [RepoFile(cwd=cwd, file_n_folder=file_n_folder, project=project)
             for file_n_folder in project.wrapped_given_folder_list(current_path)]
    return ProjectTable(repos)
