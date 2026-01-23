import calendar
import uuid
from datetime import date, timedelta
from itertools import groupby

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .forms import GroupForm, ShiftForm, ShiftTypeForm
from .models import Group, Shift, ShiftType, TradeRequest

# ------------------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------------------


def _get_redirect_url(request, fallback="dashboard"):
    """
    Retorna a URL anterior (HTTP_REFERER) para manter os filtros ativos
    após uma ação (editar, deletar, trocar), ou o fallback se não existir.
    """
    return request.META.get("HTTP_REFERER") or reverse(fallback)


# ------------------------------------------------------------------------------
# Dashboard Principal
# ------------------------------------------------------------------------------


@login_required
def dashboard(request):
    today = timezone.now().date()

    # Desativa plantões passados automaticamente
    Shift.objects.filter(is_active=True, end_time__date__lt=today).update(
        is_active=False
    )

    # --- Gestão de Grupo Ativo ---

    user_groups = request.user.work_groups.all()
    if not user_groups.exists():
        return render(request, "shifts/no_group.html", {"group_form": GroupForm()})

    active_group_id = request.GET.get("group_id") or request.session.get(
        "active_group_id"
    )
    active_group = user_groups.filter(id=active_group_id).first() or user_groups.first()

    if active_group:
        request.session["active_group_id"] = active_group.id

    # --- Criação Rápida de Plantão (Modal) ---

    if request.method == "POST":
        form = ShiftForm(request.POST)
        if form.is_valid():
            shift = form.save(commit=False)
            shift.owner = request.user
            shift.group = active_group
            shift.save()
            messages.success(request, "Plantão adicionado com sucesso.")
            return HttpResponseRedirect(_get_redirect_url(request))  # Mantém filtros
    else:
        form = ShiftForm()

    # --- Filtros e Navegação Temporal ---

    try:
        req_year = int(request.GET.get("year", today.year))
        req_month = int(request.GET.get("month", today.month))
    except ValueError:
        req_year, req_month = today.year, today.month

    current_date = date(req_year, req_month, 1)

    # Parâmetros de Filtro

    filter_user_id = request.GET.get("filter_user")
    filter_type_id = request.GET.get("filter_type")
    filter_period_scope = request.GET.get("view_mode")

    # Define Modo de Visualização

    display_mode = "user_extract" if filter_user_id else "monthly_grid"

    # Query Base

    filters = {
        "group": active_group,
        "start_time__year": req_year,
    }

    # Aplicação dos Filtros

    if display_mode == "user_extract":
        filters["owner__id"] = filter_user_id
        if filter_period_scope and filter_period_scope != "all":
            try:
                filters["start_time__month"] = int(filter_period_scope)
            except ValueError:
                pass
    elif display_mode == "monthly_grid":
        filters["start_time__month"] = req_month

    if filter_type_id:
        filters["shift_type__id"] = filter_type_id

    # Busca Plantões

    shifts = (
        Shift.objects.filter(**filters)
        .select_related("shift_type", "owner")
        .order_by("start_time")
    )

    # Organização dos Dias (Agenda)

    agenda_days = []

    if display_mode in ["user_extract", "annual_calendar"]:
        for date_obj, day_shifts_iter in groupby(
            shifts, key=lambda s: s.start_time.date()
        ):
            agenda_days.append(
                {
                    "date": date_obj,
                    "day_number": date_obj.day,
                    "is_today": date_obj == today,
                    "is_weekend": date_obj.weekday() >= 5,
                    "shifts": list(day_shifts_iter),
                    "show_month": True,
                }
            )

    elif display_mode == "monthly_grid":

        # Preenchimento de calendário completo (1 a 31)

        _, num_days = calendar.monthrange(req_year, req_month)
        all_shifts_list = list(shifts)

        for day_num in range(1, num_days + 1):
            date_obj = date(req_year, req_month, day_num)
            day_shifts = [s for s in all_shifts_list if s.start_time.day == day_num]

            agenda_days.append(
                {
                    "date": date_obj,
                    "day_number": day_num,
                    "is_today": date_obj == today,
                    "is_weekend": date_obj.weekday() >= 5,
                    "shifts": day_shifts,
                    "show_month": False,
                }
            )

    # --- Contextos ---

    # Plantões futuros (Para oferecer em troca)
    user_future_shifts = []
    if active_group:
        user_future_shifts = Shift.objects.filter(
            group=active_group,
            owner=request.user,
            start_time__gte=timezone.now(),
            is_active=True,
        ).order_by("start_time")

    # Propostas recebidas (Incoming)
    incoming_trades = TradeRequest.objects.filter(
        target_shift__owner=request.user, status=TradeRequest.Status.PENDING
    ).select_related("requester", "target_shift", "offered_shift")

    # Minhas solicitações pendentes (Para bloquear botões)

    my_pending_requests = TradeRequest.objects.filter(
        requester=request.user, status=TradeRequest.Status.PENDING
    ).values_list("target_shift_id", flat=True)

    context = {
        "active_group": active_group,
        "current_date": current_date,
        "req_year": req_year,
        "agenda_days": agenda_days,
        # Controle Visual e Filtros
        "display_mode": display_mode,
        "filter_period_scope": filter_period_scope,
        "selected_user_id": filter_user_id if filter_user_id else None,
        "selected_type_id": filter_type_id if filter_type_id else None,
        "years_range": range(today.year - 1, today.year + 2),
        # Forms e Dados
        "form": form,  # Shift form
        "group_form": GroupForm(),
        "user_groups": user_groups,
        "group_members": active_group.members.all(),
        "group_shift_types": ShiftType.objects.all(),
        # Navegação
        "prev_date": (current_date - timedelta(days=1)).replace(day=1),
        "next_date": (current_date + timedelta(days=32)).replace(day=1),
        # Trocas
        "user_future_shifts": user_future_shifts,
        "incoming_trades": incoming_trades,
        "my_pending_requests": my_pending_requests,
    }

    return render(request, "shifts/dashboard.html", context)


