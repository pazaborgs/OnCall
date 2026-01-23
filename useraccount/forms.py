from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        # Adicionei full_name e role para já preencher ao criar
        fields = ("email", "full_name", "role", "phone")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("email", "full_name", "role", "is_active", "is_staff")


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "role"]

        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Seu nome completo"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "nome@exemplo.com"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "(11) 99999-9999"}
            ),
            "role": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "full_name": "Nome Completo",
            "email": "E-mail",
            "phone": "Telefone (WhatsApp)",
            "role": "Função/Cargo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].disabled = True
        self.fields["email"].help_text = (
            "Por segurança, o e-mail não pode ser alterado aqui."
        )
