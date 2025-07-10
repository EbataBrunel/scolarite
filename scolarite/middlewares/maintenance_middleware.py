# my_project/middlewares/maintenance_middleware.py

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifie si le mode maintenance est activé
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Redirige vers la page de maintenance si l'URL actuelle n'est pas déjà celle-ci
            if request.path != reverse('settings/maintenance'):
                return redirect('settings/maintenance')
        response = self.get_response(request)
        return response
