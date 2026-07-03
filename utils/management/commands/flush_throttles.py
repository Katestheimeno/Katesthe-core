"""
Management command: clear DRF throttle counters from the cache.
Path: utils/management/commands/flush_throttles.py
"""

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear DRF throttle counters from the cache (Redis-aware, falls back to full cache clear)"

    def handle(self, *args, **options):
        if self._flush_redis_throttle_keys():
            return

        # Fallback — non-Redis backend (e.g. LocMemCache) or pattern delete unavailable
        cache.clear()
        self.stdout.write(self.style.WARNING(
            "Cleared entire cache (fallback — backend does not support pattern delete)"
        ))

    def _flush_redis_throttle_keys(self):
        """Attempt a targeted delete of `*throttle_*` keys via django-redis.

        Returns True if the Redis path succeeded (and output was written),
        False if it should fall back to a full cache clear.
        """
        try:
            client = cache.client.get_client()
            keys = list(client.keys("*throttle_*"))
            if keys:
                client.delete(*keys)
            self.stdout.write(self.style.SUCCESS(
                f"Cleared {len(keys)} throttle keys"
            ))
            return True
        except (AttributeError, NotImplementedError, ImportError) as exc:
            self.stdout.write(
                f"Redis pattern delete unavailable ({exc.__class__.__name__}); falling back"
            )
            return False
