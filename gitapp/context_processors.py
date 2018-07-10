# coding: utf-8

from django.conf import settings
from .utils import get_thumb_url


def add_thumb_url(request):
    url = ''
    if hasattr(request, 'user'):
        if request.user.is_authenticated:
            url = get_thumb_url(request.user, size=str(settings.DEFAULT_THUMB[0]))
    return {'THUMB_URL': url}
