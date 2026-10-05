from django import forms

from .models import ConsultationRequest, ContactMessage


class ConsultationRequestForm(forms.ModelForm):
    # Honeypot field — invisible to real users via CSS, bots tend to fill every input.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ConsultationRequest
        fields = ["name", "phone", "email", "city", "project_type", "message"]

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("درخواست نامعتبر تشخیص داده شد.")
        return ""


class ContactMessageForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ["name", "phone", "email", "message"]

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("درخواست نامعتبر تشخیص داده شد.")
        return ""
