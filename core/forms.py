from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import (
    MenuItem,
    PopupAd,
    ProductImage,
    Restaurant,
    RiderProfile,
    User,
    VehicleType,
)


class UserAdminCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = (
            "phone",
            "full_name",
            "email",
            "gender",
            "is_staff",
            "is_superuser",
            "is_active",
        )

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Raw passwords are not stored. Use the link below to change the password.",
    )

    class Meta:
        model = User
        fields = "__all__"

    def clean_password(self):
        return self.initial.get("password")


class RiderProfileAdminForm(forms.ModelForm):
    class Meta:
        model = RiderProfile
        fields = "__all__"
        widgets = {
            "license_photo": forms.ClearableFileInput(attrs={"class": "vTextField"}),
            "citizenship_photo_front": forms.ClearableFileInput(attrs={"class": "vTextField"}),
            "citizenship_photo_back": forms.ClearableFileInput(attrs={"class": "vTextField"}),
            "vehicle_photo": forms.ClearableFileInput(attrs={"class": "vTextField"}),
        }


class VehicleTypeAdminForm(forms.ModelForm):
    class Meta:
        model = VehicleType
        fields = "__all__"
        widgets = {"icon": forms.ClearableFileInput()}


class RestaurantAdminForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = "__all__"
        widgets = {
            "logo": forms.ClearableFileInput(),
            "cover_photo": forms.ClearableFileInput(),
        }


class MenuItemAdminForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = "__all__"
        widgets = {"photo": forms.ClearableFileInput()}


class ProductImageAdminForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = "__all__"
        widgets = {"image": forms.ClearableFileInput()}


class PopupAdAdminForm(forms.ModelForm):
    class Meta:
        model = PopupAd
        fields = "__all__"
        widgets = {"image": forms.ClearableFileInput()}
