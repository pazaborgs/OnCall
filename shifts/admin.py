from django.contrib import admin
from .models import Shift, ShiftType, Group


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "mode", "admin", "invite_token", "created_at")
    search_fields = ("name", "admin__email", "admin__username")
    filter_horizontal = ("members",)
    autocomplete_fields = ("admin",)
    readonly_fields = ("invite_token", "created_at")


@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):

    list_display = ("name", "color", "is_active")
    list_filter = ["is_active"]
    search_fields = ("name",)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "group",
        "shift_type",
        "owner",
        "start_time",
        "duration_display",
        "tradable",
        "is_active",
    )

    list_filter = ("group", "shift_type", "tradable", "start_time", "owner")

    search_fields = ("owner__email", "shift_type__name", "group__name")

    list_editable = ("tradable", "is_active")

    def duration_display(self, obj):
        return obj.get_duration_display()

    duration_display.short_description = "Duração"
