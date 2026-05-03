from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission

from .models import Club


def get_managed_clubs(user: Any | None):
    if not user or not user.is_authenticated:
        return Club.objects.none()
    if user.is_staff or user.is_superuser:
        return Club.objects.filter(is_active=True)
    return user.clubs_led.filter(is_active=True)


def has_club_management_scope(user: Any | None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return False
    return user.roles.filter(slug__iexact='club-president').exists() or user.clubs_led.filter(is_active=True).exists()


def can_manage_club(user: Any | None, club: Club | str | None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if club is None:
        return False

    club_id = getattr(club, 'pk', club)
    return get_managed_clubs(user).filter(pk=club_id).exists()


class IsManagedClubObject(BasePermission):
    message = 'You do not have permission to manage this club.'

    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        return get_managed_clubs(request.user).exists()

    def has_object_permission(self, request, view, obj):  # type: ignore[override]
        return can_manage_club(request.user, obj)