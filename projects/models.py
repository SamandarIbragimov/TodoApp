from django.conf import settings
from django.db import models, transaction


class Project(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    # Egasi o'chirilsa loyiha o'chmaydi — signals.py uni keyingi a'zoga o'tkazadi
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_projects',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectMember',
        related_name='projects',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Loyiha'
        verbose_name_plural = 'Loyihalar'

    def __str__(self):
        return self.name

    @classmethod
    @transaction.atomic
    def create_with_owner(cls, owner, **fields):
        """Loyiha yaratib, egasini avtomatik 'owner' roli bilan a'zo qiladi."""
        project = cls.objects.create(owner=owner, **fields)
        ProjectMember.objects.create(project=project, user=owner, role=ProjectMember.Role.OWNER)
        return project

    @transaction.atomic
    def transfer_ownership(self, new_owner_membership):
        """Egalikni boshqa a'zoga o'tkazadi, eski egasi admin bo'lib qoladi."""
        self.memberships.filter(role=ProjectMember.Role.OWNER).update(role=ProjectMember.Role.ADMIN)
        new_owner_membership.role = ProjectMember.Role.OWNER
        new_owner_membership.save(update_fields=['role'])
        self.owner_id = new_owner_membership.user_id
        self.save(update_fields=['owner'])

    def role_of(self, user):
        """Foydalanuvchining shu loyihadagi roli yoki None."""
        return (
            self.memberships.filter(user=user).values_list('role', flat=True).first()
            if user.is_authenticated
            else None
        )


class ProjectMember(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'

    # Loyihani boshqara oladigan rollar
    MANAGER_ROLES = (Role.OWNER, Role.ADMIN)
    # Owner roli faqat loyiha yaratilganda beriladi, qolganlarini tayinlash mumkin
    ASSIGNABLE_ROLES = [(Role.ADMIN.value, Role.ADMIN.label), (Role.MEMBER.value, Role.MEMBER.label)]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['joined_at']
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='unique_project_member'),
        ]
        verbose_name = "Loyiha a'zosi"
        verbose_name_plural = "Loyiha a'zolari"

    def __str__(self):
        return f'{self.user} — {self.project} ({self.role})'


class ProjectInvitation(models.Model):
    """Loyihaga taklif: foydalanuvchi qabul qilgandagina a'zo bo'ladi."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        ACCEPTED = 'accepted', 'Qabul qilindi'
        DECLINED = 'declined', 'Rad etildi'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_invitations',
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_project_invitations',
    )
    role = models.CharField(
        max_length=10, choices=ProjectMember.ASSIGNABLE_ROLES, default=ProjectMember.Role.MEMBER
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'user'],
                condition=models.Q(status='pending'),
                name='unique_pending_invitation',
            ),
        ]
        verbose_name = 'Taklif'
        verbose_name_plural = 'Takliflar'

    def __str__(self):
        return f'{self.user} → {self.project} ({self.status})'
