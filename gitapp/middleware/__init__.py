# coding: utf-8

from django.utils.deprecation import MiddlewareMixin


class TransitMiddleware(MiddlewareMixin):
    """
    This Middleware class ensures there is a transit created for any existing project if
    the request user is logged in
    """
    def process_request(self, request):
        user = request.user
        if request.session:
            if user:
                try:
                    repo = getattr(user, 'my_repo', None)
                    if repo and not request.session.get('transit_created', False):
                        projects = repo.projects_in_repo.all()
                        [project.update_transit() for project in projects]
                        request.session['transit_created'] = True
                        request.session.save()
                except AttributeError:
                    pass
