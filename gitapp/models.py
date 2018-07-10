# coding: utf-8

from collections import OrderedDict
import os
import hashlib
from subprocess import Popen, PIPE

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils import six
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.utils.html import mark_safe, format_html

from autoslug import AutoSlugField
from polymorphic.models import PolymorphicModel
from polymorphic.showfields import ShowFieldTypeAndContent

from gitapp.utils import detect_file_type
from .exception import ProjectUserPermissionError
from .utils import (make_path, cd, return_files_in_dir, filename_normalizer, normalize_link,
                    get_date_from_git, CommitParser)


can_clone, can_create_branch, can_delete_branch, can_pull, can_push = range(5)

PERMISSIONS = (
               (can_clone, 'Can Clone',),
               (can_create_branch, 'Can Create Branch',),
               (can_delete_branch, 'Can Delete Branch',),
               (can_pull, 'Can pull'),
               (can_push, 'Can push'),
               )


class Commit(object):
    """
    An object that represents a commit.
    """
    def __init__(self, commit=None, author=None, date=None, message=None, merge=None):
        self.commit = commit.split()[1]
        authors = list(filter(None, author.split()))
        self.author = ' '.join(authors[1:-1])  # Solve multiple names
        self.email = authors[-1]
        self.date = get_date_from_git(' '.join(date.split()[2:]))
        self.message = message.strip()
        self.email = self.email.replace('<', '').replace('>', '')

        if merge:
            self.merge = ' '.join(merge.split()[1:])
        else:
            self.merge = merge

    def __str__(self):
        return self.title

    def __repr__(self):
        return '<<Commit:{0}>>'.format(self.title)

    class Meta:
        static = {'commit': {}, 'author': {},
                  'email': {}, 'date': {}, 'message': {}}

    @cached_property
    def title(self):
        title = self.message.split('\n')[0]
        return title.title()

    def get_author(self):
        return self.Meta.static.get('author')

    def get_commit(self):
        return self.Meta.static.get('commit')

    def get_date(self):
        return self.Meta.static.get('date')

    def get_email(self):
        return self.Meta.static.get('email')

    def get_message(self):
        return self.Meta.static.get('message')


class CommitFactory(object):
    """
    Consumes stdout and returns commit objects
    """
    def __init__(self, commits):
        self.__commit_parser = CommitParser(commits)

    def __str__(self):
        return None

    def __call__(self):
        return self.get_commits

    @cached_property
    def get_commits(self):
        """
        :return:
        """
        sorted_commit = sorted(self.__commit_parser(), key=lambda x: x.date, reverse=True)
        return sorted_commit

    def get_commits_page(self, page):
        """
        Always use this method for performance reasons
        """
        from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
        sorted_commit = sorted(self.__commit_parser(), key=lambda x: x.date, reverse=True)
        paginator = Paginator(sorted_commit, settings.NUMPERPAGE or 50)

        try:
            commits = paginator.page(page)
        except PageNotAnInteger:
            commits = paginator.page(1)  # If page is not an integer, deliver first page.
        except EmptyPage:
            commits = paginator.page(paginator.num_pages)
            # If page is out of range (e.g. 9999), deliver last page of results.
        return commits


class Key(PolymorphicModel, ShowFieldTypeAndContent):
    title = models.CharField(_('Name'), max_length=150, blank=False, null=False)
    key = models.TextField(blank=False, null=False)
    date_created = models.DateField(_('Date Added'),
                                    auto_now_add=True, editable=True)

    def __str__(self):
        return '{0}-{1}'.format(self.id, self.title)

    @cached_property
    def has_md_key(self):
        md5 = hashlib.md5(self.key).hexdigest()
        fingerprint = ':'.join(a+b for a, b in zip(md5[::2], md5[1::2]))
        return fingerprint

    @cached_property
    def delete_key_url(self):
        class_name = self.__class__.__name__

        if class_name == 'GnuPgKey':
            reverse_url = 'delete_gnupg_key'
        else:
            reverse_url = 'delete_ssh_key'

        url = reverse(reverse_url, args=(self.user, self.id))
        return url

    def delete_btn(self):
        btn = "<a href={href} class='btn btn-danger'>{delete}</a>"\
            .format(href=self.delete_key_url, delete=_('Delete'))
        return mark_safe(btn)


