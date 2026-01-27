from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from shifts.models import Group, Shift, ShiftType, TradeRequest
from django.core import mail

User = get_user_model()


class OnCallFullJourneyTest(TestCase):

    def setUp(self):
        """
        Setup Inicial. Roda a cada teste.
        """
        print("\n" + "=" * 100)
        print("🚀 INICIANDO AMBIENTE DE TESTE")

        # Criar Usuários Completos (admin e colaborador)
        self.user_admin = User.objects.create_user(
            email="chefe@hospital.com", password="password123", full_name="Dr. Chefe"
        )
        self.user_colaborador = User.objects.create_user(
            email="plantonista@hospital.com",
            password="password123",
            full_name="Dra. Ana",
        )

        # Cliente HTTP (navegador fake)

        self.client = Client()
        print(
            f" ✅ Usuários criados: \n- {self.user_admin}\n - {self.user_colaborador}"
        )

    def log(self, msg):
        """Função auxiliar para melhorar output"""
        print(f"   👉 {msg}")

    # -------------------------------------------------------------------------
    # 🧪 Bateria 1: Perfil e Grupos
    # -------------------------------------------------------------------------

    def test_01_user_profile_edit(self):
        print("\n🧪 TESTE 01: Editar Perfil do Usuário")

        # Simula o usuário editando seus dados (Nome e Telefone, por exemplo)

        self.user_colaborador.full_name = "Dra. Ana Maria"
        self.user_colaborador.save()

        # Verifica no banco

        self.user_colaborador.refresh_from_db()
        self.assertEqual(self.user_colaborador.full_name, "Dra. Ana Maria")
        self.log("Perfil atualizado com sucesso no banco de dados.")

    def test_02_group_lifecycle(self):
        print("\n🧪 TESTE 02: Ciclo de Vida do Grupo (Criar, Entrar, Link, Deletar)")

        # Cria Grupo

        self.client.force_login(self.user_admin)
        response = self.client.post(
            reverse("create_group"),
            {
                "name": "Emergência 24h",
                "mode": "SELF_MANAGED",
            },
            follow=True,
        )

        group = Group.objects.first()
        self.assertIsNotNone(group)
        self.log(f"Grupo '{group.name}' criado pelo Admin.")

        # Reset de link

        old_token = group.invite_token
        self.client.get(reverse("reset_invite", args=[group.id]))
        group.refresh_from_db()
        self.assertNotEqual(old_token, group.invite_token)
        self.log("Token de convite regenerado com sucesso.")

        # Colaborador entra via link

        self.client.force_login(self.user_colaborador)
        url_convite = reverse("join_via_link", args=[group.invite_token])
        self.client.get(url_convite, follow=True)
        self.assertTrue(group.members.filter(id=self.user_colaborador.id).exists())
        self.log("Colaborador entrou no grupo usando o link.")

        # Deletar Grupo

        self.client.force_login(self.user_admin)  # Admin
        self.client.post(reverse("delete_group", args=[group.id]))
        self.assertFalse(Group.objects.filter(id=group.id).exists())
        self.log("Grupo excluído permanentemente.")

    # -------------------------------------------------------------------------
    # 🧪 Bateria 2: Plantões (CRUD)
    # -------------------------------------------------------------------------

    def test_03_shift_management(self):
        print("\n🧪 TESTE 03: Gestão de Plantões (Tipos, Criação, Edição, Delete)")

        # Setup do grupo

        group = Group.objects.create(name="UTI Teste", admin=self.user_admin)
        group.members.add(self.user_admin)
        self.client.force_login(self.user_admin)
        session = self.client.session
        session["active_group_id"] = group.id
        session.save()

        # Criar tipo de plantão (admin)

        self.client.post(
            reverse("manage_shift_types"),
            {"name": "Plantão Noturno", "color": "#000000"},
        )
        shift_type = ShiftType.objects.first()
        self.assertIsNotNone(shift_type)
        self.log(f"Tipo '{shift_type.name}' criado.")

        # Criar plantão

        start_time = (timezone.now() + timedelta(days=1)).replace(microsecond=0)
        self.client.post(
            reverse("dashboard"),
            {"shift_type": shift_type.id, "start_time": start_time, "duration": 12},
        )

        shift = Shift.objects.first()
        self.assertIsNotNone(shift)
        self.assertEqual(shift.owner, self.user_admin)
        self.log("Plantão criado na agenda.")

        # Editar plantão

        self.client.post(
            reverse("edit_shift", args=[shift.id]),
            {
                "shift_type": shift_type.id,
                "start_time": start_time,
                "duration": 24,  # 12 para 24 (mudança)
            },
        )

        shift.refresh_from_db()
        self.assertEqual(shift.duration, 24)
        self.log("Plantão editado (duração alterada para 24h).")

        # Deletar plantão

        self.client.post(reverse("delete_shift", args=[shift.id]))
        self.assertFalse(Shift.objects.filter(id=shift.id).exists())
        self.log("Plantão removido da agenda.")

    # -------------------------------------------------------------------------
    # 🧪 Bateria 3: Sistema de Trocas (Coração)
    # -------------------------------------------------------------------------

    def test_04_trade_pickup_only_and_emails(self):
        print("\n🧪 TESTE 04: Troca Simples + Verificação de E-mails")

        # Configuração do grupo

        group = Group.objects.create(name="Trocas Email", admin=self.user_admin)
        group.members.add(self.user_admin, self.user_colaborador)
        st = ShiftType.objects.create(name="Geral", group=group)

        shift = Shift.objects.create(
            owner=self.user_admin,
            group=group,
            shift_type=st,
            start_time=timezone.now() + timedelta(days=5),
            duration=12,
            tradable=True,
        )

        # Fase: Proposta
        mail.outbox = []  # Limpa a caixa

        self.client.force_login(self.user_colaborador)
        self.client.post(
            reverse("create_trade_request"),
            {"target_shift_id": shift.id, "message": "Posso cobrir!"},
        )

        # VERIFICAÇÃO DE EMAIL 1: O Admin deve receber aviso de nova proposta

        self.assertEqual(len(mail.outbox), 1, "Deveria ter enviado 1 email de proposta")
        email_proposta = mail.outbox[0]

        self.assertIn(self.user_admin.email, email_proposta.to)
        self.assertIn("Nova Proposta", email_proposta.subject)
        self.log("📧 Email de nova proposta verificado com sucesso.")

        # Fase: Aceite
        mail.outbox = []  # Limpa a caixa novamente

        trade_req = TradeRequest.objects.first()
        self.client.force_login(self.user_admin)
        self.client.post(reverse("accept_trade_request", args=[trade_req.id]))

        # VERIFICAÇÃO DE EMAIL 2: A Ana deve receber confirmação

        self.assertEqual(
            len(mail.outbox), 1, "Deveria ter enviado 1 email de confirmação"
        )
        email_confirmacao = mail.outbox[0]

        self.assertIn(self.user_colaborador.email, email_confirmacao.to)
        self.assertIn("Confirmada", email_confirmacao.subject)
        self.log("📧 Email de confirmação de troca verificado com sucesso.")

    def test_05_trade_with_swap(self):
        print("\n🧪 TESTE 05: Troca com Contra-Oferta (Um pelo Outro)")

        group = Group.objects.create(name="Trocas", admin=self.user_admin)
        group.members.add(self.user_admin, self.user_colaborador)
        st = ShiftType.objects.create(name="Geral", group=group)

        # Plantão do Admin (Dia 5)

        shift_admin = Shift.objects.create(
            owner=self.user_admin,
            group=group,
            shift_type=st,
            start_time=timezone.now() + timedelta(days=5),
            duration=12,
            tradable=True,
        )
        # Plantão da Ana (Dia 10)

        shift_ana = Shift.objects.create(
            owner=self.user_colaborador,
            group=group,
            shift_type=st,
            start_time=timezone.now() + timedelta(days=10),
            duration=12,
        )

        # 1. Ana propõe: "Pego o seu do dia 5, te dou o meu do dia 10"

        self.client.force_login(self.user_colaborador)
        self.client.post(
            reverse("create_trade_request"),
            {
                "target_shift_id": shift_admin.id,
                "offered_shift_id": shift_ana.id,  # Contra-oferta
                "message": "Troca pau a pau?",
            },
        )
        self.log("Ana propôs uma troca de datas.")

        # Admin Aceita

        trade_req = TradeRequest.objects.first()
        self.client.force_login(self.user_admin)
        self.client.post(reverse("accept_trade_request", args=[trade_req.id]))

        # Verificação

        shift_admin.refresh_from_db()
        shift_ana.refresh_from_db()

        self.assertEqual(shift_admin.owner, self.user_colaborador)
        self.assertEqual(shift_ana.owner, self.user_admin)
        self.log("✅ Sucesso: Ambos os plantões trocaram de dono corretamente.")
