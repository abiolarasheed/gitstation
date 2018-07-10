# coding: utf-8

import base64
import codecs
from Crypto import Cipher, Random
import datetime
from hashlib import md5
import markdown
import os
from subprocess import Popen, PIPE
import time

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import Http404
from django.urls import reverse_lazy
from django.utils.html import format_html

from django_gravatar.helpers import get_gravatar_url

from .tasks import update_transit


progress_bar = ["progress progress-info",
                "progress progress-success",
                "progress progress-warning",
                "progress progress-danger",
                ]

filename_normalizer_dict = {'ASCII': 'Text',
                            'Bourne-Again': 'Shell',
                            'empty': 'Text'
                            }

EXTENSIONS = {'.md': 'html', '.py': 'python', '.js': 'javascript',
              '.css': 'css', '.php': 'php', '.txt': 'text', '.html': 'html',
              '.sh': 'shell', '.pl': 'perl', '.rb': 'ruby', '.java': 'java',
              '.sql': 'sql', '.erl': 'erlang', '.go': 'go', '.scala': 'scala',
              '.yaml': 'yaml', '.cpp': 'cpp'
              }

keydict = {'sshkey': lambda user, pk: user.sshkey_set.get(id=pk).delete(),
           'gnupgkey': lambda user, pk: user.gnupgkey_set.get(id=pk).delete()
           }

months_dict = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
               'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

imag_dict = {'large': settings.PROFILE_THUMB_LARGE,
             'small': settings.PROFILE_THUMB_SMALL,
             'mini': settings.PROFILE_THUMB_MINI}


def detect_file_type(filename):
    """
    This detects the file type(programming language)
    :param filename:
    :return:
    """
    command = 'file {}'.format(filename)
    process = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    result = process.communicate()[0]

    try:
        result = result.decode("utf-8")
    except AttributeError:
        pass

    result = result.split(',')[0].split(': ')[-1].replace('script', '').split(' ')[0].strip()
    return result


def get_date_from_git(astring):
    str_2_list = astring.split()
    if len(str_2_list) == 5:
        month, day, time_, year, _ = str_2_list
    else:
        month, day, time_, year = str_2_list[1:]

    month = months_dict[month]
    minute, second, microsecond = [int(i) for i in time_.split(':')]
    year, day, month = [int(one) for one in [year, day, month]]
    return datetime.datetime(year, month, day, minute, second, microsecond)


def get_relative_and_full_path(file_path, path=settings.SOURCE):
    """

    :param file_path:
    :param path:
    :return:
    """
    relative_path = file_path.replace(path + '/', '')
    relative_path = '/'.join([path for path in filter(None, relative_path.split('/'))])
    full_path = os.path.join(settings.TRANSIT_POINT, relative_path)
    return relative_path, full_path


def get_from_gravatar(email, size):
    gravatar_url = get_gravatar_url(email, size=imag_dict.get(size, 'large')[0])
    return gravatar_url


def get_thumb_url(user, size, cache_name='thumb'):
    key = cache.get('user_{0}'.format(str(user.id)))
    url = None

    if key:
        url = key.get(cache_name)
        if url is not None:
            return url

    thumb_url = os.path.join(settings.STATIC_URL, settings.PROFILE_DEFAULT_THUMB)
    make_path(settings.MEDIA_ROOT)
    user_repos = os.path.join(settings.MEDIA_ROOT, user.username)
    make_path(user_repos)

    with cd(user_repos):
        make_path(size)
        with cd(size):
            try:
                url = list(filter(None, os.listdir('.')))[0]
            except IndexError:
                pass

    if url is None:
        url = get_from_gravatar(user.email, size)

    if url:
        url = "{0}?s={1}&amp;d=mm&amp;r=g".format(url.split('?')[0], str(size))
        dct = {cache_name: url}
        cache.set(key, dct, 60 * 15)
        print(url)
        return url

    else:
        return thumb_url


def commit_2_list(commits):
    """
    Takes commit from stdout and returns list of commit messages
    :param commits:
    :return:
    """
    commits = list(filter(None, commits.split('\n\n')))
    all_commits = []

    for index, value in enumerate(commits):
        if not index % 2:
            top = value.split('\n')
        else:
            bottom = list(filter(None, value.split('\n')))
            top.append(bottom[-1].strip())
            all_commits.append(top)
    return all_commits


