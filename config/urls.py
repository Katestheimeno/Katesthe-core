"""
URL configuration for config project.
"""

from django.conf import settings as cfg
from django.contrib import admin
from django.urls import path, include, re_path

urlpatterns = [
    path('admin/', admin.site.urls),
]

if cfg.DEBUG:
    urlpatterns += [
        path('silk/', include('silk.urls', namespace='silk')),
        re_path(r'^rosetta/', include('rosetta.urls'))
    ]
