from django.contrib import admin
from .models import Notification


# Register your models here.
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "notification_type",
        "created_at",
        "priority",
        "title",
        "on_click",
        "get_receivers",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("reciever_user_id")

    def get_receivers(self, obj):
        return ",".join([r.email for r in obj.reciever_user_id.all()])


admin.site.register(Notification, NotificationAdmin)
