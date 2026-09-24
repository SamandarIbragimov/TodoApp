from rest_framework import permissions

from projects.models import ProjectMember


def project_roles(request):
    """{project_id: role} — bitta so'rov bilan olinadi va request davomida keshlanadi."""
    if not hasattr(request, '_project_roles'):
        request._project_roles = dict(
            ProjectMember.objects.filter(user=request.user).values_list('project_id', 'role')
        )
    return request._project_roles


def _is_participant(user, task):
    return user.id in (task.created_by_id, task.assigned_to_id)


def can_edit_task(request, task):
    """Shaxsiy task: yaratgan yoki tayinlangan. Loyiha: owner/admin yoki task ishtirokchisi."""
    if task.project_id is None:
        return _is_participant(request.user, task)
    role = project_roles(request).get(task.project_id)
    if role in ProjectMember.MANAGER_ROLES:
        return True
    return role is not None and _is_participant(request.user, task)


def can_delete_task(request, task):
    """Shaxsiy task: faqat yaratgan. Loyiha: owner/admin yoki taskni yaratgan a'zo."""
    if task.project_id is None:
        return task.created_by_id == request.user.id
    role = project_roles(request).get(task.project_id)
    if role in ProjectMember.MANAGER_ROLES:
        return True
    return role is not None and task.created_by_id == request.user.id


class TaskPermission(permissions.BasePermission):
    # Ko'rish huquqi get_queryset() da (Task.objects.visible_to) cheklangan
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'DELETE':
            return can_delete_task(request, obj)
        return can_edit_task(request, obj)


class CommentPermission(permissions.BasePermission):
    """Izohni muallifi tahrirlaydi; o'chirishni muallif yoki loyiha owner/admini qila oladi."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS or obj.user_id == request.user.id:
            return True
        if request.method == 'DELETE' and obj.task.project_id:
            return project_roles(request).get(obj.task.project_id) in ProjectMember.MANAGER_ROLES
        return False
