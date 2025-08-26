from config.env import *
from config.settings import *
from config.logger import setup_django_logging

setup_django_logging()


ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Schedule Tasks
CELERY_BEAT_SCHEDULE = {
    # 'say-hello-every-minute': {
    #     'task': 'appointments.tasks.my_task',
    #     'schedule': 60.0,
    #     'args': ("DevMozach",)
    # },
}
