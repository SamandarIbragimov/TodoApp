from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .filters import TaskFilter
from .pagination import TaskPagination
from .models import Comment, Tag, Task
from .permissions import CommentPermission, TaskPermission
from .serializers import (
    CommentSerializer,
    TagSerializer,
    TaskDetailSerializer,
    TaskSerializer,
    TaskStatsSerializer,
)


class TaskViewSet(viewsets.ModelViewSet):
    """Shaxsiy tasklar va foydalanuvchi a'zo bo'lgan loyihalar tasklari."""

    permission_classes = [permissions.IsAuthenticated, TaskPermission]
    pagination_class = TaskPagination
    filterset_class = TaskFilter
    search_fields = ('title', 'description')
    ordering_fields = ('due_date', 'priority', 'status', 'created_at')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Task.objects.none()
        qs = (
            Task.objects.visible_to(self.request.user)
            .select_related('created_by', 'assigned_to', 'project')
            .prefetch_related('tags')
        )
        # stats guruhlab sanaydi — izohlar JOIN'i u yerda sonlarni buzadi
        if self.action != 'stats':
            qs = qs.annotate(comments_count=Count('comments', distinct=True))
        if self.action == 'retrieve':
            qs = qs.prefetch_related(Prefetch('comments', Comment.objects.select_related('user')))
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(responses=TaskStatsSerializer, summary='Tasklar statistikasi (dashboard)')
    @action(detail=False, methods=['get'], pagination_class=None)
    def stats(self, request):
        """Filtrlarni hisobga olgan holda tasklar soni: status, priority, muddati o'tganlar."""
        qs = self.filter_queryset(self.get_queryset()).order_by()
        today = timezone.localdate()
        open_tasks = qs.exclude(status=Task.Status.DONE)

        def counts(field, choices):
            data = dict.fromkeys(choices.values, 0)
            data.update(qs.values_list(field).annotate(n=Count('id')))
            return data

        return Response({
            'total': qs.count(),
            'by_status': counts('status', Task.Status),
            'by_priority': counts('priority', Task.Priority),
            'overdue': open_tasks.filter(due_date__lt=today).count(),
            'due_today': open_tasks.filter(due_date=today).count(),
        })


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    search_fields = ('name',)
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Tag.objects.none()
        return Tag.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save(user=self.request.user)
        except IntegrityError as exc:  # parallel so'rov bir xil tegni yaratib ulgurgan
            raise ValidationError({'name': 'Bu nomli teg sizda allaqachon bor.'}) from exc


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, CommentPermission]
    filterset_fields = ('task',)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()
        visible_tasks = Task.objects.visible_to(self.request.user)
        return Comment.objects.filter(task__in=visible_tasks).select_related('user', 'task')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
