from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from tasks.models import Task

from .models import Project, ProjectInvitation, ProjectMember

User = get_user_model()
Role = ProjectMember.Role


class ProjectTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.com', 'parol12345')
        self.admin = User.objects.create_user('admin', 'admin@example.com', 'parol12345')
        self.member = User.objects.create_user('member', 'member@example.com', 'parol12345')
        self.outsider = User.objects.create_user('outsider', 'out@example.com', 'parol12345')
        self.project = Project.create_with_owner(self.owner, name='Diplom ishi')
        ProjectMember.objects.create(project=self.project, user=self.admin, role=Role.ADMIN)
        ProjectMember.objects.create(project=self.project, user=self.member, role=Role.MEMBER)

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def detail_url(self):
        return f'/api/projects/{self.project.pk}/'

    def members_url(self, membership=None):
        base = f'/api/projects/{self.project.pk}/members/'
        return f'{base}{membership.pk}/' if membership else base

    def membership(self, user):
        return self.project.memberships.get(user=user)


class ProjectCrudTests(ProjectTestCase):
    def test_create_makes_creator_owner(self):
        response = self.as_user(self.outsider).post('/api/projects/', {'name': 'Yangi'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['my_role'], Role.OWNER)
        self.assertEqual(response.data['members_count'], 1)
        project = Project.objects.get(pk=response.data['id'])
        self.assertEqual(project.role_of(self.outsider), Role.OWNER)

    def test_list_only_my_projects(self):
        Project.create_with_owner(self.outsider, name='Begona')
        response = self.as_user(self.member).get('/api/projects/')
        self.assertEqual([p['name'] for p in response.data], ['Diplom ishi'])
        self.assertEqual(response.data[0]['my_role'], Role.MEMBER)
        self.assertEqual(response.data[0]['members_count'], 3)

    def test_outsider_cannot_see_project(self):
        response = self.as_user(self.outsider).get(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_permissions(self):
        response = self.as_user(self.member).patch(self.detail_url(), {'name': 'X'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.as_user(self.admin).patch(self.detail_url(), {'name': 'X'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_owner_deletes(self):
        response = self.as_user(self.admin).delete(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.as_user(self.owner).delete(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class MemberManagementTests(ProjectTestCase):
    def test_members_list_visible_to_members(self):
        response = self.as_user(self.member).get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({m['username'] for m in response.data}, {'owner', 'admin', 'member'})

    def test_only_owner_changes_roles(self):
        target = self.membership(self.member)
        response = self.as_user(self.admin).patch(self.members_url(target), {'role': 'admin'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.as_user(self.owner).patch(self.members_url(target), {'role': 'admin'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.project.role_of(self.member), Role.ADMIN)

    def test_owner_membership_is_protected(self):
        target = self.membership(self.owner)
        response = self.as_user(self.owner).delete(self.members_url(target))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.as_user(self.owner).patch(self.members_url(target), {'role': 'member'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_removes_member_but_not_admin(self):
        other_admin = User.objects.create_user('admin2', 'a2@example.com', 'parol12345')
        ProjectMember.objects.create(project=self.project, user=other_admin, role=Role.ADMIN)
        client = self.as_user(self.admin)
        response = client.delete(self.members_url(self.membership(other_admin)))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = client.delete(self.members_url(self.membership(self.member)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_member_can_leave(self):
        response = self.as_user(self.member).delete(self.members_url(self.membership(self.member)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(self.project.role_of(self.member))

    def test_removed_member_is_unassigned_from_tasks(self):
        task = Task.objects.create(
            title='T', project=self.project, created_by=self.owner, assigned_to=self.member
        )
        self.as_user(self.owner).delete(self.members_url(self.membership(self.member)))
        task.refresh_from_db()
        self.assertIsNone(task.assigned_to)


class InvitationTests(ProjectTestCase):
    def invitations_url(self):
        return f'/api/projects/{self.project.pk}/invitations/'

    def invite(self, by, user='outsider', role='member'):
        return self.as_user(by).post(self.invitations_url(), {'user': user, 'role': role})

    def test_invitation_does_not_add_member_until_accepted(self):
        response = self.invite(self.admin, user='OUT@example.com', role='admin')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(self.project.role_of(self.outsider))

        client = self.as_user(self.outsider)
        # Taklif qabul qilinmaguncha loyiha ko'rinmaydi
        self.assertEqual(client.get('/api/projects/').data, [])
        invitations = client.get('/api/invitations/').data
        self.assertEqual([i['project_name'] for i in invitations], ['Diplom ishi'])

        response = client.post(f"/api/invitations/{invitations[0]['id']}/accept/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.project.role_of(self.outsider), Role.ADMIN)
        self.assertEqual(client.get('/api/invitations/').data, [])

    def test_decline(self):
        invitation_id = self.invite(self.owner).data['id']
        response = self.as_user(self.outsider).post(f'/api/invitations/{invitation_id}/decline/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(self.project.role_of(self.outsider))
        # Rad etilgach qayta taklif qilish mumkin
        self.assertEqual(self.invite(self.owner).status_code, status.HTTP_201_CREATED)

    def test_cannot_answer_someone_elses_invitation(self):
        invitation_id = self.invite(self.owner).data['id']
        response = self.as_user(self.member).post(f'/api/invitations/{invitation_id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_cannot_invite_or_list(self):
        self.assertEqual(self.invite(self.member).status_code, status.HTTP_403_FORBIDDEN)
        response = self.as_user(self.member).get(self.invitations_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_validation(self):
        self.assertEqual(self.invite(self.owner, user='nobody').status_code, 400)
        self.assertEqual(self.invite(self.owner, user='member').status_code, 400)
        self.assertEqual(self.invite(self.owner, role='owner').status_code, 400)
        self.invite(self.owner)
        self.assertEqual(self.invite(self.owner).status_code, 400)  # takroriy taklif

    def test_manager_cancels_invitation(self):
        invitation_id = self.invite(self.owner).data['id']
        client = self.as_user(self.admin)
        self.assertEqual(client.get(self.invitations_url()).data[0]['username'], 'outsider')
        response = client.delete(f'{self.invitations_url()}{invitation_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.as_user(self.outsider).get('/api/invitations/').data, [])
        invitation = ProjectInvitation.objects.get(pk=invitation_id)
        self.assertEqual(invitation.status, ProjectInvitation.Status.CANCELLED)


class OwnershipTests(ProjectTestCase):
    def transfer(self, by, target):
        return self.as_user(by).post(
            f'/api/projects/{self.project.pk}/transfer-ownership/',
            {'member_id': self.membership(target).pk},
        )

    def test_owner_transfers_ownership(self):
        response = self.transfer(self.owner, self.member)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.owner, self.member)
        self.assertEqual(self.project.role_of(self.member), Role.OWNER)
        self.assertEqual(self.project.role_of(self.owner), Role.ADMIN)
        self.assertEqual(self.project.memberships.filter(role=Role.OWNER).count(), 1)

    def test_only_owner_transfers(self):
        self.assertEqual(self.transfer(self.admin, self.member).status_code, 403)
        self.assertEqual(self.transfer(self.owner, self.owner).status_code, 400)


class DeletedUserTests(ProjectTestCase):
    def test_owner_deletion_passes_project_to_admin(self):
        task = Task.objects.create(title='T', project=self.project, created_by=self.owner)
        self.owner.delete()
        self.project.refresh_from_db()
        self.assertEqual(self.project.owner, self.admin)
        self.assertEqual(self.project.role_of(self.admin), Role.OWNER)
        task.refresh_from_db()  # jamoa taski saqlanib qoladi
        self.assertIsNone(task.created_by)

    def test_owner_deletion_without_admin_passes_to_member(self):
        self.admin.delete()
        self.owner.delete()
        self.project.refresh_from_db()
        self.assertEqual(self.project.owner, self.member)

    def test_project_without_members_is_deleted(self):
        solo = Project.create_with_owner(self.outsider, name='Yakka')
        self.outsider.delete()
        self.assertFalse(Project.objects.filter(pk=solo.pk).exists())
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_member_deletion_keeps_their_project_tasks(self):
        project_task = Task.objects.create(title='A', project=self.project, created_by=self.member)
        personal = Task.objects.create(title='B', created_by=self.member, assigned_to=self.member)
        self.member.delete()
        self.assertTrue(Task.objects.filter(pk=project_task.pk).exists())
        self.assertFalse(Task.objects.filter(pk=personal.pk).exists())


class ProjectPagesTests(ProjectTestCase):
    def test_pages_require_login(self):
        for url in ('/', f'/project/{self.project.pk}/', f'/project/{self.project.pk}/members/'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertTrue(response['Location'].startswith('/accounts/login/'), url)

    def test_member_sees_project_pages(self):
        self.client.force_login(self.member)
        self.assertContains(self.client.get('/'), 'id="projects"')
        self.assertContains(self.client.get(f'/project/{self.project.pk}/'), 'Diplom ishi')
        self.assertEqual(self.client.get(f'/project/{self.project.pk}/members/').status_code, 200)

    def test_outsider_gets_404(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(f'/project/{self.project.pk}/').status_code, 404)
        self.assertEqual(self.client.get(f'/project/{self.project.pk}/members/').status_code, 404)

    def test_project_name_is_escaped(self):
        self.project.name = '<script>alert(1)</script>'
        self.project.save()
        self.client.force_login(self.owner)
        response = self.client.get(f'/project/{self.project.pk}/')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
