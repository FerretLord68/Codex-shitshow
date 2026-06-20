import re
import unicodedata
from decimal import Decimal
from difflib import SequenceMatcher

from django.db import transaction
from django.utils import timezone

from catalog.models import Ingredient, Product, Store

from .models import GroceryOffer, OfferProvider, OfferSyncRun, PriceRecord, ProductIngredientMatch
from .providers import PROVIDER_TYPES


def normalize_name(value):
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def match_product_to_ingredients(product):
    target = normalize_name(f"{product.brand} {product.name}")
    candidates = []
    for ingredient in Ingredient.objects.filter(active=True).prefetch_related("aliases"):
        names = [ingredient.name_da, ingredient.name_en, *ingredient.aliases.values_list("alias", flat=True)]
        confidence = max(SequenceMatcher(None, target, normalize_name(name)).ratio() for name in names)
        if confidence >= 0.55:
            match, _ = ProductIngredientMatch.objects.update_or_create(
                product=product,
                ingredient=ingredient,
                defaults={"confidence": Decimal(str(round(confidence, 3))), "approved": confidence >= 0.88},
            )
            candidates.append(match)
    return candidates


@transaction.atomic
def import_manual_records(provider, records):
    if provider.kind != OfferProvider.Kind.MANUAL:
        raise ValueError("Provider is not configured for manual imports.")
    imported = 0
    for record in records:
        required = {"source_identifier", "product_name", "offer_price", "starts_at", "ends_at", "store"}
        missing = required - set(record)
        if missing:
            raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
        store, _ = Store.objects.get_or_create(name=str(record["store"])[:150])
        product, _ = Product.objects.get_or_create(
            name=str(record["product_name"])[:200],
            brand=str(record.get("brand", ""))[:150],
            defaults={"category": str(record.get("category", ""))[:100]},
        )
        offer, _ = GroceryOffer.objects.update_or_create(
            provider=provider,
            source_identifier=str(record["source_identifier"])[:200],
            starts_at=record["starts_at"],
            defaults={
                "store": store,
                "product": product,
                "product_name": product.name,
                "brand": product.brand,
                "description": str(record.get("description", ""))[:5000],
                "category": str(record.get("category", ""))[:100],
                "offer_price": record["offer_price"],
                "regular_price": record.get("regular_price"),
                "unit_price": record.get("unit_price"),
                "currency": str(record.get("currency", store.currency))[:3],
                "ends_at": record["ends_at"],
                "source_url": str(record.get("source_url", ""))[:500],
                "original_source_text": str(record.get("original_source_text", record["product_name"]))[:5000],
                "retrieved_at": timezone.now(),
            },
        )
        PriceRecord.objects.create(
            product=product, store=store, price=offer.offer_price,
            currency=offer.currency, source="manual", offer=offer,
        )
        match_product_to_ingredients(product)
        imported += 1
    return imported


@transaction.atomic
def synchronize_provider(provider_id):
    provider = OfferProvider.objects.get(pk=provider_id, enabled=True)
    run = OfferSyncRun.objects.create(provider=provider, status="running")
    imported = 0
    try:
        adapter_class = PROVIDER_TYPES.get(provider.kind)
        if not adapter_class:
            raise ValueError("Provider requires an approved adapter.")
        adapter = adapter_class(provider) if provider.kind == OfferProvider.Kind.SALLING_GROUP else adapter_class()
        for record in adapter.fetch():
            store_data = record.get("store", {})
            external_store_id = store_data.get("external_id")
            if external_store_id:
                store = Store.objects.filter(
                    provider_identifiers__salling_group=external_store_id
                ).first()
                if not store:
                    store = Store(provider_identifiers={"salling_group": external_store_id})
                store.name = store_data["name"]
                store.chain = store_data.get("chain", "")
                store.address = store_data.get("street", "")
                store.postal_code = store_data.get("postal_code", "")
                store.city = store_data.get("city", "")
                store.latitude = store_data.get("latitude")
                store.longitude = store_data.get("longitude")
                store.opening_hours = store_data.get("opening_hours", [])
                store.currency = record["currency"]
                store.save()
            else:
                store, _ = Store.objects.get_or_create(
                    name=record.get("store_name", "Mock store"),
                    defaults={"currency": record["currency"]},
                )
            product, _ = Product.objects.get_or_create(
                name=record["product_name"],
                brand=record.get("brand", ""),
                defaults={
                    "category": record.get("category", ""),
                    "barcode": record.get("external_product_id", ""),
                },
            )
            offer, _ = GroceryOffer.objects.update_or_create(
                provider=provider,
                source_identifier=record.get("source_identifier", record.get("external_offer_id")),
                starts_at=record.get("starts_at", record.get("valid_from")),
                defaults={
                    "store": store, "product": product, "product_name": product.name,
                    "brand": product.brand, "category": product.category,
                    "description": record.get("description", ""),
                    "regular_price": record.get("regular_price", record.get("original_price")),
                    "offer_price": record["offer_price"],
                    "discount_amount": record.get("discount_amount"),
                    "discount_percentage": record.get("discount_percentage"),
                    "quantity": record.get("quantity"),
                    "unit": record.get("unit", ""),
                    "currency": record["currency"],
                    "ends_at": record.get("ends_at", record.get("valid_until")),
                    "image_url": record.get("image_url", ""),
                    "product_identifier": record.get("external_product_id", ""),
                    "original_source_text": record.get("original_source_text", record["product_name"]),
                    "retrieved_at": timezone.now(),
                    "raw_source_timestamp": record.get("raw_source_timestamp"),
                },
            )
            PriceRecord.objects.get_or_create(
                product=product, store=store, observed_at=offer.retrieved_at,
                defaults={"price": offer.offer_price, "currency": offer.currency, "source": "offer", "offer": offer},
            )
            match_product_to_ingredients(product)
            imported += 1
        GroceryOffer.objects.filter(provider=provider, ends_at__lt=timezone.now()).update(is_active=False)
        run.status = "succeeded"
        run.imported_count = imported
    except Exception as error:
        run.status = "failed"
        run.error_type = type(error).__name__
        run.error_message = str(error)[:500]
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()
    return run
