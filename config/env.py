"""
env.py
-------------------------------------------------------------------------------
This file handles environment variable configuration for the Django project.

- Sets the project's base directory
- Loads variables from a `.env` file using `django-environ`
- Exports `env` and `BASE_DIR` for use in other settings files

Usage:
    from config.env import env, BASE_DIR
-------------------------------------------------------------------------------

"""
from pathlib import Path
import environ

# Exportable symbols list for `from env import *` usage
imports = []

# Initialize the environment reader
imports += ["env"]
env = environ.Env()

# Define the base directory of the project (2 levels up from this file)
imports += ["BASE_DIR"]
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file located at the project root
env_file = BASE_DIR / ".env"
env.read_env(env_file)


imports += ["DEBUG"]
DEBUG = env.bool('DJANGO_DEBUG', default=True)

imports += ["SECRET_KEY"]
SECRET_KEY = env("SECRET_KEY")

imports += ["ALLOWED_HOSTS"]
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=['*'])


__all__ = imports
