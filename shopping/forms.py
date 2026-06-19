from django import forms

from .models import ShoppingList, ShoppingListItem


class ShoppingListForm(forms.ModelForm):
    class Meta:
        model = ShoppingList
        fields = ("name", "start_date", "end_date", "meal_plan", "store", "status", "notes")
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}


class ShoppingListItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingListItem
        fields = ("product_name", "ingredient", "required_quantity", "unit", "category", "store", "preferred_brand", "priority", "notes")

