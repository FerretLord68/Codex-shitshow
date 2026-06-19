from django import forms

from .models import MealPlan, PlannedMeal


class MealPlanForm(forms.ModelForm):
    class Meta:
        model = MealPlan
        fields = ("name", "start_date", "end_date", "notes")
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}


class PlannedMealForm(forms.ModelForm):
    class Meta:
        model = PlannedMeal
        fields = ("recipe", "date", "meal_type", "servings", "guests", "notes", "status", "locked", "leftover_servings")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class GeneratePlanForm(forms.Form):
    only_empty = forms.BooleanField(required=False, initial=True)
    max_minutes = forms.IntegerField(required=False, min_value=1, max_value=600)
    max_cost = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2)
    prefer_inventory = forms.BooleanField(required=False, initial=True)
    prefer_offers = forms.BooleanField(required=False, initial=True)

