from django.db.models import Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Comment, Tag, Task
from .sa import task_stats
from .serializers import CommentSerializer, TagSerializer, TaskDetailSerializer, TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """Foydalanuvchi yaratgan yoki unga tayinlangan tasklar."""

    filterset_fields = {
        'status': ['exact'],
        'priority': ['exact'],
        'due_date': ['exact', 'lte', 'gte'],
        'tags': ['exact'],
    }
    search_fields = ('title', 'description')
    ordering_fields = ('due_date', 'priority', 'created_at')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Task.objects.none()
        user = self.request.user
        return (
            Task.objects.filter(Q(created_by=user) | Q(assigned_to=user))
            .select_related('created_by', 'assigned_to')
            .prefetch_related('tags')
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(responses=inline_serializer('TaskStats', {
        name: serializers.IntegerField()
        for name in ('total', 'todo', 'in_progress', 'done', 'high_priority', 'overdue')
    }))
    @action(detail=False)
    def stats(self, request):
        """Tasklar statistikasi (SQLAlchemy orqali hisoblanadi)."""
        return Response(task_stats(request.user.id))


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    search_fields = ('name',)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Tag.objects.none()
        return Tag.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    filterset_fields = ('task',)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()
        user = self.request.user
        return Comment.objects.filter(
            Q(task__created_by=user) | Q(task__assigned_to=user)
        ).select_related('user').distinct()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
