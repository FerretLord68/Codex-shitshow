from abc import ABC, abstractmethod
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .salling import SallingClient


class OfferProviderAdapter(ABC):
    @abstractmethod
    def fetch(self):
        """Return validated offer dictionaries without persistence."""


class MockProvider(OfferProviderAdapter):
    def fetch(self):
        now = timezone.now()
        return [
            {
                "source_identifier": "mock-tomato-1",
                "product_name": "Danske tomater",
                "brand": "Testgården",
                "category": "Grøntsager",
                "offer_price": Decimal("15.00"),
                "regular_price": Decimal("22.00"),
                "currency": "DKK",
                "starts_at": now,
                "ends_at": now + timedelta(days=7),
                "original_source_text": "Development-only mock offer: Danske tomater 500 g, 15 kr.",
            }
        ]


class ManualProvider(OfferProviderAdapter):
    REQUIRED = {"source_identifier", "product_name", "offer_price", "starts_at", "ends_at", "store"}

    def __init__(self, records):
        self.records = records

    def fetch(self):
        for record in self.records:
            missing = self.REQUIRED - set(record)
            if missing:
                raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
            yield record


class SallingGroupProvider(OfferProviderAdapter):
    def __init__(self, provider):
        self.provider = provider

    def fetch(self):
        configuration = self.provider.configuration
        result = SallingClient(base_url=self.provider.base_url or None).food_waste(
            zip_code=configuration.get("zip"),
            geo=configuration.get("geo"),
            radius=configuration.get("radius"),
            store_id=configuration.get("store_id"),
        )
        return result.items


PROVIDER_TYPES = {"mock": MockProvider, "salling_group": SallingGroupProvider}
