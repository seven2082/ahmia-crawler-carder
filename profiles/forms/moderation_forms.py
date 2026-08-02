from django import forms
from django.utils.translation import gettext_lazy as _

from ahmia.validators import validate_onion_url


class MigrationReportForm(forms.Form):
    """Form for reporting a site migration."""

    old_domain = forms.CharField(
        max_length=70,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True})
    )
    new_url = forms.URLField(
        max_length=255,
        validators=[validate_onion_url],
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'http://newdomain.onion/'})
    )
    evidence_url = forms.URLField(
        max_length=500,
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'URL showing migration notice'})
    )
    evidence_text = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the evidence'})
    )

    def clean_new_url(self):
        url = self.cleaned_data.get('new_url', '')
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or url


class EditReviewForm(forms.Form):
    """Form for reviewing an edit."""

    ACTION_CHOICES = [
        ('approve', _('Approve')),
        ('reject', _('Reject')),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    notes = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