class CommitParser(object):
    def __init__(self, commits):
        self.commit_str_list = self.parser_20_list(commits)
        self.commit_objects = self.create_commit_object()

    @staticmethod
    def parser_20_list(commits):
        """
        Takes commit from stdout and returns list of commit messages
        :param commits:
        :return:
        """
        commits = list(filter(None, commits.decode("utf-8").split('\n\n')))
        all_commits = []
        commit_pack = []

        for index, value in enumerate(commits):
            if value.startswith('commit'):
                commit_pack = [value]
            else:
                commit_pack.append(value)

            if index > 0 and value.startswith('commit'):
                all_commits.append(commit_pack)
        return all_commits

    def create_commit_object(self):
        commit_objects_list = []
        for commit in self.commit_str_list:
            clean_commit = list(filter(None, commit))[0]
            commit_objects_list.append(clean_commit)
        commit_object_list = [solve_commit(a_list) for a_list in commit_objects_list]
        return commit_object_list

    def __call__(self):
        return self.commit_objects


def solve_commit(alist):
    """
    Takes desission and creates a commit instance
    :param alist:
    :return:
    """
    from .models import Commit
    commit_dict = {}

    if type(alist) == str:
        alist = [alist]

    if len(alist) == 2:
        pt1 = alist[0].split('\n')
        pt1.append(alist[1])
        alist = pt1

    if len(alist) > 4:
        if alist[1].startswith('Merge:'):
                commit, merge, author, date = alist[:4]
                message = '\n'.join(alist[4:])
                commit_dict.update({'merge': merge})
        else:
            commit, author, date = alist[:3]
            message = '\n'.join(alist[3:])
    elif len(alist) == 1:
        try:
            commit, author, date, = alist[0].splitlines()
        except IndexError:
            commit, merge, author, date, = alist[0].splitlines()
            commit_dict.update({'merge': merge})
        message = ''

    else:
        commit, author, date, message = alist

    commit_dict.update({'commit': commit, 'author': author,
                        'date': date, 'message': message.strip()
                        })
    commit = Commit(**commit_dict)
    return commit


def normalize_link(root_dir, given_file_or_dir, source_link=settings.SOURCE):
    full_path = os.path.join(root_dir, given_file_or_dir)
    files_or_paths = []

    for file_or_path in full_path.replace(settings.TRANSIT_POINT, '').split('/'):
        try:
            file_or_path = file_or_path.decode("utf-8")
            files_or_paths.append(file_or_path)
        except AttributeError:
            files_or_paths.append(file_or_path)

    url = '/{0}/{1}/{2}'.format('/'.join(files_or_paths[:2]),
                                source_link,
                                '/'.join(files_or_paths[2:]))
    url = url.rstrip('/')

    if url.endswith('/{0}'.format(source_link)):
        url = url.rstrip('/{0}/'.format(source_link))
    return url


def markdown_2_html(markdown_text):
    html = format_html(markdown.markdown(markdown_text))
    return html


def file_len(fname):
    """
    http://stackoverflow.com/questions/845058/how-to-get-line-count-cheaply-in-python
    count the number of lines in a file
    """

    # To avoid UnboundLocalError for local variable 'i' referenced before assignment and set -1 because of empty files
    with open(fname) as f:
        i = - 1
        for i, _ in enumerate(f):
            pass
    return i + 1


def get_code_n_count(afile):
    """
    This returns the file content and the number of lines in it and its size in bytes
    :param afile:
    :return:
    """
    try:
        with codecs.open(afile, mode="r", encoding="utf-8") as input_file:
            text = input_file.read()
            num_lines = file_len(afile)
            size = os.path.getsize(afile)
            return text, num_lines, size
    except UnicodeDecodeError:
        return reverse_lazy('encoding_error')


def get_language_via_ext(ext):
    return EXTENSIONS.get(ext, None)


def delete_key(user, pk, key_type):
    try:
        keydict.get(key_type)(user, pk)
    except KeyError:
        raise Http404


def filename_normalizer(filename):
    """
    This will give the right name to given file type
    :param filename:
    :return:
    """
    result = filename_normalizer_dict.get(filename, filename)
    return result


def return_files_in_dir(a_dir, ext=None, exclude_file=None, exclude_dir=None):
    """ This returns all file in a dir,you can exclude any list of
    files or dirs or any type of extension or group of extensions.
        USEAGE ::


    >>> exclude_files = ['.gitignore']
    >>> return_files_in_dir('.', exclude_dir=('.git',),)
    >>> return_files_in_dir('.', exclude_dir=('.git',), exclude_file=exclude_files)
    >>> return_files_in_dir('.', ext='.py', exclude_dir=('.git',), exclude_file=exclude_files)
    >>> return_files_in_dir('.', ext=['.py'], exclude_dir=('.git',), exclude_file=exclude_files)
    """
    if exclude_file is None:
        exclude_file = []

    def check_exclude_dir(the_root, name, the_exclude_dir):
        """" Returns true if file is in the excluded dir list """
        full_path = os.path.join(the_root, name)
        split_path = set(full_path.split('/'))
        dir_2_exclude = split_path.intersection(the_exclude_dir)
        return True if dir_2_exclude else False

    def check_extension(file_name, extension):
        """
        Returns true if file has given extension
        :param file_name:
        :param extension extension:
        :return:
        """
        if isinstance(extension, list):
            file_ext = os.path.splitext(file_name)
            new_ext = []

            for i in extension:
                if not i.startswith('.'):
                    new_ext.append('.{0}'.format(i))
                else:
                    new_ext.append(i)
            extensions = new_ext
            return True if file_ext in extensions else False
        return True if file_name.endswith(extension) else False

    a_dir = os.path.abspath(a_dir)
    if not os.path.exists(a_dir):
        raise OSError

    all_files = []
    exclude_dir = set(exclude_dir)
    for root, _, files in os.walk(a_dir, topdown=False):
        [all_files.append(os.path.join(root, name)) for name in files if name not in exclude_file
         and not check_exclude_dir(root, name, exclude_dir)
         ]

    if ext is not None:
        all_files = [a_file for a_file in all_files if not check_extension(a_file, ext)]
    return all_files


