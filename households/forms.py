from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import Household, HouseholdMemberProfile, Membership


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ("name", "currency", "locale", "timezone")

    def save(self, commit=True):
        household = super().save(commit=False)
        if not household.slug:
            base = slugify(household.name)[:110] or "household"
            household.slug = f"{base}-{__import__('secrets').token_hex(3)}"
        if commit:
            household.save()
        return household


class InvitationForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"))
    role = forms.ChoiceField(choices=Membership.Role.choices, initial=Membership.Role.MEMBER)


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = HouseholdMemberProfile
        fields = (
            "display_name", "age_group", "portion_multiplier", "daily_calorie_target",
            "protein_target_g", "carbohydrate_target_g", "fat_target_g",
            "dietary_preferences", "allergies", "foods_to_avoid", "disliked_foods",
            "favourite_foods", "notes",
        )

