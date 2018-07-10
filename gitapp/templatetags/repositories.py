# coding: utf-8

import os
import time
from django import template
register = template.Library()


@register.filter("name")
def name(value):
    return value.split(os.sep)[-2]


@register.filter("join")
def os_join(project, a_file):
    return os.path.join(project.working_dir(), a_file)


@register.filter("last_modified")
def last_modified(filename):
    """
    Returns file last modified  time
    :param filename:
    :return:
    """
    modified_at = time.ctime(os.path.getmtime(filename))
    return modified_at


@register.filter("remove_dot_git")
def remove_dot_git(url_with_dot_git):
    """
    Removes trailing .git in repo name or url
    :param url_with_dot_git:
    :return:
    """
    url = url_with_dot_git.split('.git')[0]
    return url
