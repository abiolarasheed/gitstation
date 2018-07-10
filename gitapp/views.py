# coding: utf-8

import os
import time
from subprocess import Popen, PIPE
from wsgiref.util import FileWrapper

from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, Http404
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.encoding import smart_str
from django.urls import reverse_lazy, reverse
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db.models import Q, F
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.generic import (CreateView, ListView, DetailView, UpdateView,
                                  DeleteView, TemplateView, FormView)
from django.utils import timezone
from django.views.generic import View

from django.db import transaction

from gitapp import gitHttpBackend
from gitapp.forms import WikiUpdateForm
from gitapp.mixins import WikiMixin
from gitapp.models import Wiki
from .utils import (view_if_public, get_project_repo,
                    delete_key, get_code_n_count, cd, markdown_2_html,
                    get_language_via_ext, get_thumb_url, get_relative_and_full_path
                    )
from .forms import (CreateProjectForm, LoginForm, UserCreationForm, WikiForm,
                    ChangePasswordForm, ChangeEmailForm,
                    SshKeyForm, GnuPgKeyForm, AddEmailForm, EditFile)
from .models import Project, Repo, Star, Email, CommitFactory
from .tables import (format_repo_2_table, ProjectListTable, KeyTable, EmailTable,
                     ProjectFilesTable, dynamic_format_repo_2_table)


@method_decorator(view_if_public, name='dispatch')
class DisplayFileView(TemplateView):
    template_name = 'gitapp/code.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repo_name = kwargs.get("repo_name")
        project_name = kwargs.get("project_name")

        path = '{0}/{1}.git'.format(repo_name, project_name)
        project = get_object_or_404(Project, repo__name=repo_name, path=path)

        code = size = num_lines = lang = None
        file_path = self.request.META.get('PATH_INFO', '/')
        relative_path = file_path.replace(settings.SOURCE + '/', '')
        relative_path = '/'.join([path for path in filter(None, relative_path.split('/'))])
        full_path = os.path.join(settings.TRANSIT_POINT, relative_path)
        file_path = full_path

        if file_path == '/' or not os.path.exists(full_path):
            raise Http404

        else:
            if os.path.isdir(file_path):
                table = dynamic_format_repo_2_table(project, file_path)
                self.template_name = 'gitapp/specific_project.html'
                context.update({'project': project, 'table': table})
                return context

            elif os.path.isfile(file_path):
                list_or_str = get_code_n_count(file_path)
                if type(list_or_str) == str:
                    return redirect(list_or_str)

                code, num_lines, size = list_or_str
                filename = os.path.split(file_path)[-1]
                context.update({'filename': filename})
                file_ = os.path.splitext(filename)[0]
                if file_.lower() == 'readme':
                    code = markdown_2_html(code)

                ext = os.path.splitext(file_path)[-1]
                if ext:
                    if ext in ['rm', 'rst', 'html']:
                        lang = 'html'
                    else:
                        lang = get_language_via_ext(ext)

            if lang is None:
                with cd(project.working_dir):
                    command = ['file', file_path]
                    process = Popen(command, stdout=PIPE, stderr=PIPE)
                    result = process.communicate()[0].decode("utf-8")
                    lang = result.split(',')[0].split(': ')[-1].replace('script', '').split(' ')[0].strip().lower()

            n_relative_path = '/'.join([i for i in filter(None, relative_path.split('/'))
                                        if i not in (repo_name, project_name)])
            history_url = reverse('file_history', args=[repo_name, project_name, n_relative_path])
            edit_url = reverse('edit_file', args=[repo_name, project_name, n_relative_path])
            text_url = reverse('render_file_as_text', args=[repo_name, project_name, n_relative_path])

            context.update({'code': code, 'num_lines': num_lines,
                            'size': size, 'project': project, 'lang': lang,
                            'history_url': history_url, 'text_url': text_url,
                            'edit_url': edit_url})

            return context


@method_decorator(view_if_public, name='dispatch')
class RenderFileAsTextView(TemplateView):
    template_name = 'gitapp/text.html'
    full_path = None

    def get_context_data(self, **kwargs):
        self.full_path = get_relative_and_full_path(self.request.META.get('PATH_INFO', '/'),
                                                    path=settings.TEXT_PATH)[1]
        if self.full_path == '/' or not os.path.exists(self.full_path) or os.path.isdir(self.full_path):
            raise Http404
        context = {}
        code = get_code_n_count(self.full_path)[0]
        context.update({'code': code})
        return context


