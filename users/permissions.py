from __future__ import annotations

from collections.abc import Iterable

from django.contrib.auth.models import Permission

FRONTEND_PERMISSION_ACTIONS = {
    "add": "create",
    "change": "edit",
    "delete": "delete",
    "view": "view",
}


def permission_to_frontend_key(permission: Permission | str) -> str:
    """
    Convert a Django permission string into a frontend-friendly key.
    """
    perm_value = permission.codename if isinstance(permission, Permission) else permission
    if "." in perm_value:
        app_label, codename = perm_value.split(".", 1)
    else:
        app_label = ""
        codename = perm_value

    for prefix, action in FRONTEND_PERMISSION_ACTIONS.items():
        if codename.startswith(f"{prefix}_"):
            return f"{app_label}.{action}" if app_label else action

    return perm_value


def permissions_to_frontend_keys(permissions: Iterable[Permission | str]) -> list[str]:
    seen: set[str] = set()
    keys: list[str] = []

    for permission in permissions:
        key = permission_to_frontend_key(permission)
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)

    return sorted(keys)