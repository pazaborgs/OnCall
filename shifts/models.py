from django.db import models
from django.conf import settings
from datetime import timedelta
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Group(models.Model):
    """
    Define os grupos
    """

    class Mode(models.TextChoices):
        SUPERVISED = "SUPERVISED", "Supervisionado"
        SELF_MANAGED = "SELF_MANAGED", "Auto-Gerenciado"

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="administered_groups",
        verbose_name="Administrador",
    )

    name = models.CharField("Nome do Grupo/Hospital", max_length=100)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="work_groups", verbose_name="Membros"
    )
    mode = models.CharField(
        max_length=20, choices=Mode.choices, default=Mode.SELF_MANAGED
    )
    invite_token = models.CharField(max_length=50, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invite_token:
            self.invite_token = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ShiftType(models.Model):
    """
    Define os tipos de plantão e suas cores no calendário.
    """

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="shift_types",
        null=True,
        blank=True,
    )
    name = models.CharField("Tipo de Plantão", max_length=100)
    color = models.CharField(
        "Cor (Hex)",
        max_length=7,
        default="#0d6efd",
        help_text="Ex: #FF0000 para vermelho",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Shift(models.Model):
    """
    Model do Plantão
    """

    class Duration(models.IntegerChoices):
        SIX = 6, "6 Horas"
        TWELVE = 12, "12 Horas"
        TWENTY_FOUR = 24, "24 Horas"

    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="shifts", verbose_name="Grupo"
    )
    shift_type = models.ForeignKey(
        ShiftType, on_delete=models.CASCADE, verbose_name="Tipo de Plantão"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shifts"
    )
    start_time = models.DateTimeField("Início")
    duration = models.IntegerField(
        "Duração", choices=Duration.choices, default=Duration.TWELVE
    )
    end_time = models.DateTimeField("Fim", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tradable = models.BooleanField("Disponível para Troca", default=False)

    class Meta:
        ordering = ["start_time"]
        verbose_name = "Plantão"
        verbose_name_plural = "Plantões"

    def __str__(self):
        return f"{self.shift_type} - ({self.get_duration_display()})"

    def save(self, *args, **kwargs):
        if self.start_time and self.duration:
            self.end_time = self.start_time + timedelta(hours=self.duration)
        super().save(*args, **kwargs)


class TradeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente (Aguardando Dono)"
        ACCEPTED_BY_OWNER = "ACCEPTED_BY_OWNER", "Aceito pelo Dono (Aguardando Admin)"
        APPROVED = "APPROVED", "Aprovado e Finalizado"
        REJECTED = "REJECTED", "Recusado"
        CANCELLED = "CANCELLED", "Cancelado"

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trade_requests_sent",
    )
    target_shift = models.ForeignKey(
        Shift, on_delete=models.CASCADE, related_name="incoming_trade_requests"
    )  # Troca Alvo
    offered_shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_trade_requests",
    )  # Contra-Oferta
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Troca: {self.requester} quer {self.target_shift}"
