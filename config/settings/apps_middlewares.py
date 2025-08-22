# this file includes all the middlewares
# and the installed apps

# Application definition
imports = []

UNFOLD_APP = [
    "unfold",  # before django.contrib.admin
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is used
    "unfold.contrib.location_field",  # optional, if django-location-field package is used
    "unfold.contrib.constance",  # optional, if django-constance package is used
]

# django's default apps
DJANGO_APPS = [
    *UNFOLD_APP,
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]


# appas and packages installed
THIRD_PARTY_PACKAGES = [
    "rest_framework",       # DRF
    "django_extensions",    # dev tools like shell_plus, graph_models
]

# main project apps
PROJECT_APPS = [
    'utils',
]

imports += ["INSTALLED_APPS"]

INSTALLED_APPS = [
    *DJANGO_APPS,
    *THIRD_PARTY_PACKAGES,
    *PROJECT_APPS,
]

imports += ["DEV_APPS"]

# apps that should only be accessable in the dev environment
DEV_APPS = [
    'rosetta',
    'silk',
]

imports += ["MIDDLEWARE"]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


__all__ = imports
