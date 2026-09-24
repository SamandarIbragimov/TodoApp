from django.db.models import Q
from rest_framework import viewsets

from .models import Comment, Tag, Task
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
        queryset = Comment.objects.filter(
            Q(task__created_by=user) | Q(task__assigned_to=user)
        ).select_related('user').distinct()
        if self.action in {'update', 'partial_update', 'destroy'}:
            queryset = queryset.filter(user=user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
