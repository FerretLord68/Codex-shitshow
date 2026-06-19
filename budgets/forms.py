from django import forms

from .models import HouseholdBudget


class BudgetForm(forms.ModelForm):
    class Meta:
        model = HouseholdBudget
        fields = ("period", "start_date", "end_date", "amount", "currency", "savings_priority", "convenience_priority")
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}

