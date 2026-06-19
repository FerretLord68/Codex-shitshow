from django.contrib import admin

from .models import AuditEvent, SupportAccess


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event", "actor", "household", "request_id")
    list_filter = ("event",)
    search_fields = ("event", "request_id", "target_id")
    readonly_fields = [field.name for field in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(SupportAccess)

