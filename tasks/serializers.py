from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Comment, Tag, Task

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color')

    def validate_name(self, value):
        user = self.context['request'].user
        qs = Tag.objects.filter(user=user, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Bu nomli teg sizda allaqachon bor.')
        return value


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'task', 'user', 'text', 'created_at')
        read_only_fields = ('created_at',)

    def validate_task(self, task):
        user = self.context['request'].user
        if task.created_by != user and task.assigned_to != user:
            raise serializers.ValidationError('Bu taskka izoh qoldira olmaysiz.')
        return task


class TaskSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False,
    )

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'status', 'priority', 'due_date',
            'assigned_to', 'created_by', 'tags', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate_tags(self, tags):
        user = self.context['request'].user
        if any(tag.user_id != user.id for tag in tags):
            raise serializers.ValidationError("Faqat o'zingizning teglaringizni biriktira olasiz.")
        return tags


class TaskDetailSerializer(TaskSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ('comments',)
