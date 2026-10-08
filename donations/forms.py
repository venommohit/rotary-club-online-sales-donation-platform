# forms.py
from django import forms


class DonationForm(forms.Form):
    amount = forms.DecimalField(min_value=5, max_value=10000, max_digits=8, decimal_places=2)
    donor_name = forms.CharField(max_length=150, label="Full name")
    donor_email = forms.EmailField(label="Email address")
    donor_message = forms.CharField(
        max_length=1000, required=False, widget=forms.Textarea, label="Message"
    )


class StaffLoginForm(forms.Form):
    """Checked against STAFF_USERNAME / STAFF_PASSWORD in views.dashboard_login."""
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, max_length=200)
