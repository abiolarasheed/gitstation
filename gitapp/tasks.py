# coding: utf-8

from gitstation import celery_app


@celery_app.task(ignore_result=True)
def update_transit(project_id):
    """
    This task updates a project's transit path in the background.
    :param str project_id: Project id
    :return:
    """
    from .models import Project
    project = Project.objects.get(id=project_id)
    project.update_transit()
