"""
Geolocation suffix
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import math

imports = []

imports += ["GeolocationModel"]

class GeolocationModel(models.Model):
    """
    Abstract model for geolocation data with utility methods.
    Stores latitude, longitude, altitude, accuracy, and optional address components.
    """

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude in decimal degrees (-90 to 90)"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude in decimal degrees (-180 to 180)"
    )
    altitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Altitude in meters"
    )
    accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="GPS accuracy in meters"
    )

    # Optional address components
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    class Meta:
        abstract = True

    @property
    def coordinates(self):
        """Return coordinates as a (latitude, longitude) tuple or None if missing."""
        if self.latitude is not None and self.longitude is not None:
            return float(self.latitude), float(self.longitude)
        return None

    def distance_to(self, other):
        """
        Calculate distance to another GeolocationModel instance using Haversine formula.
        Returns distance in kilometers.
        """
        if not self.coordinates or not getattr(other, 'coordinates', None):
            return None

        lat1, lon1 = self.coordinates
        lat2, lon2 = other.coordinates

        R = 6371  # Earth's radius in kilometers

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def has_valid_coordinates(self):
        """Return True if both latitude and longitude are set and within valid ranges."""
        return (
            self.latitude is not None and -90 <= self.latitude <= 90 and
            self.longitude is not None and -180 <= self.longitude <= 180
        )

    def as_dict(self):
        """Return geolocation and address data as a dictionary."""
        return {
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "altitude": self.altitude,
            "accuracy": self.accuracy,
            "address": self.address,
            "city": self.city,
            "country": self.country,
            "postal_code": self.postal_code,
        }


__all__ = imports