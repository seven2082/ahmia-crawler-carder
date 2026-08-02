from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import OnionProfile, Category, Tag


class ProfileEditForm(forms.Form):
    """Form for suggesting edits to a profile."""

    name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tags = forms.CharField(
        max_length=200,
        required=False,
        help_text=_('Comma-separated tags'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        if len(desc) > 500:
            desc = desc[:500]
        return desc


class ClaimForm(forms.Form):
    """Form for claiming profile ownership."""

    confirm = forms.BooleanField(
        required=True,
        label=_('I confirm I am the owner of this site')
    )
