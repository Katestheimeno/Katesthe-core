"""
this file serve as a self contained time and language setting
"""

imports = []


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

imports += ["LANGUAGE_CODE"]
LANGUAGE_CODE = 'en-us'

imports += ["TIME_ZONE"]
TIME_ZONE = 'UTC'

imports += ["USE_I18N"]
USE_I18N = True

imports += ["USE_TZ"]
USE_TZ = True


__all__ = imports
