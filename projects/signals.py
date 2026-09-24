from django.conf import settings
from django.db.models import Case, IntegerField, Value, When
from django.db.models.signals import post_delete
from django.dispatch import receiver

from tasks.models import Task

from .models import Project, ProjectMember


@receiver(post_delete, sender=settings.AUTH_USER_MODEL)
def handle_deleted_user(sender, instance, **kwargs):
    """
    Foydalanuvchi o'chirilgach (FK'lar allaqachon NULL bo'lgan):
    - egasiz qolgan loyihalar eng eski admin'ga, u bo'lmasa eng eski a'zoga o'tadi;
      a'zosi qolmagan loyiha o'chiriladi;
    - hech kimga tegishli bo'lmay qolgan shaxsiy tasklar o'chiriladi.
    """
    admins_first = Case(
        When(role=ProjectMember.Role.ADMIN, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    for project in Project.objects.filter(owner__isnull=True):
        successor = project.memberships.order_by(admins_first, 'joined_at').first()
        if successor is None:
            project.delete()
        else:
            project.transfer_ownership(successor)

    Task.objects.filter(
        project__isnull=True, created_by__isnull=True, assigned_to__isnull=True
    ).delete()
