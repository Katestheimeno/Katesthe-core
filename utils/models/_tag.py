"""
Tag suffix
"""

from django.db import models
from django.core.exceptions import ValidationError

imports = []

imports += ["TaggableModel"]


class TaggableModel(models.Model):
    """
    Abstract model that adds tagging functionality.
    
    Tags are stored in a JSONField as lowercase, unique strings.
    Leading '#' characters are removed automatically.
    The `tag_count` field is automatically updated.
    """
    tags = models.JSONField(default=list, blank=True)
    tag_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        abstract = True

    def _clean_tag(self, tag):
        """Strip whitespace, lowercase, remove leading '#'"""
        if not isinstance(tag, str):
            raise ValidationError(f"Invalid tag type: {tag} (must be string)")
        return tag.strip().lower().lstrip("#")

    def clean_tags(self):
        """Ensure all tags are cleaned and unique"""
        if self.tags:
            cleaned = []
            for tag in self.tags:
                t = self._clean_tag(tag)
                if t and t not in cleaned:
                    cleaned.append(t)
            self.tags = cleaned
            self.tag_count = len(cleaned)

    def save(self, *args, **kwargs):
        """Clean tags and update tag_count before saving"""
        self.clean_tags()
        super().save(*args, **kwargs)

    def add_tag(self, tag):
        """Add a single tag, removing duplicates and leading '#'"""
        t = self._clean_tag(tag)
        if t and t not in self.tags:
            self.tags.append(t)
            self.tag_count = len(self.tags)
            self.save(update_fields=['tags', 'tag_count'])

    def remove_tag(self, tag):
        """Remove a tag if it exists"""
        t = self._clean_tag(tag)
        if t in self.tags:
            self.tags.remove(t)
            self.tag_count = len(self.tags)
            self.save(update_fields=['tags', 'tag_count'])

    def has_tag(self, tag):
        """Check if object has a specific tag"""
        return self._clean_tag(tag) in self.tags

    def get_tag_string(self):
        """Get tags as a comma-separated string"""
        return ", ".join(self.tags)

    def set_tags(self, tag_list):
        """
        Replace current tags with a new list.
        Automatically cleans duplicates, whitespace, and leading '#'.
        """
        if not isinstance(tag_list, list):
            raise ValueError("tag_list must be a list of strings")
        self.tags = [self._clean_tag(t) for t in tag_list if t.strip()]
        self.tag_count = len(self.tags)
        self.save(update_fields=['tags', 'tag_count'])

    def add_tags_bulk(self, tag_list):
        """
        Add multiple tags at once.
        Ignores duplicates and cleans whitespace/leading '#'.
        """
        new_tags = [self._clean_tag(t) for t in tag_list if t.strip()]
        added = False
        for t in new_tags:
            if t not in self.tags:
                self.tags.append(t)
                added = True
        if added:
            self.tag_count = len(self.tags)
            self.save(update_fields=['tags', 'tag_count'])

    def clear_tags(self):
        """Remove all tags"""
        self.tags = []
        self.tag_count = 0
        self.save(update_fields=['tags', 'tag_count'])

__all__ = imports