from django.conf import settings


def app_settings(request):
    return {
        'MAPS_API_KEY': getattr(settings, 'MAPS_API_KEY', ''),
        'DEBUG': getattr(settings, 'DEBUG', False),
    }

