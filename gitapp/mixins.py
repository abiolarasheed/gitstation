# coding: utf-8

from django.urls import reverse_lazy

from gitapp.utils import get_project_repo


class WikiMixin:
    """
    This mixing is used to provide context to Wiki forms and to redirect to Wiki detail view on success
    """
    kwargs = None
    form_class = None

    def form_valid(self, form):
        pass

    def form_invalid(self, form):
        pass

    def get_object(self):
        project = get_project_repo(self.kwargs["repo_name"],
                                   self.kwargs["project_name"])
        return project.my_wiki

    def get_success_url(self):
        return reverse_lazy("read_wiki",
                            args=(self.kwargs["repo_name"],
                                  self.kwargs["project_name"]))

    def get_form_kwargs(self):
        kwargs = {'repo_name': self.kwargs["repo_name"],
                  'project_name': self.kwargs["project_name"]
                  }
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST,
                               **self.get_form_kwargs())

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
