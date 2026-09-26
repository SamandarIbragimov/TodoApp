from django.contrib.auth import get_user_model
from rest_framework import serializers

from projects.models import Project, ProjectMember

from .models import Comment, Tag, Task
from .permissions import can_delete_task, can_edit_task, project_roles

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color')

    def validate_name(self, value):
        user = self.context['request'].user
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Teg nomi bo\'sh bo\'lishi mumkin emas.')
        qs = Tag.objects.filter(user=user, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Bu nomli teg sizda allaqachon bor.')
        return value

    def validate_color(self, value):
        if len(value) != 7 or value[0] != '#' or not all(c in '0123456789abcdefABCDEF' for c in value[1:]):
            raise serializers.ValidationError('Rang #RRGGBB formatida bo\'lishi kerak.')
        return value


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default=None)
    text = serializers.CharField(max_length=2000)

    class Meta:
        model = Comment
        fields = ('id', 'task', 'user', 'username', 'text', 'created_at')
        read_only_fields = ('user', 'created_at')

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError('Izoh bo\'sh bo\'lishi mumkin emas.')
        return value

    def validate_task(self, task):
        if self.instance and task != self.instance.task:
            raise serializers.ValidationError("Izohni boshqa taskka ko'chirib bo'lmaydi.")
        user = self.context['request'].user
        if not Task.objects.visible_to(user).filter(pk=task.pk).exists():
            raise serializers.ValidationError('Bu taskka izoh qoldira olmaysiz.')
        return task


class TaskSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True, default=None
    )
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), required=False, allow_null=True,
    )
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True,
    )
    assigned_to_username = serializers.CharField(
        source='assigned_to.username', read_only=True, default=None
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False,
    )
    # Boshqa a'zolarning teglari ham nomi va rangi bilan ko'rinishi uchun
    tags_detail = TagSerializer(source='tags', many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'status', 'priority', 'due_date',
            'project', 'project_name', 'assigned_to', 'assigned_to_username',
            'created_by', 'created_by_username', 'tags', 'tags_detail', 'comments_count',
            'can_edit', 'can_delete', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_by', 'created_at', 'updated_at')

    def get_comments_count(self, task) -> int:
        # Ro'yxatda queryset annotatsiyasidan, yaratish/yangilash javobida esa hisoblanadi
        if hasattr(task, 'comments_count'):
            return task.comments_count
        return task.comments.count()

    def get_can_edit(self, task) -> bool:
        return can_edit_task(self.context['request'], task)

    def get_can_delete(self, task) -> bool:
        return can_delete_task(self.context['request'], task)

    def validate_project(self, project):
        if self.instance and project != self.instance.project:
            raise serializers.ValidationError("Taskni boshqa loyihaga ko'chirib bo'lmaydi.")
        if project and project.pk not in project_roles(self.context['request']):
            raise serializers.ValidationError("Siz bu loyiha a'zosi emassiz.")
        return project

    def validate_tags(self, tags):
        user = self.context['request'].user
        # Boshqa a'zo qo'shgan teglar taskda qolishi mumkin, yangilari esa faqat o'zinikidan
        existing = set(self.instance.tags.values_list('pk', flat=True)) if self.instance else set()
        if any(tag.user_id != user.id and tag.pk not in existing for tag in tags):
            raise serializers.ValidationError("Faqat o'zingizning teglaringizni biriktira olasiz.")
        return tags

    def validate(self, attrs):
        if 'assigned_to' in attrs:
            self._validate_assignee(attrs['assigned_to'], attrs)
        return attrs

    def _validate_assignee(self, assignee, attrs):
        request = self.context['request']
        project = attrs.get('project', self.instance.project if self.instance else None)
        unchanged = self.instance is not None and assignee == self.instance.assigned_to
        if assignee is None or unchanged or assignee == request.user:
            if project and assignee and not project.memberships.filter(user=assignee).exists():
                raise serializers.ValidationError({'assigned_to': "Bu foydalanuvchi loyiha a'zosi emas."})
            return

        if project is None:
            raise serializers.ValidationError(
                {'assigned_to': 'Shaxsiy taskni faqat o\'zingizga tayinlay olasiz.'}
            )
        if project_roles(request).get(project.pk) not in ProjectMember.MANAGER_ROLES:
            raise serializers.ValidationError(
                {'assigned_to': 'Boshqalarga faqat loyiha egasi yoki admini tayinlay oladi.'}
            )
        if not project.memberships.filter(user=assignee).exists():
            raise serializers.ValidationError({'assigned_to': "Bu foydalanuvchi loyiha a'zosi emas."})


class TaskDetailSerializer(TaskSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ('comments',)


class TaskStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_priority = serializers.DictField(child=serializers.IntegerField())
    overdue = serializers.IntegerField()
    due_today = serializers.IntegerField()
