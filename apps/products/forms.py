from django import forms

from .models import ProductOrder


class ProductOrderForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)  # honeypot

    class Meta:
        model = ProductOrder
        fields = ["name", "company", "phone", "city", "quantity", "model_type", "usage", "message"]

    def clean_phone(self):
        raw = self.cleaned_data["phone"].strip()
        digits = "".join(ch for ch in raw.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")) if ch.isdigit())
        if len(digits) < 8:
            raise forms.ValidationError("شماره تماس معتبر وارد کنید.")
        return raw

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("درخواست نامعتبر تشخیص داده شد.")
        return ""
