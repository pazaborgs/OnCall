from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from shifts.models import Group, Shift, ShiftType, TradeRequest
from django.core import mail

User = get_user_model()


class OnCallSystemTest(TestCase):

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="userA@test.com", password="password123", full_name="User A"
        )
        self.user_b = User.objects.create_user(
            email="userB@test.com", password="password123", full_name="User B"
        )
        self.user_c = User.objects.create_user(
            email="userC@test.com", password="password123", full_name="User C"
        )

        self.group = Group.objects.create(name="UTI Geral", admin=self.user_a)
        self.group.members.add(self.user_a, self.user_b)

        self.shift_type = ShiftType.objects.create(
            name="Noturno", group=self.group, color="#000000"
        )
        self.client = Client()

    def test_dashboard_access_login_required(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_logout_functionality(self):
        self.client.force_login(self.user_a)
        try:
            logout_url = reverse("logout")
        except:
            logout_url = "/accounts/logout/"

        response = self.client.post(logout_url)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(response.status_code, 302)

    def test_create_shift(self):
        self.client.force_login(self.user_a)
        url = reverse("dashboard")
        data = {
            "shift_type": self.shift_type.id,
            "start_time": (timezone.now() + timedelta(days=1)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "duration": 12,
        }
        self.client.post(url, data)
        self.assertEqual(Shift.objects.count(), 1)
        self.assertEqual(Shift.objects.first().owner, self.user_a)

    def test_switch_shift_tradable(self):
        shift = Shift.objects.create(
            owner=self.user_a,
            group=self.group,
            shift_type=self.shift_type,
            start_time=timezone.now() + timedelta(days=2),
            duration=12,
        )

        self.client.force_login(self.user_a)
        self.client.post(reverse("switch_shift_tradable", args=[shift.id]))

        shift.refresh_from_db()
        self.assertTrue(shift.tradable)
        self.assertTrue(len(mail.outbox) > 0)

    def test_security_cannot_delete_others_shift(self):
        shift = Shift.objects.create(
            owner=self.user_a,
            group=self.group,
            shift_type=self.shift_type,
            start_time=timezone.now(),
            duration=12,
        )

        self.client.force_login(self.user_b)
        self.client.post(reverse("delete_shift", args=[shift.id]))

        self.assertTrue(Shift.objects.filter(id=shift.id).exists())

    def test_admin_can_create_shift_type(self):
        self.client.force_login(self.user_a)

        session = self.client.session
        session["active_group_id"] = self.group.id
        session.save()

        url = reverse("manage_shift_types")
        self.client.post(url, {"name": "Diurno Extra", "color": "#FF0000"})

        self.assertTrue(ShiftType.objects.filter(name="Diurno Extra").exists())

    def test_member_cannot_create_shift_type(self):
        self.client.force_login(self.user_b)

        session = self.client.session
        session["active_group_id"] = self.group.id
        session.save()

        url = reverse("manage_shift_types")
        response = self.client.post(url, {"name": "Hacker Type", "color": "#000"})

        self.assertFalse(ShiftType.objects.filter(name="Hacker Type").exists())
        self.assertEqual(response.status_code, 302)

    def test_join_group_via_link(self):
        self.client.force_login(self.user_c)
        url = reverse("join_via_link", args=[self.group.invite_token])

        response = self.client.get(url, follow=True)
        self.assertTrue(self.group.members.filter(id=self.user_c.id).exists())
        self.assertContains(
            response, f"Sucesso! Você entrou no grupo {self.group.name}"
        )

    def test_join_group_via_form_code(self):
        self.client.force_login(self.user_c)
        url = reverse("join_via_form")

        self.client.post(url, {"invite_token": self.group.invite_token}, follow=True)
        self.assertTrue(self.group.members.filter(id=self.user_c.id).exists())

    def test_reset_invite_token(self):
        self.client.force_login(self.user_a)
        old_token = self.group.invite_token

        self.client.get(reverse("reset_invite", args=[self.group.id]))
        self.group.refresh_from_db()

        self.assertNotEqual(old_token, self.group.invite_token)

    def test_full_trade_flow_pickup(self):
        shift = Shift.objects.create(
            owner=self.user_a,
            group=self.group,
            shift_type=self.shift_type,
            start_time=timezone.now() + timedelta(days=5),
            tradable=True,
        )

        self.client.force_login(self.user_b)
        self.client.post(
            reverse("create_trade_request"),
            {"target_shift_id": shift.id, "message": "Eu pego!"},
        )
        trade_req = TradeRequest.objects.first()

        self.client.force_login(self.user_a)
        response = self.client.post(
            reverse("accept_trade_request", args=[trade_req.id]), follow=True
        )

        shift.refresh_from_db()
        trade_req.refresh_from_db()

        self.assertEqual(shift.owner, self.user_b)
        self.assertEqual(trade_req.status, "APPROVED")
        self.assertContains(response, "Troca realizada!")

    def test_full_trade_flow_swap(self):
        shift_a = Shift.objects.create(
            owner=self.user_a,
            group=self.group,
            shift_type=self.shift_type,
            start_time=timezone.now() + timedelta(days=5),
            tradable=True,
        )
        shift_b = Shift.objects.create(
            owner=self.user_b,
            group=self.group,
            shift_type=self.shift_type,
            start_time=timezone.now() + timedelta(days=10),
            tradable=False,
        )

        self.client.force_login(self.user_b)
        self.client.post(
            reverse("create_trade_request"),
            {
                "target_shift_id": shift_a.id,
                "offered_shift_id": shift_b.id,
                "message": "Troca?",
            },
        )
        trade_req = TradeRequest.objects.first()

        self.client.force_login(self.user_a)
        self.client.post(
            reverse("accept_trade_request", args=[trade_req.id]), follow=True
        )

        shift_a.refresh_from_db()
        shift_b.refresh_from_db()

        self.assertEqual(shift_a.owner, self.user_b)
        self.assertEqual(shift_b.owner, self.user_a)

    def test_reject_trade_request(self):
        shift = Shift.objects.create(
            owner=self.user_a,
            group=self.group,
            shift_type=self.shift_type,
            start_time=timezone.now() + timedelta(days=5),
            tradable=True,
        )

        self.client.force_login(self.user_b)
        self.client.post(reverse("create_trade_request"), {"target_shift_id": shift.id})
        trade_req = TradeRequest.objects.first()

        self.client.force_login(self.user_a)
        self.client.post(reverse("reject_trade_request", args=[trade_req.id]))

        trade_req.refresh_from_db()
        shift.refresh_from_db()

        self.assertEqual(trade_req.status, "REJECTED")
        self.assertEqual(shift.owner, self.user_a)

    def test_prevent_duplicate_trade_request(self):
        shift = Shift.objects.create(
            owner=self.user_a,
            group=self.group,
            shift_type=self.shift_type,
            start_time=timezone.now() + timedelta(days=5),
            tradable=True,
        )

        self.client.force_login(self.user_b)
        url = reverse("create_trade_request")
        data = {"target_shift_id": shift.id}

        self.client.post(url, data)
        self.assertEqual(TradeRequest.objects.count(), 1)

        self.client.post(url, data)
        self.assertEqual(TradeRequest.objects.count(), 1)