@method_decorator(view_if_public, name='dispatch')
@method_decorator(login_required, name='dispatch')
class EditCodeView(FormView):
    template_name = 'gitapp/edit.html'
    form_class = EditFile
    full_path = None

    def dispatch(self, request, *args, **kwargs):
        self.full_path = get_relative_and_full_path(request.META.get('PATH_INFO', '/'),
                                                    path=settings.EDIT_PATH)[1]

        if self.full_path == '/' or not os.path.exists(self.full_path) or os.path.isdir(self.full_path):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        url = self.request.META.get('PATH_INFO')
        code = get_code_n_count(self.full_path)[0]

        if self.request.method == 'POST':
            form = EditFile(self.request.POST, url=url, code=code)
        else:
            form = EditFile({'content': code,
                             'choice_branch': 'current'},
                            url=url, code=None
                            )

        return form


@method_decorator(login_required, name='dispatch')
class ChangePasswordView(UpdateView):
    template_name = 'gitapp/password.html'
    form_class = ChangePasswordForm

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request.user, data=self.request.POST or None)


@method_decorator(login_required, name='dispatch')
class ViewPasswordView(TemplateView):
    template_name = 'gitapp/password.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update({'form': ChangePasswordForm(user)})
        return context


@method_decorator(login_required, name='dispatch')
class AddEmailView(CreateView):
    form_class = AddEmailForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

    def form_invalid(self, form):
        return redirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        email = form.save(commit=False)
        email.user = self.request.user
        email.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class ChangeEmail(CreateView, UpdateView):
    form_class = ChangeEmailForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

    def form_invalid(self, form):
        return redirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


@method_decorator(login_required, name='dispatch')
class EmailsDetailView(TemplateView):
    template_name = 'gitapp/emails.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        emails = [{'email': user.email}]
        qs = Email.objects.filter(user=user).order_by('id')

        if qs.exists():
            [emails.append({'email': email_obj.email}) for email_obj in qs]

        table = EmailTable(emails)
        context.update({'email_change_form': ChangeEmailForm(user=user),
                        'add_email_form': AddEmailForm(user=user),
                        'table': table,
                        })
        return context


@method_decorator(login_required, name='dispatch')
class SshKeyDetailView(TemplateView):
    template_name = 'gitapp/sshkeys.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update({'form': SshKeyForm(user=user),
                        'table': KeyTable(user.sshkey_set.all().order_by('id')),
                        })

        return context


@method_decorator(login_required, name='dispatch')
class CreateSshKeyView(CreateView):
    form_class = SshKeyForm

    def get_form_kwargs(self):
        kwargs = {"user": self.request.user}
        return kwargs

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

    def form_valid(self, form):
        keys = form.save(commit=False)
        keys.user = self.request.user
        keys.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class DeleteSshKeyView(DetailView):
    def get(self, request, *args, **kwargs):
        if request.user.username != kwargs["username"]:
            raise PermissionDenied

        delete_key(request.user, kwargs["pk"], 'sshkey')
        move_next = request.META.get('HTTP_REFERER', '/')
        return redirect(move_next)


@method_decorator(login_required, name='dispatch')
class ViewGpgKeysView(TemplateView):
    template_name = 'gitapp/gnupgkeys.html'

    def get_context_data(self, **kwargs):
        user = self.request.user

        return {'form': GnuPgKeyForm(user=user),
                'table': KeyTable(user.gnupgkey_set.all().order_by('id')),
                }


@method_decorator(login_required, name='dispatch')
class CreateGpgKeysView(CreateView):
    form_class = GnuPgKeyForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

    def form_valid(self, form):
        gpgkey = form.save(commit=False)
        gpgkey.user = self.request.user
        gpgkey.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class DeleteGpgKeysView(DetailView):
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.username != self.kwargs.get("username"):
            raise PermissionDenied
        delete_key(user, self.kwargs.get("pk"), 'gnupgkey')
        move_next = request.META.get('HTTP_REFERER', '/')
        return redirect(move_next)


@method_decorator(view_if_public, name='dispatch')
class ChangeRepoStatusView(UpdateView):
    template_name = 'generic_form.html'

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

    def get_object(self, queryset=None):
        obj = get_object_or_404(Project, slug=self.kwargs.get("slug"))
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        is_private = {'public': False, 'private': True}
        status = is_private.get(kwargs.get("status"), True)
        kwargs.update({'status': status})
        return kwargs


