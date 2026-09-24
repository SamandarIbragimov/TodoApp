from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from .models import Project, ProjectInvitation, ProjectMember

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    my_role = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'owner', 'my_role', 'members_count', 'created_at')
        read_only_fields = ('created_at',)

    # Ro'yxatda qiymatlar queryset annotatsiyasidan keladi, yangi yaratilganda esa hisoblanadi
    def get_my_role(self, project) -> str | None:
        if hasattr(project, 'my_role'):
            return project.my_role
        return project.role_of(self.context['request'].user)

    def get_members_count(self, project) -> int:
        if hasattr(project, 'members_count'):
            return project.members_count
        return project.memberships.count()

    def create(self, validated_data):
        return Project.create_with_owner(**validated_data)


class MemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ProjectMember
        fields = ('id', 'user_id', 'username', 'email', 'role', 'joined_at')
        read_only_fields = ('joined_at',)


class InviteSerializer(serializers.Serializer):
    """Username yoki email bo'yicha taklif yuborish."""

    user = serializers.CharField(help_text='Username yoki email')
    role = serializers.ChoiceField(
        choices=ProjectMember.ASSIGNABLE_ROLES, default=ProjectMember.Role.MEMBER
    )

    def validate_user(self, value):
        user = User.objects.filter(Q(username__iexact=value) | Q(email__iexact=value)).first()
        if user is None:
            raise serializers.ValidationError('Bunday foydalanuvchi topilmadi.')
        project = self.context['project']
        if project.memberships.filter(user=user).exists():
            raise serializers.ValidationError("Bu foydalanuvchi allaqachon loyiha a'zosi.")
        if project.invitations.filter(user=user, status=ProjectInvitation.Status.PENDING).exists():
            raise serializers.ValidationError('Bu foydalanuvchiga taklif allaqachon yuborilgan.')
        return user


class InvitationSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    invited_by = serializers.CharField(
        source='invited_by.username', read_only=True, default=None
    )

    class Meta:
        model = ProjectInvitation
        fields = (
            'id', 'project', 'project_name', 'user', 'username', 'invited_by', 'role', 'status',
            'created_at', 'responded_at',
        )
        read_only_fields = fields


class TransferOwnershipSerializer(serializers.Serializer):
    member_id = serializers.IntegerField(help_text="Yangi egasining a'zolik id'si")


class ChangeRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ProjectMember.ASSIGNABLE_ROLES)
