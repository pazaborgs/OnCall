from django import forms
from .models import Shift, Group, ShiftType


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "mode"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ex: UTI Santa Casa"}
            ),
            "mode": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "name": "Nome do Grupo/Hospital",
            "mode": "Modo de Gestão",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mode"].choices = [
            ("SELF_MANAGED", "Auto-Gerenciado"),
            ("SUPERVISED", "Supervisionado (Em breve...)"),
        ]
        self.initial["mode"] = "SELF_MANAGED"

    def clean_mode(self):
        mode = self.cleaned_data.get("mode")
        if mode == "SUPERVISED":
            raise forms.ValidationError(
                "O modo Supervisionado ainda não está disponível. Por favor, selecione Auto-Gerenciado."
            )
        return mode


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["shift_type", "start_time", "duration"]
        widgets = {
            "start_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "shift_type": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.Select(attrs={"class": "form-select"}),  # Dropdown bonito
        }
        labels = {
            "shift_type": "Onde/Tipo",
            "start_time": "Início do Plantão",
            "duration": "Duração (Horas)",
        }


class ShiftTypeForm(forms.ModelForm):
    class Meta:
        model = ShiftType
        fields = ["name", "color", "is_active"]
        widgets = {
            "color": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "form-control form-control-color w-100",
                }
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ex: Plantão Noturno"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "name": "Tipo de Plantão",
            "color": "Cor da Etiqueta",
            "is_active": "Ativo?",
        }