@method_decorator(view_if_public, name='dispatch')
class ListCommitsView(DetailView):
    template_name = 'gitapp/commit_default.html'
    context_object_name = "project"

    def get_object(self, queryset=None):
        return get_object_or_404(Project,
                                 repo__name=self.kwargs.get("repo_name"),
                                 name=self.kwargs.get("project_name"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = context["project"]

        user = project.repo.owner
        commits = project.commits()
        all_commits = CommitFactory(commits)

        page = self.request.GET.get('page')
        context.update({'repo': project, 'user': user,
                       'commits': all_commits.get_commits_page(page)})

        if self.request.GET.get('time_line'):
            self.template_name = 'gitapp/commits_timeline.html'
            alt_path = self.request.META.get('PATH_INFO').replace('?time_line=True', '')
        else:
            alt_path = '{0}?time_line=True'.format(self.request.META.get('PATH_INFO'))

        context.update({'alt_path': alt_path})
        return context


class UserWallView(DetailView):
    template_name = 'gitapp/wall.html'
    context_object_name = "user"

    def get_object(self, queryset=None):
        return get_object_or_404(User,
                                 username=self.kwargs.get("username"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = context.get("user")

        public_repos = user.my_repo.projects_in_repo.filter(is_private=False)
        size = str(settings.PROFILE_THUMB_LARGE[0])
        url = get_thumb_url(user, size, cache_name='thumb')
        context.update({'user': user, 'url': url, 'public_repos': public_repos,
                        'today': timezone.now()})
        return context


@method_decorator(view_if_public, name='dispatch')
@method_decorator(login_required, name='dispatch')
class UpdateRepoStarsView(View):
    @staticmethod
    def get(request, slug):
        project = Project.objects.get(slug=slug)

        try:
            with transaction.atomic():
                star = Star.objects.select_for_update().get(id=project.current_stars.latest().id)
                if request.user not in star.user.all():
                    total = star.total + 1
                    star.update(total=total)
                    star.user.add(request.user)
                    star = Star(project=project)
                    star.save()
                    star.user.add(request.user)
        except Star.DoesNotExist:
            star = Star(project=project)
            star.save()
            star.user.add(request.user)

        return redirect(request.META.get('HTTP_REFERER'))


class MyLoginView(LoginView):
    template_name = "login.html"
    authentication_form = LoginForm
    success_url = reverse_lazy('profile')


class UserRegistrationView(CreateView):
    template_name = "login.html"
    form_class = UserCreationForm
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        password = self.request.POST.get('password1')
        user = form.save()
        user = authenticate(username=user.username, password=password)
        login(self.request, user)
        repo = Repo(owner=user, name=user.username)
        repo.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class AccountView(ListView):
    template_name = "gitapp/profile.html"

    def get_queryset(self):
        return self.request.user.my_repo.projects_in_repo.all()

    def get_context_data(self, *, object_list=None, **kwargs):
        repos = self.get_queryset()

        context = super().get_context_data(**kwargs)
        context["table"] = ProjectListTable(repos)
        context["total_repos"] = repos.count()
        context["form"] = CreateProjectForm()
        return context


@method_decorator(login_required, name='dispatch')
class CreateProjectView(CreateView):
    template_name = "gitapp/project_form.html"
    success_url = reverse_lazy('profile')
    fields = ("name", 'description', 'is_private', 'poster')
    model = Project

    def form_valid(self, form):
        user = self.request.user
        project_name = form.cleaned_data.get('name')

        try:
            repo = user.my_repo
        except AttributeError:
            repo = Repo(owner=user, name=user.username)
            repo.save()

        try:
            Project.objects.get(name=project_name, repo=repo)
        except Project.DoesNotExist:
            project = form.save(commit=False)
            project.repo = repo
            project.save()
            self.success_url = reverse_lazy('specific_project',
                                            args=(repo.name, project.name))
            project.update_transit()
        return super().form_valid(form)


@method_decorator(view_if_public, name='dispatch')
class ProjectDetailView(DetailView):
    template_name = 'gitapp/project_detail.html'
    context_object_name = 'project'
    model = Project

    def get_object(self, queryset=None):
        project_name = "{0}.git".format(self.kwargs["project_name"])
        return get_object_or_404(Project,
                                 repo__name=self.kwargs["repo_name"],
                                 path__endswith=project_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = context["project"]

        table = format_repo_2_table(project)
        readme_file = project.get_readme_file()

        context.update({'table': table,
                        'user': project.repo.owner,
                        'readme_file': readme_file}
                       )
        return context


@method_decorator(view_if_public, name='dispatch')
class WikiDetailView(DetailView):
    template_name = 'gitapp/read_wiki.html'
    context_object_name = 'wiki'
    model = Wiki

    def get_object(self, queryset=None):
        project = get_project_repo(self.kwargs["repo_name"],
                                   self.kwargs["project_name"])
        return project.my_wiki

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'project': context["wiki"].project})
        return context


@method_decorator(login_required, name="dispatch")
class CreateWikiView(WikiMixin, CreateView):
    template_name = 'generic_form.html'
    form_class = WikiForm

    def form_valid(self, form):
        wiki = form.save(commit=False)
        wiki.project = get_project_repo(self.kwargs["repo_name"],
                                        self.kwargs["project_name"])
        wiki.save()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(view_if_public, name='dispatch')
class UpdateWikiView(WikiMixin, UpdateView):
    template_name = 'generic_form.html'
    form_class = WikiUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'instance': self.get_object()})
        return kwargs


@method_decorator(login_required, name="dispatch")
class WikiDeleteView(WikiMixin, DeleteView):
    model = Wiki
    template_name = "gitapp/wiki_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("specific_project",
                            args=(self.kwargs["repo_name"],
                                  self.kwargs["project_name"]))

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
@method_decorator(view_if_public, name='dispatch')
class FilesInRepo(TemplateView):
    template_name = 'gitapp/list_files_in_repo.html'

    def get_context_data(self, **kwargs):
        try:
            project = Project.objects.get(Q(repo__name=self.kwargs["repo_name"]),
                                          Q(name=self.kwargs["project_name"]) |
                                          Q(name=self.kwargs["project_name"].replace('_', ' ')))
            user = project.repo.owner
            repo_files = project.list_repo_files()
            data = []
            [data.append({'file': file_name}) for file_name in repo_files]
            table = ProjectFilesTable(data)
            return {'project': project,
                    'user': user,
                    'table': table}
        except Project.DoesNotExist:
            raise Http404