# ------------------------------------------------------------------------------
# Gestão de Grupos
# ------------------------------------------------------------------------------


@login_required
def _process_group_entry(request, group):
    if request.user in group.members.all():
        messages.info(request, f"Você já é membro do grupo {group.name}.")
    else:
        group.members.add(request.user)
        messages.success(request, f"Sucesso! Você entrou no grupo {group.name}.")
    request.session["active_group_id"] = group.id


@login_required
@login_required
def create_group(request):
    if request.method == "POST":
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.admin = request.user
            group.save()
            group.members.add(request.user)

            request.session["active_group_id"] = group.id

            messages.success(request, f"Grupo '{group.name}' criado com sucesso!")
            return redirect("dashboard")
        else:
            messages.error(request, "Erro ao criar grupo. Verifique os dados.")
            return redirect("dashboard")

    return redirect("dashboard")


@login_required
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if group.admin != request.user:
        messages.error(request, "Permissão negada.")
        return redirect("dashboard")

    if request.method == "POST":
        if str(request.session.get("active_group_id")) == str(group.id):
            del request.session["active_group_id"]

        group.delete()
        messages.success(request, "Grupo excluído.")
        return redirect("dashboard")

    return redirect("dashboard")


@login_required
def join_via_link(request, token):
    group = get_object_or_404(Group, invite_token=token)
    _process_group_entry(request, group)
    return redirect("dashboard")


@login_required
def join_via_form(request):
    if request.method == "POST":
        raw_input = request.POST.get("invite_token", "").strip()
        if not raw_input:
            messages.error(request, "Insira um código válido.")
            return redirect("dashboard")

        token = raw_input.rstrip("/").split("/")[-1]
        try:
            group = Group.objects.get(invite_token=token)
            _process_group_entry(request, group)
        except Group.DoesNotExist:
            messages.error(request, "Código inválido.")

    return redirect("dashboard")


