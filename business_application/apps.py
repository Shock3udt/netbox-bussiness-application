from django.apps import AppConfig


class BusinessApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'business_application'
    verbose_name = 'Business Application'

    def ready(self):
        """
        Import signals when the app is ready to ensure they are registered.
        """
        import business_application.signals