@method_decorator(login_required, name="dispatch")
class GitView(View):
    """
    This view handles all git commands
    """
    def dispatch(self, request, *args, **kwargs):
        try:
            user = request.user.username
        except AttributeError:
            user = None

        status_line, headers, response_body_generator = \
            gitHttpBackend.wsgi_to_git_http_backend(request.META,
                                                    settings.REPO_PATH,
                                                    user=user)

        response = HttpResponse(response_body_generator,
                                status=int(status_line[:3]))
        headers = dict((key, values) for key, values in headers)

        for key, values in headers.items():
            setattr(response, key, values)

        return response


@method_decorator(view_if_public, name='dispatch')
class HistoryView(TemplateView):
    """
    Show diff on file
    """
    template_name = 'gitapp/history.html'

    def get_context_data(self, **kwargs):
        _, full_path = get_relative_and_full_path(self.request.META.get('PATH_INFO', '/'),
                                                  path=settings.EDIT_PATH)
        project = get_object_or_404(Project,
                                    repo__name=self.kwargs["repo_name"],
                                    name=self.kwargs["project_name"])
        with cd(project.working_dir):
            command = ['git', 'diff', 'HEAD^^', 'HEAD', full_path]
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            result = process.communicate()[0].decode("utf-8")

        return {'result': result}


class EncodingErrorView(TemplateView):
    template_name = 'error.html'

    def get_context_data(self, **kwargs):
        error_message = _('The file You Are Trying To open as Encoding Error')
        context = super().get_context_data(**kwargs)
        context.update({'error_message': error_message})
        return context


@method_decorator(view_if_public, name='dispatch')
class DownloadView(View):
    def dispatch(self, request, *args, **kwargs):
        repo_name = kwargs.get("repo_name")
        project_name = kwargs.get("project_name").split('.')

        project_name = project_name.split('.')
        compression_type = '.'.join(project_name[1:])
        path = '{0}/{1}.git'.format(repo_name, project_name[0])
        project = get_object_or_404(Project, repo__name=repo_name, path=path)
        project.compress_project(compression=compression_type)
        file_path = smart_str(project.compress_project(return_path=True, compression=compression_type))

        with open(file_path, 'rb') as file_content:
            response = HttpResponse(FileWrapper(file_content), content_type="application/force-download")
            response['Content-Disposition'] = 'attachment; filename={0}; filename*=UTF-8''{0}' \
                .format(smart_str(project.compress_project(return_compressed_dir=True, compression=compression_type)))

            try:
                response['Content-Length'] = os.path.getsize(file_path)
            except (AttributeError, NotImplementedError):
                pass  # Generated files.

            response['Content-Encoding'] = 'utf-8'
            Project.objects.filter(repo__name=repo_name, path=path).update(downloads=F('downloads') + 1)
            file_path_not_exist = True

            while file_path_not_exist:
                time.sleep(6)  # Sleep while compressing is going on in background
                if os.path.exists(file_path):
                    file_path_not_exist = False
        return response
