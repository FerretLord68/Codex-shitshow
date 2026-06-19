from django import forms

from .models import InventoryItem, StorageLocation, WasteRecord


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = ("name", "kind")


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = (
            "product_name", "ingredient", "brand", "quantity", "unit", "package_size", "packages",
            "location", "purchase_date", "opened_date", "best_before_date", "expiration_date",
            "price_paid", "store", "barcode", "batch", "notes", "status",
        )
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "opened_date": forms.DateInput(attrs={"type": "date"}),
            "best_before_date": forms.DateInput(attrs={"type": "date"}),
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
        }


class WasteRecordForm(forms.ModelForm):
    class Meta:
        model = WasteRecord
        fields = ("item", "ingredient", "quantity", "unit", "date", "reason", "custom_reason", "estimated_value", "location")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

