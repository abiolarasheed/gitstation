# coding: utf-8

import os

from django.core.management.base import BaseCommand

from django.conf import settings
from ...models import Project, User, Repo
from ...utils import cd


def make_user_n_repo(folder_name, return_user=False):
    try:
        user = User.objects.get(username=folder_name)
    except User.DoesNotExist:
        user = User(username=folder_name)
        user.set_unusable_password()
        user.save()

    try:
        Repo.objects.get(owner=user, name=user.username)
    except Repo.DoesNotExist:
        repo = Repo(owner=user, name=user.username)
        repo.save()

    if return_user:
        return user


def create_project(user, project_name):
    """
    Create a new repo project.
    :param user:
    :param project_name:
    :return:
    """
    try:
        repo = user.my_repo
    except AttributeError:
        repo = Repo(owner=user, name=user.username)
        repo.save()
    try:
        Project.objects.get(name=project_name, repo=repo)
    except Project.DoesNotExist:
        project = Project(name=project_name, repo=repo)
        project.save()


def create_repo_n_project(folder_name):
    user = make_user_n_repo(folder_name, return_user=True)

    with cd(folder_name):
        folders = [folder.replace('.git', '') for folder in os.listdir(os.getcwd()) if folder]
        [create_project(user, folder) for folder in folders]
                

class Command(BaseCommand):
    help = " This helps Creates repo from existing file system. "

    @staticmethod
    def handle_noargs(**options):
        with cd(settings.REPO_PATH):
            projects = Project.objects.all()
            folders_in_db = [project.repo.owner.__str__() for project in projects]

            folders_on_fill_sys = [folder for folder in os.listdir(os.getcwd()) if folder not in settings.EXCLUDE_DIRS]
            folders_not_in_db = set(folders_on_fill_sys).difference(set(folders_in_db))

            if folders_not_in_db:
                [create_repo_n_project(folder_name) for folder_name in folders_not_in_db]
