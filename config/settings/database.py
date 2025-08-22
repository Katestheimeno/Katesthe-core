from config.settings import SQLITE_DATABASE_PATH
imports = []

imports += ["DATABASES"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':  SQLITE_DATABASE_PATH / 'db.sqlite3',
    }
}

imports += ["DEFAULT_AUTO_FIELD"]
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


__all__ = imports
