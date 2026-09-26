from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


class Tag(models.Model):
    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=7,
        default='#6c757d',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Rang #RRGGBB formatida bo\'lishi kerak.')],
        help_text='HEX rang, masalan #ff0000',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tags',
    )

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_tag'),
        ]
        verbose_name = 'Teg'
        verbose_name_plural = 'Teglar'

    def __str__(self):
        return self.name


class TaskQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Shaxsiy tasklar (yaratgan/tayinlangan) + foydalanuvchi a'zo bo'lgan loyihalar tasklari."""
        from projects.models import Project

        personal = Q(project__isnull=True) & (Q(created_by=user) | Q(assigned_to=user))
        in_my_projects = Q(project__in=Project.objects.filter(memberships__user=user))
        return self.filter(personal | in_my_projects)


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'todo', 'To do'
        IN_PROGRESS = 'in_progress', 'In progress'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True,
        help_text="Bo'sh bo'lsa — shaxsiy task",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_tasks',
        null=True,
        blank=True,
    )
    # Muallif o'chirilsa jamoa taski saqlanib qoladi
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
    )
    tags = models.ManyToManyField(Tag, related_name='tasks', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['due_date']),
        ]
        verbose_name = 'Task'
        verbose_name_plural = 'Tasklar'

    def __str__(self):
        return self.title


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comments',
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Izoh'
        verbose_name_plural = 'Izohlar'

    def __str__(self):
        return f'{self.user} → {self.task}: {self.text[:30]}'
