from django import forms

from .models import Recipe


class RecipeForm(forms.ModelForm):
    instructions_text = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = Recipe
        fields = (
            "name", "description", "servings", "preparation_minutes", "cooking_minutes",
            "categories", "cuisine", "allergens", "dietary_tags", "calories_kcal",
            "protein_g", "carbohydrate_g", "fat_g", "fibre_g", "sugar_g", "sodium_mg",
            "nutrition_quality", "estimated_cost", "difficulty", "equipment", "source",
            "source_url", "attribution", "visibility",
        )


class RecipeImportForm(forms.Form):
    method = forms.ChoiceField(choices=[("json", "JSON"), ("url", "URL")])
    payload = forms.CharField(widget=forms.Textarea)


class RecipeImageForm(forms.Form):
    image = forms.ImageField()
    alt_text = forms.CharField(max_length=250)
