from django.apps import AppConfig

class WarehouseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications.warehouse'

    def ready(self):
        from applications.warehouse import signals
