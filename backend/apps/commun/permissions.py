from rest_framework.permissions import BasePermission


class PermissionParRole(BasePermission):
    """Permission generique basee sur le role. La vue definit
    roles_lecture/roles_ecriture ou roles_par_action (voir projets
    precedents pour la logique complete)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, "role", None)

        roles_par_action = getattr(view, "roles_par_action", None)
        if roles_par_action is not None:
            action = getattr(view, "action", None)
            roles_autorises = roles_par_action.get(action, roles_par_action.get("default"))
            if roles_autorises is None:
                return True
            return role in roles_autorises

        roles_lecture = getattr(view, "roles_lecture", None)
        roles_ecriture = getattr(view, "roles_ecriture", None)
        if roles_lecture is None and roles_ecriture is None:
            return True

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True if roles_lecture is None else role in roles_lecture
        return True if roles_ecriture is None else role in roles_ecriture
