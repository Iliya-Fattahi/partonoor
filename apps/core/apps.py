from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "تنظیمات عمومی"

    def ready(self):
        from .django_compat import apply_context_copy_shim
        from .signals import connect_cache_invalidation_signals, connect_image_variant_signals

        apply_context_copy_shim()
        connect_image_variant_signals()
        connect_cache_invalidation_signals()
