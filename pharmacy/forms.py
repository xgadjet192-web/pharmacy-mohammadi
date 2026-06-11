from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import PharmacyUser, Product
import secrets


# -----------------------------------------
#   فرم ساخت کاربر
# -----------------------------------------
class PharmacyUserCreationForm(UserCreationForm):

    account_type = forms.ChoiceField(
        choices=[
            ('normal', 'کاربر عادی'),
            ('staff', 'پرسنل'),
            ('admin', 'ادمین جنگو')
        ],
        label="نوع دسترسی",
        widget=forms.RadioSelect
    )

    class Meta:
        model = PharmacyUser
        fields = ["username", "email", "phone", "address", "postal_code", "profile_image"]

    def save(self, commit=True):
        user = super().save(commit=False)

        account_type = self.cleaned_data.get("account_type")
        if account_type == 'staff':
            user.is_staff = True
            user.is_superuser = False
        elif account_type == 'admin':
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_staff = False
            user.is_superuser = False

        if commit:
            user.save()

        return user


# -----------------------------------------
#   فرم ویرایش کاربر
# -----------------------------------------
class PharmacyUserChangeForm(UserChangeForm):

    account_type = forms.ChoiceField(
        choices=[
            ('normal', 'کاربر عادی'),
            ('staff', 'پرسنل'),
            ('admin', 'ادمین جنگو')
        ],
        label="نوع دسترسی",
        widget=forms.RadioSelect
    )

    class Meta:
        model = PharmacyUser
        fields = [
            "username", "email", "phone",
            "address", "postal_code", "profile_image", "is_active"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.is_superuser:
            self.fields["account_type"].initial = "admin"
        elif self.instance.is_staff:
            self.fields["account_type"].initial = "staff"
        else:
            self.fields["account_type"].initial = "normal"
