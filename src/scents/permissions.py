from rest_framework import permissions

from scents.models import MuseumProfile

# WARN: BR-004
"""
- CapsuleViewSet: aposentar (retired) só curador. Falta.
- QualityCheckViewSet: inspeção so tecnico (IsTechnician não é usado nunca). Falta.
- checkout: aprovar rara/única so curador. Falta.
- ReservationViewSet: criar reserva qualquer perfil. Ok.
- MuseumProfileViewSet: gerenciar perfis so curador (IsCurator). Ok.
"""


def _role(request):
    user = getattr(request, "user", None)
    profile = getattr(user, "museum_profile", None)
    return getattr(profile, "role", None)


class IsCurator(permissions.BasePermission):
    """Permite a escrita apenas para usuários com perfil de curador.

    Leituras seguem liberadas; mutações exigem o papel de curadoria.
    """

    message = "Apenas a curadoria pode executar esta operação."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return _role(request) == MuseumProfile.Role.CURATOR


class IsTechnician(permissions.BasePermission):
    """Permite a escrita apenas para usuários com perfil técnico."""

    message = "Apenas a equipe técnica pode executar esta operação."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return _role(request) == MuseumProfile.Role.TECHNICIAN