class SshKey(Key):
    user = models.ForeignKey(User, blank=False, null=False,
                             on_delete=models.CASCADE)

    class Meta:
        db_table = 'sshkey'
        verbose_name = _('Ssh key')
        verbose_name_plural = _('Ssh Keys')

    def __str__(self):
        return '{0}-{1}'.format(self.id, self.title)


class GnuPgKey(Key):
    user = models.ForeignKey(User, blank=False, null=False,
                             on_delete=models.CASCADE)

    class Meta:
        db_table = 'gnupgkeys'
        verbose_name = _('GnuPG key')
        verbose_name_plural = _('GnuPG keys')

    def __str__(self):
        return '{0}-{1}'.format(self.id, self.title)


class Email(models.Model):
    user = models.ForeignKey(User, related_name='my_email_object', blank=False,
                             null=False, on_delete=models.CASCADE)
    email = models.EmailField(verbose_name=_('email address'),
                              max_length=255, unique=True, blank=False, null=False)

    class Meta:
        db_table = 'email'
        verbose_name = _('Email')
        verbose_name_plural = _('Emails')

    def __str__(self):
        return '{0}-{1}'.format(self.user.username, self.email)


class Star(models.Model):
    project = models.ForeignKey("Project", blank=False, null=False, related_name='current_stars',
                                on_delete=models.CASCADE)
    user = models.ManyToManyField(User, related_name='project_stared')
    total = models.PositiveIntegerField(blank=False, null=False)

    class Meta:
        db_table = 'star'
        verbose_name = _('Star')
        verbose_name_plural = _('Stars')
        get_latest_by = 'id'

    def __str__(self):
        return str(self.total)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.total = 1
        super().save(*args, **kwargs)


class RepoFile(object):
    """
    A python object used to represent a file in a repo file specific work is don here
    """
    def __init__(self, **kwargs):
        self.cwd = kwargs.get('cwd')
        self.wrap_folder, self.file = kwargs.get('file_n_folder')
        self.project = kwargs.get('project')

    def file_last_modified(self):
        with cd(self.cwd):
            try:
                modified_time = os.path.getmtime(self.file)
                return naturaltime(timezone.datetime.fromtimestamp(modified_time))
            except OSError:
                return

    def last_commit(self):
        with cd(self.cwd):
            command = 'git log -n 1 -- {0}'.format(self.file).split(' ')
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            results = process.communicate()[0].decode("utf-8")
            results = list(filter(None, results.split('\n')))
            return results[-1].strip()[:60]

    def detect_file_type(self):
        return detect_file_type(self.file)


class Repo(models.Model):
    name = models.CharField(_('Name'), max_length=150, unique=True)
    owner = models.OneToOneField(User, blank=False, null=False, related_name="my_repo",
                                 on_delete=models.CASCADE)
    path = models.FilePathField(_('Path'), blank=True, null=True, editable=True)

    class Meta:
        db_table = 'repo'
        verbose_name = _('Repo')
        verbose_name_plural = _('Repos')

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name,

    @property
    def get_path(self):
        path = '{0}/{1}'.format(settings.REPO_PATH, self.owner.username)
        make_path(settings.REPO_PATH)
        make_path(path)
        return path.split(settings.REPO_PATH)[1]

    def save(self, *args, **kwargs):
        self.path = self.get_path
        super().save(*args, **kwargs)


class Wiki(models.Model):
    date_created = models.DateTimeField(_('Date Created'), auto_now_add=True, editable=True)
    date_updated = models.DateTimeField(_('Date Updated'), auto_now=True, editable=True)
    project = models.OneToOneField('Project', related_name='my_wiki', on_delete=models.CASCADE)
    text = models.TextField(blank=False, null=False)

    class Meta:
        db_table = 'wiki'
        verbose_name = _('Wiki')
        verbose_name_plural = _('Wikis')

    def __str__(self):
        return '{0}\'s wiki'.format(self.project.name)

    def natural_key(self):
        return self.project.name,

    def save(self, *args, **kwargs):
        now = timezone.now()

        if not self.pk:
            self.date_created = now
        self.date_updated = now
        super().save(*args, **kwargs)


