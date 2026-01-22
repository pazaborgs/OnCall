from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("", views.dashboard, name="home"),
    # Grupos
    path("group/create/", views.create_group, name="create_group"),
    path("group/delete/<int:group_id>/", views.delete_group, name="delete_group"),
    # Joins via Code e Reset-Invite
    path("join/submit/", views.join_via_form, name="join_via_form"),
    path("join/<str:token>/", views.join_via_link, name="join_via_link"),
    path(
        "group/<int:group_id>/reset-invite/",
        views.reset_invite_token,
        name="reset_invite",
    ),
    # Edit/Delete/Switch Tradable/ShiftTypes
    path("shift/edit/<int:shift_id>/", views.edit_shift, name="edit_shift"),
    path("shift/delete/<int:shift_id>/", views.delete_shift, name="delete_shift"),
    path(
        "shift/tradable/<int:shift_id>/",
        views.switch_shift_tradable,
        name="switch_shift_tradable",
    ),
    path("manage-types/", views.manage_shift_types, name="manage_shift_types"),
    # Trocas
    path("trade/create/", views.create_trade_request, name="create_trade_request"),
    path(
        "trade/<int:trade_id>/accept/",
        views.accept_trade_request,
        name="accept_trade_request",
    ),
    path(
        "trade/<int:trade_id>/reject/",
        views.reject_trade_request,
        name="reject_trade_request",
    ),
]
