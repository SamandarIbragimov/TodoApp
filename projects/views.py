from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from tasks.models import Task

from .models import Project, ProjectInvitation, ProjectMember
from .permissions import ProjectPermission
from .serializers import (
    ChangeRoleSerializer,
    InvitationSerializer,
    InviteSerializer,
    MemberSerializer,
    ProjectSerializer,
    TransferOwnershipSerializer,
)

Role = ProjectMember.Role


class ProjectViewSet(viewsets.ModelViewSet):
    """Foydalanuvchi a'zo bo'lgan loyihalar."""

    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, ProjectPermission]
    search_fields = ('name', 'description')
    ordering_fields = ('name', 'created_at')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Project.objects.none()
        user = self.request.user
        my_role = ProjectMember.objects.filter(project=OuterRef('pk'), user=user).values('role')
        return (
            Project.objects.filter(pk__in=ProjectMember.objects.filter(user=user).values('project'))
            .select_related('owner')
            .annotate(
                members_count=Count('memberships', distinct=True),
                my_role=Subquery(my_role[:1]),
            )
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def _get_member_project(self):
        """
        A'zolar/takliflar endpointlari uchun loyiha. get_object() ishlatilmaydi, chunki
        ProjectPermission DELETE'ni faqat owner'ga ruxsat beradi — bu yerda huquqlar alohida.
        """
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    def _require_role(self, project, roles, message):
        if project.role_of(self.request.user) not in roles:
            raise PermissionDenied(message)

    def _require_manager(self, project):
        self._require_role(
            project, ProjectMember.MANAGER_ROLES,
            "Faqat loyiha egasi yoki admini a'zolarni boshqara oladi.",
        )

    # ----- A'zolar -----

    @extend_schema(responses=MemberSerializer(many=True), summary="Loyiha a'zolari")
    @action(detail=True, methods=['get'], pagination_class=None)
    def members(self, request, pk=None):
        memberships = self._get_member_project().memberships.select_related('user')
        return Response(MemberSerializer(memberships, many=True).data)

    @extend_schema(
        methods=['PATCH'],
        request=ChangeRoleSerializer,
        responses=MemberSerializer,
        summary="A'zo rolini o'zgartirish (faqat owner)",
    )
    @extend_schema(
        methods=['DELETE'],
        responses={204: None},
        summary="A'zoni chiqarish (owner/admin) yoki loyihadan o'zi chiqish",
    )
    @action(detail=True, methods=['patch', 'delete'], url_path=r'members/(?P<member_id>\d+)')
    def member_detail(self, request, pk=None, member_id=None):
        project = self._get_member_project()
        membership = get_object_or_404(project.memberships, pk=member_id)
        my_role = project.role_of(request.user)

        if membership.role == Role.OWNER:
            raise ValidationError(
                "Loyiha egasini o'zgartirib yoki chiqarib bo'lmaydi. "
                "Avval egalikni boshqa a'zoga o'tkazing."
            )

        if request.method == 'PATCH':
            self._require_role(project, [Role.OWNER], "Rollarni faqat loyiha egasi o'zgartira oladi.")
            serializer = ChangeRoleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            membership.role = serializer.validated_data['role']
            membership.save(update_fields=['role'])
            return Response(MemberSerializer(membership).data)

        if membership.user_id != request.user.id:
            self._require_manager(project)
            # Admin boshqa adminni chiqara olmaydi, bu faqat owner huquqi
            if my_role == Role.ADMIN and membership.role == Role.ADMIN:
                raise PermissionDenied('Adminni faqat loyiha egasi chiqara oladi.')
        with transaction.atomic():
            # Chiqarilgan a'zoga shu loyihada tayinlangan tasklar egasiz qoladi
            Task.objects.filter(project=project, assigned_to=membership.user).update(
                assigned_to=None
            )
            membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=TransferOwnershipSerializer,
        responses=MemberSerializer(many=True),
        summary="Egalikni boshqa a'zoga o'tkazish (faqat owner; eski egasi admin bo'ladi)",
    )
    @action(detail=True, methods=['post'], url_path='transfer-ownership')
    def transfer_ownership(self, request, pk=None):
        project = self._get_member_project()
        self._require_role(project, [Role.OWNER], "Egalikni faqat loyiha egasi o'tkaza oladi.")
        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = get_object_or_404(project.memberships, pk=serializer.validated_data['member_id'])
        if membership.user_id == request.user.id:
            raise ValidationError('Siz allaqachon loyiha egasisiz.')
        project.transfer_ownership(membership)
        return Response(MemberSerializer(project.memberships.select_related('user'), many=True).data)

    # ----- Takliflar -----

    @extend_schema(
        methods=['GET'],
        responses=InvitationSerializer(many=True),
        summary='Kutilayotgan takliflar (owner/admin)',
    )
    @extend_schema(
        methods=['POST'],
        request=InviteSerializer,
        responses={201: InvitationSerializer},
        summary='Loyihaga taklif yuborish (owner/admin)',
    )
    @action(detail=True, methods=['get', 'post'], pagination_class=None)
    def invitations(self, request, pk=None):
        project = self._get_member_project()
        self._require_manager(project)
        if request.method == 'GET':
            pending = project.invitations.filter(status=ProjectInvitation.Status.PENDING)
            return Response(
                InvitationSerializer(pending.select_related('user', 'invited_by'), many=True).data
            )

        serializer = InviteSerializer(data=request.data, context={'project': project})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                invitation = ProjectInvitation.objects.create(
                    project=project, invited_by=request.user, **serializer.validated_data
                )
        except IntegrityError as exc:  # parallel so'rov bir xil taklifni yaratib ulgurgan
            raise ValidationError({'user': 'Bu foydalanuvchiga taklif allaqachon yuborilgan.'}) from exc
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={204: None}, summary='Taklifni bekor qilish (owner/admin)')
    @action(
        detail=True,
        methods=['delete'],
        url_path=r'invitations/(?P<invitation_id>\d+)',
    )
    def cancel_invitation(self, request, pk=None, invitation_id=None):
        project = self._get_member_project()
        self._require_manager(project)
        invitation = get_object_or_404(
            project.invitations, pk=invitation_id, status=ProjectInvitation.Status.PENDING
        )
        invitation.status = ProjectInvitation.Status.CANCELLED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Menga kelgan va hali javob berilmagan takliflar."""

    serializer_class = InvitationSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProjectInvitation.objects.none()
        return ProjectInvitation.objects.filter(
            user=self.request.user, status=ProjectInvitation.Status.PENDING
        ).select_related('project', 'user', 'invited_by')

    def _respond(self, new_status):
        invitation = self.get_object()
        with transaction.atomic():
            invitation.status = new_status
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=['status', 'responded_at'])
            if new_status == ProjectInvitation.Status.ACCEPTED:
                ProjectMember.objects.get_or_create(
                    project=invitation.project,
                    user=invitation.user,
                    defaults={'role': invitation.role},
                )
        return Response(InvitationSerializer(invitation).data)

    @extend_schema(request=None, summary="Taklifni qabul qilish — loyiha a'zosi bo'lasiz")
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        return self._respond(ProjectInvitation.Status.ACCEPTED)

    @extend_schema(request=None, summary='Taklifni rad etish')
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        return self._respond(ProjectInvitation.Status.DECLINED)