def make_path(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def get_project_repo(repo_name, project_name, slug=None):
    from .models import Project
    data = {}

    if slug is not None:
        data['slug'] = slug
    else:
        data = dict(repo__name=repo_name, name=project_name)

    try:
        project_repo = Project.objects.get(**data)
        return project_repo
    except Project.DoesNotExist:
        return None


def view_if_public(func):
    """ Decorator that ensure the repo is accessed only if its public. """

    def _dec(request, *args, **kwargs):

        project_name = kwargs.get('project_name')
        repo_name = kwargs.get('repo_name').split('/')[-1]

        if project_name is None:
            slug = kwargs.get('slug')
            project = get_project_repo(request.user.username, project_name, slug=slug)

        elif project_name.endswith('.git'):
            project_name = project_name.split('.git')[0]

            project = get_project_repo(request.user.username, project_name)

        else:
            ext = project_name.split('.')
            if ext[-1] in ['zip', 'gz']:

                if ext == '.zip':
                    project_name = project_name.split('.zip')[0]

                else:
                    project_name = project_name.split('.tar.gz')[0]

            kwargs['repo_name'] = repo_name
            project = get_project_repo(request.user.username, project_name)
            if project is None:
                raise PermissionDenied

        exists = os.path.exists(project.working_dir)

        if not exists:
            update_transit.delay(project.id)
            while not exists:
                time.sleep(1)
                exists = os.path.exists(project.working_dir)

        is_owner = project.repo.owner == request.user

        if project.is_private and not is_owner:
            raise PermissionDenied

        setattr(request, "project", project)

        response = func(request, *args, **kwargs)
        return response
    return _dec


class cd(object):
    def __init__(self, new_path):
        self.new_path = new_path

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def encrypt_val(clear_text):
    """
    Encrypt Text
    :param clear_text:
    :return:
    """
    enc_secret = Cipher.AES.new(settings.SECRET_KEY[:32])
    tag_string = (str(clear_text) +
                  (Cipher.AES.block_size -
                   len(str(clear_text)) % Cipher.AES.block_size) * "\0")
    cipher_text = base64.b64encode(enc_secret.encrypt(tag_string))
    return cipher_text


def decrypt_val(cipher_text):
    """
    Decrypt text
    :param cipher_text:
    :return:
    """
    dec_secret = Cipher.AES.new(settings.SECRET_KEY[:32])
    raw_decrypted = dec_secret.decrypt(base64.b64decode(cipher_text))
    clear_val = raw_decrypted.rstrip("\0")
    return clear_val


def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).hexdigest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]


def encrypt_file(in_file, out_file, password, key_length=32):
    bs = Cipher.AES.block_size
    salt = Random.new().read(bs - len('Salted__'))
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = Cipher.AES.new(key, Cipher.AES.MODE_CBC, iv)
    out_file.write('Salted__' + salt)
    finished = False

    while not finished:
        chunk = in_file.read(1024 * bs)
        if len(chunk) == 0 or len(chunk) % bs != 0:
            padding_length = bs - (len(chunk) % bs)
            chunk += padding_length * chr(padding_length)
            finished = True
        out_file.write(cipher.encrypt(chunk))


def decrypt_file(in_file, out_file, password, key_length=32):
    bs = Cipher.AES.block_size
    salt = in_file.read(bs)[len('Salted__'):]
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = Cipher.AES.new(key, Cipher.AES.MODE_CBC, iv)
    next_chunk = ''
    finished = False

    while not finished:
        chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
        if len(next_chunk) == 0:
            padding_length = ord(chunk[-1])
            if padding_length < 1 or padding_length > bs:
                raise ValueError("bad decrypt pad (%d)" % padding_length)
                # all the pad-bytes must be the same
            if chunk[-padding_length:] != (padding_length * chr(padding_length)):
                # this is similar to the bad decrypt:evp_enc.c from openssl program
                raise ValueError("bad decrypt")
            chunk = chunk[:-padding_length]
            finished = True
        out_file.write(chunk)
