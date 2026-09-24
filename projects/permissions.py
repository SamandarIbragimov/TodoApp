from rest_framework import permissions

from .models import ProjectMember


class ProjectPermission(permissions.BasePermission):
    """
    A'zolar loyihani ko'radi; owner/admin tahrirlaydi; faqat owner o'chiradi.
    Ro'yxat allaqachon a'zolik bo'yicha filtrlangan (get_queryset).
    """

    def has_object_permission(self, request, view, obj):
        role = obj.role_of(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role is not None
        if request.method == 'DELETE':
            return role == ProjectMember.Role.OWNER
        return role in ProjectMember.MANAGER_ROLES