@login_required
def reset_invite_token(request, group_id):
    # TODO: Somente admin reseta?
    group = get_object_or_404(Group, id=group_id)
    if request.user in group.members.all():
        group.invite_token = str(uuid.uuid4())[:8]
        group.save()
        messages.success(request, "Link redefinido.")
    return HttpResponseRedirect(_get_redirect_url(request))


# ------------------------------------------------------------------------------
# Gestão de Plantões (CRUD)
# ------------------------------------------------------------------------------


@login_required
def edit_shift(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    if shift.owner != request.user:
        messages.error(request, "Permissão negada.")
        return redirect("dashboard")

    if request.method == "POST":
        form = ShiftForm(request.POST, instance=shift)
        if form.is_valid():
            form.save()
            messages.success(request, "Plantão atualizado.")
            return redirect("dashboard")
    else:
        form = ShiftForm(instance=shift)

    return render(request, "shifts/edit_shift.html", {"form": form, "shift": shift})


@login_required
def delete_shift(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    if shift.owner != request.user:
        messages.error(request, "Permissão negada.")
    elif request.method == "POST":
        shift.delete()
        messages.success(request, "Plantão removido.")

    return HttpResponseRedirect(_get_redirect_url(request))


@login_required
def manage_shift_types(request):
    group_id = request.session.get("active_group_id")
    if not group_id:
        return redirect("dashboard")

    group = get_object_or_404(Group, id=group_id)
    if group.admin != request.user:
        return redirect("dashboard")

    if request.method == "POST":
        form = ShiftTypeForm(request.POST)
        if form.is_valid():
            st = form.save(commit=False)
            st.group = group
            st.save()
            messages.success(request, "Tipo adicionado.")
            return HttpResponseRedirect(
                _get_redirect_url(request, "manage_shift_types")
            )

    types = ShiftType.objects.filter(group=group)
    return render(
        request,
        "shifts/manage_shift_types.html",
        {"group": group, "types": types, "form": ShiftTypeForm()},
    )


# ------------------------------------------------------------------------------
# Sistema de Trocas (Trade System)
# ------------------------------------------------------------------------------


@login_required
def switch_shift_tradable(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)

    if shift.owner != request.user:
        messages.error(request, "Permissão negada.")
        return HttpResponseRedirect(_get_redirect_url(request))

    if request.method == "POST":
        if shift.tradable:
            has_pending = TradeRequest.objects.filter(
                target_shift=shift, status=TradeRequest.Status.PENDING
            ).exists()
            if has_pending:
                messages.warning(
                    request,
                    "Não é possível cancelar oferta: Existem propostas pendentes para este plantão.",
                )
                return HttpResponseRedirect(_get_redirect_url(request))

        shift.tradable = not shift.tradable
        shift.save()

        if shift.tradable:
            # Notificação por E-mail
            group_members = shift.group.members.exclude(id=request.user.id)
            recipients = [m.email for m in group_members if m.email]

            if recipients:
                subject = f"[On Call] Oportunidade em {shift.group.name}"
                message = (
                    f"Olá!\n\n{request.user.full_name or request.user.email} disponibilizou um plantão.\n"
                    f"📅 {shift.start_time.strftime('%d/%m')} - {shift.shift_type.name}\n\n"
                    f"Acesse: {request.scheme}://{request.get_host()}/dashboard/"
                )
                try:
                    email = EmailMessage(
                        subject=subject,
                        body=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[settings.DEFAULT_FROM_EMAIL],
                        bcc=recipients,
                    )
                    email.send(fail_silently=True)
                except Exception:
                    pass

            messages.success(request, "Plantão ofertado para troca.")
        else:
            messages.info(request, "Plantão retirado das trocas.")

    return HttpResponseRedirect(_get_redirect_url(request))


@login_required
def create_trade_request(request):
    if request.method == "POST":
        target_id = request.POST.get("target_shift_id")
        offered_id = request.POST.get("offered_shift_id")
        msg = request.POST.get("message")

        if not target_id:
            return redirect("dashboard")

        try:
            target_shift = Shift.objects.get(id=target_id)
        except Shift.DoesNotExist:
            return redirect("dashboard")

        # Validações
        if target_shift.owner == request.user:
            return redirect("dashboard")
        if not target_shift.tradable:
            messages.error(request, "Plantão indisponível.")
            return redirect("dashboard")

        # Check Duplicidade
        if TradeRequest.objects.filter(
            requester=request.user,
            target_shift=target_shift,
            status=TradeRequest.Status.PENDING,
        ).exists():
            messages.warning(
                request, "Você já tem uma proposta pendente para este plantão."
            )
            return HttpResponseRedirect(_get_redirect_url(request))

        trade = TradeRequest(
            group=target_shift.group,
            requester=request.user,
            target_shift=target_shift,
            message=msg,
        )

        if offered_id:
            try:
                offered = Shift.objects.get(id=offered_id, owner=request.user)
                trade.offered_shift = offered
            except Shift.DoesNotExist:
                pass

        trade.save()

        try:
            subject = f"🔄 Nova Proposta de Troca: {target_shift.start_time.strftime('%d/%m')}"
            html_content = render_to_string(
                "shifts/emails/trade_proposal.html",
                {
                    "requester": request.user,
                    "target": target_shift,
                    "offered": trade.offered_shift,
                    "msg": msg,
                    "dashboard_url": f"{request.scheme}://{request.get_host()}/dashboard/",
                },
            )
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [target_shift.owner.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=True)
        except Exception:
            pass

        messages.success(request, "Proposta enviada com sucesso.")
        return HttpResponseRedirect(_get_redirect_url(request))

    return redirect("dashboard")


@login_required
@transaction.atomic
def accept_trade_request(request, trade_id):
    trade = get_object_or_404(TradeRequest, id=trade_id)

    if request.user != trade.target_shift.owner:
        messages.error(request, "Ação não autorizada.")
        return redirect("dashboard")

    if trade.status != TradeRequest.Status.PENDING:
        messages.warning(request, "Solicitação já finalizada.")
        return redirect("dashboard")

    # Executa a Troca
    t_shift = trade.target_shift
    o_shift = trade.offered_shift

    t_shift.owner = trade.requester
    t_shift.tradable = False
    t_shift.save()

    if o_shift:
        o_shift.owner = request.user
        o_shift.tradable = False
        o_shift.save()

    trade.status = TradeRequest.Status.APPROVED
    trade.save()

    # Cancela outras propostas pendentes para o mesmo plantão
    TradeRequest.objects.filter(
        target_shift=trade.target_shift, status=TradeRequest.Status.PENDING
    ).update(status=TradeRequest.Status.REJECTED)

    # Notifica
    _send_trade_acceptance_email(trade)
    messages.success(request, "Troca realizada!")

    return HttpResponseRedirect(_get_redirect_url(request))


@login_required
def reject_trade_request(request, trade_id):
    trade = get_object_or_404(TradeRequest, id=trade_id)

    if request.user != trade.target_shift.owner:
        return redirect("dashboard")

    trade.status = TradeRequest.Status.REJECTED
    trade.save()
    messages.info(request, "Proposta recusada.")

    return HttpResponseRedirect(_get_redirect_url(request))


def _send_trade_acceptance_email(trade):
    try:
        subject = f"✅ Troca Confirmada!"
        html_content = f"<p>Sua proposta para o dia {trade.target_shift.start_time.strftime('%d/%m')} foi aceita.</p>"
        text = strip_tags(html_content)
        email = EmailMultiAlternatives(
            subject, text, settings.DEFAULT_FROM_EMAIL, [trade.requester.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=True)
    except:
        pass
