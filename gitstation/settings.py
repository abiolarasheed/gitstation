# coding: utf-8
from __future__ import unicode_literals

import os
from os import environ
from django.urls import reverse_lazy

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

DEFAULT_CHARSET = 'utf-8'
APPEND_SLASH = True
ROOT_URLCONF = 'gitstation.urls'
WSGI_APPLICATION = 'gitstation.wsgi.application'

# SECURITY
SECRET_KEY = environ.get('SECRET_KEY')

DEBUG = True
TEMPLATE_DEBUG = DEBUG
if DEBUG:
    ALLOWED_HOSTS = ['*']

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Application definition
NUMPERPAGE = 50
DEFAULT_THUMB = (24, 24)
PROFILE_THUMB_SMALL = (80, 80)
PROFILE_THUMB_MINI = (16, 16)
PROFILE_THUMB_LARGE = (400, 400)
PROFILE_DEFAULT_THUMB = "img/git.png"

# Exclude this directory when auto making repo from existing repo
EXCLUDE_DIRS = ['git-shell-commands', '.ssh', '.cache']


INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'polymorphic',
    'gitapp',
    'crispy_forms',
    'django_tables2',
    'django_filters',
    'django_pygments',
    'django_gravatar',
    'django_extensions',
)


MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

FILE_UPLOAD_HANDLERS = (
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
)


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'gitapp.middleware.TransitMiddleware',
]


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'gitstation',
        'USER': environ.get('GITSTATION_USER'),
        'PASSWORD': environ.get('DATABASES_HOST_PASSWORD'),
        'HOST': os.environ.get('ITSTATION_DB'),
        'PORT': '',
        'CONN_MAX_AGE': None,
        'CHARSET': 'UTF8',
        'OPTIONS': {'sslmode': 'require'}
        }
}

CACHE_MIDDLEWARE_KEY_PREFIX = 'gitstation'
DJANGO_REDIS_IGNORE_EXCEPTIONS = True

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_REDIS_HOST = environ.get('SESSION_REDIS_HOST', "localhost")
SESSION_REDIS_PORT = environ.get('SESSION_REDIS_PORT', 6379)
SESSION_REDIS_DB = environ.get('SESSION_REDIS_DB', 0)
SESSION_REDIS_PREFIX = '{0}-session'.format(CACHE_MIDDLEWARE_KEY_PREFIX)
SESSION_REDIS_PASSWORD = environ.get('SESSION_REDIS_PASSWORD', None)

CACHE_MIDDLEWARE_SECONDS = 60 * 60
CACHE_HERD_TIMEOUT = CACHE_MIDDLEWARE_SECONDS

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{0}:{1}/1".format(SESSION_REDIS_HOST, SESSION_REDIS_PORT),
        'TIMEOUT': CACHE_MIDDLEWARE_SECONDS,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.HerdClient",
            "PICKLE_VERSION": -1,
            "COMPRESS_MIN_LEN": 10,
            "IGNORE_EXCEPTIONS": True,
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "MAX_ENTRIES": 1000,
            "CULL_FREQUENCY": 0,
            "KEY_PREFIX": CACHE_MIDDLEWARE_KEY_PREFIX,
            "KEY_FUNCTION": 'cache.utils.set_cache_key',
            "VERSION": 1,
        }
    },
}


TEMPLATES_PATH = os.path.join(BASE_DIR,  "gitstation/templates")
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'gitstation/assets'),)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATES_PATH],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "gitapp.context_processors.add_thumb_url",
            ],
            'loaders': [('django.template.loaders.cached.Loader',
                         ('django.template.loaders.filesystem.Loader',
                          'django.template.loaders.app_directories.Loader',)),
                         ]
        },
    },
]


# Repository Paths / Locations
ROOT_DIR = os.path.join(BASE_DIR, 'gitstation')
REPO_PATH = os.path.join(ROOT_DIR, 'repo')  # Location of the git server repository
TRANSIT_POINT = os.path.join(ROOT_DIR, 'transit')  # We clone repo to this dir and use it for serving or querying
COMPRESSION_POINT = os.path.join(ROOT_DIR, 'compress')  # Location we use to server repo in compressed format

# URL PATH
SOURCE = 'src-tree'
HISTORY = 'file-history'
EDIT_PATH = 'edit-file'
TEXT_PATH = 'render-as-text'

# Static & Media Paths
MEDIA_ROOT = os.path.join(BASE_DIR, 'gitstation/media')
STATIC_ROOT = os.path.join(BASE_DIR, 'gitstation/static')

# Project URLs
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

PROJECT_URL = environ.get("PROJECT_URL", 'gitstation.com')
PROTOCOL = environ.get('PROTOCOL', 'http://')
if not DEBUG:
    ALLOWED_HOSTS = [PROJECT_URL]

LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('profile')
LOGOUT_URL = reverse_lazy('logout')

# 3rd party settings
#DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap4.html"
CRISPY_TEMPLATE_PACK = 'bootstrap4'

REDIS_URL = environ.get('REDIS_URL')

# CELERY SETTINGS
BROKER_URL = environ.get("BROKER_URL", "{0}".format(REDIS_URL))
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ALWAYS_EAGER = True
CELERYBEAT_SCHEDULE = {}