class Project(models.Model):
    name = models.CharField(_('Name'), max_length=150)
    description = models.CharField(_('Description'), max_length=255, blank=False,
                                   null=False, default=_('A new git repo'))
    website = models.URLField(_("Website"), blank=True, null=True,
                              help_text=_("Website for this repository (optional)"))
    poster = models.ImageField(blank=True, null=True)
    date_created = models.DateTimeField(_('Date Created'), auto_now_add=True, editable=True)
    date_updated = models.DateTimeField(_('Date Updated'), auto_now=True, editable=True)
    path = models.FilePathField(_('Path'), blank=True, null=True, editable=True)
    repo = models.ForeignKey(Repo, blank=False, null=False, related_name="projects_in_repo",
                             on_delete=models.CASCADE)
    contributors = models.ManyToManyField(User, verbose_name=_('contributors'),
                                          related_name="the_project_contributors")
    is_private = models.BooleanField(default=True, blank=False, null=False,)
    downloads = models.PositiveIntegerField(default=0, blank=False, null=False)
    clones = models.PositiveIntegerField(default=0, blank=False, null=False)
    slug = AutoSlugField(populate_from='get_slug',
                         unique_with=['name', 'repo__owner__username', 'date_created'],
                         slugify=slugify, unique=True, editable=True)

    class Meta:
        db_table = 'project'
        verbose_name = _('Project')
        verbose_name_plural = _('Projects')
        unique_together = (('repo', 'name'),)

    def __str__(self):
        return self.name

    def cover(self):
        try:
            return self.poster.url
        except (AttributeError, ValueError):
            return "#"

    @cached_property
    def user(self):
        return self.repo.owner

    def get_slug(self):
        slug = '{0}-{1}-{2}'.format(self.name, self.repo.owner.username,
                                    str(timezone.now())
                                    )
        return slugify(slug)

    def stars(self):
        try:
            return self.current_stars.latest().user.all().count()
        except (Star.DoesNotExist, AttributeError):
            return 0

    def natural_key(self):
        return self.name,

    def display_in_profile(self):
        url = self.url.split('.git')[0]
        display = "<a href='{0}'>{1}</a>".format(url, self.name)
        return mark_safe(display)

    def display_on_wall(self):
        icon = "<i class='icon-globe icon-black'></i>"
        url = self.url.split('.git')[0]

        if self.is_private:
            icon = "<i class=\"icon-lock icon-black\"></i>"
        display = " {0} <a href='{1}'>{2} </a>".format(icon, url, self.name)
        return mark_safe(display)

    def has_wiki(self):
        try:
            _ = self.my_wiki
            return True
        except AttributeError:
            return False

    def log(self, n=None, **kwargs):
        if n is not None:
            result = 'git,log,-n {0}'.format(n)
        else:
            result = 'git,log'

        for key, value in kwargs.items():
            if key and value:
                result = '{0},{1},{2}'.format(result, key, value)
        command = result.split(',')

        with cd(self.working_dir):
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            results = process.communicate()
            return results[0]

    def last_commit_object_on_file(self, filename):
        """
        Returns last commit on a file
        :param filename:
        :return:
        """
        from gitapp.utils import solve_commit
        command = ['git', 'log', '-n 1', '--', filename]

        with cd(self.working_dir):
            try:
                process = Popen(command, stdout=PIPE, stderr=PIPE)
                results = process.communicate()
                results = results[0].decode("utf-8")
                results = [result for result in filter(None, results.split('\n'))]
                return solve_commit(results)
            except IndexError:
                pass

    def commits(self):
        return self.log()

    def get_branches(self):
        command = ['git', 'branch', '--all']

        with cd(self.working_dir):
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            results = process.communicate()
            results = results[0].decode("utf-8")

            try:
                results = list(filter(None, [result.strip() for result in results.split('\n')]))
                results = [name.split('/')[-1] for name in results]
                results = [name for name in results if not name.startswith('*')]
                results = list(set(results))
            except (AttributeError, IndexError):
                pass

            if not results:
                results = ['master']
        return results

    def get_current_branch_url(self):
        url = reverse('commits', args=(self.repo.name, self.name, self.current_branch()))
        return url

    def list_branches(self):
        branches = self.get_branches()
        for index, value in enumerate(branches):
            if value.startswith('*'):
                value = value.replace('* ', '')
                branches[index] = value
        return branches

    def current_branch(self):
        branch = [i.replace('* ', '') for i in self.get_branches() if i.startswith('*')]
        if type(branch) == list:
            if branch:
                return branch[0]
            branch = 'master'
        return branch

    @cached_property
    def owner(self):
        owner = self.repo.owner
        return owner

    @cached_property
    def url(self):
        if getattr(settings, 'DEBUG', True):
            url = '127.0.0.1:8000'
            protocol = 'http://'

        else:
            url = getattr(settings, 'PROJECT_URL', '127.0.0.1:8000')
            protocol = getattr(settings, 'PROTOCOL', 'http://')
        return '{0}{1}{2}'.format(protocol, url, self.__get_path)

    @cached_property
    def create_repo_name(self):
        repo_name = '{0}.git'.format('_'.join(self.name.split()))
        return repo_name

    @cached_property
    def name_dot_tar(self):
        repo_name = '{0}.tar.gz'.format('_'.join(self.name.split()))
        return repo_name

    @cached_property
    def name_dot_zip(self):
        repo_name = '{0}.zip'.format('_'.join(self.name.split()))
        return repo_name

    def full_path(self):
        path = '{0}/{1}/{2}'.format(settings.REPO_PATH,
                                    self.repo.owner.username,
                                    self.create_repo_name)
        return path

    def number_of_commits(self):
        """
        Counts number of commits
        :return:
        """
        command = ['git', 'rev-list', '--count', 'HEAD']
        with cd(self.working_dir):
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            result = process.communicate()[0]

            try:
                result = int(result)
            except ValueError:
                result = 0
            return result

    @cached_property
    def number_of_contributors(self):
        result = self.contributors.all().count()
        return result

    @cached_property
    def number_of_branches(self):
        result = len(self.get_branches())
        return result

    @cached_property
    def number_of_releases(self):
        result = self.contributors.all().count()
        return result

    def status(self):
        with cd(self.working_dir):
            command = ['git', 'log', '-1']
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            result = process.communicate()
            result = result[0].decode("utf-8")

            try:
                return result.splitlines()[-1].strip()
            except IndexError:
                return result

    @cached_property
    def get_transit_path(self):
        make_path(settings.TRANSIT_POINT)
        with cd(settings.TRANSIT_POINT):
            make_path(self.repo.owner.username)
            with cd(self.repo.owner.username):
                return os.getcwd()

    @cached_property
    def get_compression_path(self):
        make_path(settings.COMPRESSION_POINT)
        with cd(settings.COMPRESSION_POINT):
            make_path(self.repo.owner.username)
            with cd(self.repo.owner.username):
                return os.getcwd()

    @property
    def make_path_name(self):
        make_path(self.repo.owner.username)
        with cd(self.repo.owner.username):
            return os.getcwd()

    @cached_property
    def get_repo_media(self):
        make_path(settings.MEDIA_ROOT)
        with cd(settings.MEDIA_ROOT):
            return self.make_path_name

    def command(self, command_str):
        """
        Good for issuing arbitrary command from command line. Command should he entered as they will
        from the command line as a string.
        """
        command = command_str.split(' ')
        with cd(self.get_transit_path):
            result = Popen(command, stdout=PIPE, stderr=PIPE)
            result = result.communicate()[0]
            return result

    def update_repo_url(self, url):
        command = ['git', 'remote', 'set-url', 'origin', '&&', 'git',
                   'push', 'origin', 'HEAD:master', url]

        with cd(self.get_transit_path):
            result = Popen(command, stdout=PIPE, stderr=PIPE)
            result = result.communicate()
            del result

    def update_transit(self):
        transit_point = os.path.join(self.get_transit_path, str(self.name))

        if os.path.exists(transit_point):
            command = ['git', 'pull', '--all']

        else:
            command = ['git', 'clone', self.full_path()]

        with cd(self.get_transit_path):
            result = Popen(command, stdout=PIPE, stderr=PIPE)
            return result.communicate()[0]

    def compress_project(self, compression='tar.gz', return_path=False, return_compressed_dir=False):
        project_name = self.file_name.replace('.git', '')
        compressed_dir = '{0}.{1}'.format(project_name, compression)

        if return_compressed_dir:
            return '{0}.{1}'.format(project_name, compression)

        repo_2_compress = os.path.join(self.get_transit_path, project_name)

        if compression.startswith('tar'):
            command = ['tar', 'cvzf', compressed_dir, repo_2_compress]
        else:
            command = ['zip', '-r', compressed_dir, repo_2_compress]

        with cd(self.get_compression_path):
            result = Popen(command, stdout=PIPE, stderr=PIPE)
            result = result.communicate()[0]
            del result

            if return_path:
                return os.path.join(os.getcwd(), compressed_dir)

    @cached_property
    def file_name(self):
        return list(filter(None, self.path.split('/')))[1]

    @cached_property
    def __get_path(self):
        project_path = self.full_path()

        if not os.path.exists(project_path):
            make_path(project_path)

            command1 = ['git', 'init', '--bare']

            with cd(project_path):
                p = Popen(command1, stdout=PIPE, stderr=PIPE)
                _ = p.communicate()[0]

        return "/{0}".format('/'.join(project_path.split('/')[-2:]))

    def list_files(self):
        working_dir = self.working_dir

        with cd(working_dir):
            files = os.listdir('.')
            return files

    def source_path(self):
        working_dir = self.working_dir.replace(settings.TRANSIT_POINT, '')
        return os.path.join(working_dir, settings.SOURCE)

    @staticmethod
    def wrap_folder(file_or_folder, icon='black'):
        normalized_url = normalize_link(os.getcwd(), file_or_folder)
        full_path = '{0}'.format(normalized_url)

        if os.path.isdir(file_or_folder):
            return format_html(mark_safe('<i class="icon-folder-close icon-{0}"></i> <a href=\'{2}\'> {1} </a>'.
                                         format(icon, file_or_folder, full_path))), file_or_folder
        return format_html(mark_safe('<i class="icon-file icon-{0}"></i> <a href=\'{2}\'>{1} </a>'.
                                     format(icon, file_or_folder, full_path))), file_or_folder

    def file_last_modified(self, filename):
        with cd(self.working_dir):
            modified_time = os.path.getmtime(filename)
            return timezone.datetime.fromtimestamp(modified_time)

    def wrapped_list_folder(self):
        working_dir = self.working_dir
        root_folder = working_dir.split('/')[-1]
        root_dir = '/'.join(working_dir.split('/')[:-1])

        with cd(root_dir):
            current_files = [self.wrap_folder(root_folder)]

        with cd(working_dir):
            [current_files.append(self.wrap_folder(i)) for i in self.list_files() if i != '.git']
            return current_files

    def wrapped_given_folder_list(self, given_dir=None):
        working_dir = given_dir
        root_folder = working_dir.split('/')[-1]
        root_dir = '/'.join(working_dir.split('/')[:-1])

        with cd(root_dir):
            current_files = [self.wrap_folder(root_folder)]

        with cd(working_dir):
            [current_files.append(self.wrap_folder(i)) for i in os.listdir('.') if i != '.git']
            return current_files

    @cached_property
    def working_dir(self):
        """
        Returns the current working dir of project
        """
        filename = self.file_name.split('.git')[0]
        transit_path = self.get_transit_path
        full_path = os.path.join(transit_path, filename)
        return full_path

    @cached_property
    def base_dir(self):
        try:
            url_list = filter(None, self.working_dir.split(settings.TRANSIT_POINT))
            return [url for url in url_list][0]
        except IndexError:
            return '#'

    @staticmethod
    def detect_file_type(filename):
        """
        This detects the file type(programming language)
        :param filename:
        :return:
        """
        return detect_file_type(filename)

    def list_all_in_repo(self):
        with cd(self.working_dir):
            return return_files_in_dir('.', exclude_dir=('.git',), exclude_file=['.gitignore'])

    def __all_files(self):
        with cd(self.working_dir):
            return return_files_in_dir('.', exclude_dir=('.git',))

    def list_repo_files(self):
        files = [_file.split('transit/')[-1] for _file in self.__all_files()]
        return files

    def get_readme_file(self):
        from .utils import get_code_n_count, markdown_2_html

        with cd(self.working_dir):
            try:
                readme_file = [i for i in os.listdir(os.getcwd()) if i.lower().startswith('readme')][0]
                markdown_text = get_code_n_count(readme_file)[0]
                html = markdown_2_html(markdown_text)
            except IndexError:
                return False
        return html

    def file_percentage(self):
        def percentage(number_of_files, file_count):
            result = (float(number_of_files) / float(file_count)) * 100
            return float("{0:.0f}".format(result))

        file_type_n_count_dict = {}
        percentage_of_files = {}  # List all file type and percentages

        def set_file_type_n_count(percentage_dict, file_name):
            """
            Count the number of files and its types and return it as a dict.
            :param percentage_dict:
            :param file_name:
            :return:
            """
            file_type = self.detect_file_type(file_name)
            count_list = percentage_dict.get(file_type, [])
            count_list.append(file_name)
            percentage_dict[file_type] = count_list

        [set_file_type_n_count(file_type_n_count_dict, filename) for filename in self.list_all_in_repo()]

        all_files = []
        [all_files.extend(a_file) for a_file in file_type_n_count_dict.values()]
        total_files = len(all_files)

        for key, value in file_type_n_count_dict.items():
            percentage_of_files[filename_normalizer(key)] = percentage(len(value), total_files)

        percentage_of_files = OrderedDict(sorted(percentage_of_files.items(), key=lambda t: t[0]))
        return percentage_of_files

    def __create_repo_chart(self, show=False):
        from .statistics import create_chart, display_graph
        labels = []
        size = []

        for lang, percent in self.file_percentage().items():
            labels.append(lang)
            size.append(percent)

        chart = create_chart(labels=labels, sizes=size, colors=None, explode=None)
        path = self.get_repo_media

        with cd(path):
            image_path = '{0}.jpeg'.format(self.file_name.split('.')[0])
        return display_graph(show=show, path=image_path)

    def get_percentage_media_file(self, show=False):
        path = self.get_repo_media

        with cd(path):
            image_path = '{0}.jpeg'.format(self.file_name.split('.')[0])
            image_full_path = os.path.join(path, image_path)

            if not os.path.exists(image_full_path):
                self.__create_repo_chart(show=show)
        return '/media/{0}'.format('/'.join((image_full_path.split('/')[-2:])))

    def save(self, *args, **kwargs):
        if not self.pk:
            self.path = self.__get_path
        self.date_updated = timezone.now()
        super().save(*args, **kwargs)


class ProjectPermission(models.Model):
    """
    This permission system provides a way to assign permissions to specific
    users on a particular project.
    """
    permissions = models.CharField(_('Permissions'), max_length=40, choices=PERMISSIONS)
    project = models.ForeignKey("Project", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'project_permission'
        verbose_name = _('Project Permission')
        verbose_name_plural = _('Project Permissions')
        unique_together = (('permissions', 'project', 'user'),)

    def __str__(self):
        return '{0} | {1} | {2}'.format(six.text_type(self.user),
                                        six.text_type(self.permissions),
                                        six.text_type(self.project)
                                        )

    def save(self, *args, **kwargs):
        if self.user == self.project.repo.owner:
            raise ProjectUserPermissionError
        super().save(*args,  **kwargs)
