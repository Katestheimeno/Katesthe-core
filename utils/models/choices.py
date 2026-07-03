"""
Reusable choices base: boolean-valued choices.
Path: utils/models/choices.py
"""

from django.db import models


class BooleanChoices(models.Choices):
    """Base class for boolean-valued choices (True/False members).

    Subclass and define members with boolean values, e.g.::

        class YesNoChoices(BooleanChoices):
            YES = True, "Yes"
            NO = False, "No"

    Unlike ``IntegerChoices``/``TextChoices`` (whose ``int``/``str`` mixin unwraps
    the member value), a plain ``Choices`` enum has no data-type mixin, so Django
    would otherwise store the value as a 1-tuple. The custom ``__new__`` unwraps it
    so ``.value`` is the real ``bool`` and ``.choices`` is usable on a model field.
    """

    def __new__(cls, value):
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


__all__ = ["BooleanChoices"]
