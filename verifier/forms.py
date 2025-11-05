from django import forms


class PharmacyForm(forms.Form):
    pharmacy_name = forms.CharField(label='Pharmacy Name', max_length=255)
    pbm_name = forms.CharField(label='PBM Name (optional)', max_length=255, required=False)
    address = forms.CharField(label='Address (optional)', max_length=500, required=False, widget=forms.TextInput(attrs={'placeholder': '123 Main St, City, State'}) )

