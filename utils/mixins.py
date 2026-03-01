"""
Reusable model mixins.

"""

from django.db import models


class TimestampMixin(models.Model):
    """
    Adds created_at and updated_at to any model.

    Usage:
        class MyModel(TimestampMixin, models.Model):
            ...
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]