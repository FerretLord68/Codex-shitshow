from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label=_("E-mail"))
    display_name = forms.CharField(label=_("Name"), max_length=100)
    accept_terms = forms.BooleanField(label=_("I accept the terms and privacy policy"))

    class Meta:
        model = User
        fields = ("email", "display_name", "locale")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.terms_accepted_at = timezone.now()
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label=_("E-mail"))


class ResetRequestForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "locale")


class PasswordUpdateForm(PasswordChangeForm):
    pass


class PasswordResetConfirmForm(SetPasswordForm):
    pass

