from django import forms


class ManualOfferImportForm(forms.Form):
    payload = forms.JSONField(widget=forms.Textarea, help_text="JSON array of offers")

