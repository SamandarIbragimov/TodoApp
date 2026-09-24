from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from projects.models import Project, ProjectMember

from .models import Comment, Tag, Task

User = get_user_model()
Role = ProjectMember.Role
URL = '/api/tasks/'


class TaskTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.com', 'parol12345')
        self.member = User.objects.create_user('member', 'member@example.com', 'parol12345')
        self.member2 = User.objects.create_user('member2', 'member2@example.com', 'parol12345')
        self.outsider = User.objects.create_user('outsider', 'out@example.com', 'parol12345')
        self.project = Project.create_with_owner(self.owner, name='Loyiha')
        for user in (self.member, self.member2):
            ProjectMember.objects.create(project=self.project, user=user, role=Role.MEMBER)

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def task(self, **fields):
        fields.setdefault('title', 'Task')
        fields.setdefault('created_by', self.owner)
        return Task.objects.create(**fields)

    def titles(self, response):
        return sorted(task['title'] for task in response.data['results'])


class VisibilityTests(TaskTestCase):
    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_403_FORBIDDEN)

    def test_member_sees_project_tasks_and_own_personal_tasks(self):
        self.task(title='Loyiha taski', project=self.project)
        self.task(title='Ownerning shaxsiy taski')
        self.task(title='Memberning shaxsiy taski', created_by=self.member)
        response = self.as_user(self.member).get(URL)
        self.assertEqual(self.titles(response), ['Loyiha taski', 'Memberning shaxsiy taski'])

    def test_outsider_sees_nothing(self):
        task = self.task(project=self.project)
        client = self.as_user(self.outsider)
        self.assertEqual(client.get(URL).data['count'], 0)
        self.assertEqual(client.get(f'{URL}{task.pk}/').status_code, status.HTTP_404_NOT_FOUND)


class CreateAndAssignTests(TaskTestCase):
    def test_create_personal_task(self):
        response = self.as_user(self.outsider).post(URL, {'title': 'Kitob o\'qish'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['project'])
        self.assertEqual(response.data['created_by'], self.outsider.pk)
        self.assertEqual(response.data['created_by_username'], 'outsider')
        self.assertTrue(response.data['can_delete'])

    def test_cannot_create_in_foreign_project(self):
        response = self.as_user(self.outsider).post(URL, {'title': 'X', 'project': self.project.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('project', response.data)

    def test_personal_task_only_self_assignable(self):
        client = self.as_user(self.member)
        response = client.post(URL, {'title': 'X', 'assigned_to': self.member2.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = client.post(URL, {'title': 'X', 'assigned_to': self.member.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_owner_assigns_any_member_but_not_outsider(self):
        client = self.as_user(self.owner)
        data = {'title': 'X', 'project': self.project.pk, 'assigned_to': self.member.pk}
        self.assertEqual(client.post(URL, data).status_code, status.HTTP_201_CREATED)
        data['assigned_to'] = self.outsider.pk
        self.assertEqual(client.post(URL, data).status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_assigns_only_self(self):
        client = self.as_user(self.member)
        data = {'title': 'X', 'project': self.project.pk, 'assigned_to': self.member2.pk}
        self.assertEqual(client.post(URL, data).status_code, status.HTTP_400_BAD_REQUEST)
        data['assigned_to'] = self.member.pk
        self.assertEqual(client.post(URL, data).status_code, status.HTTP_201_CREATED)

    def test_project_cannot_be_changed(self):
        task = self.task(project=self.project)
        other = Project.create_with_owner(self.owner, name='Boshqa')
        response = self.as_user(self.owner).patch(f'{URL}{task.pk}/', {'project': other.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EditPermissionTests(TaskTestCase):
    def test_assigned_member_changes_status(self):
        task = self.task(project=self.project, assigned_to=self.member)
        response = self.as_user(self.member).patch(f'{URL}{task.pk}/', {'status': 'in_progress'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')

    def test_unrelated_member_cannot_edit_or_delete(self):
        task = self.task(project=self.project, assigned_to=self.member)
        client = self.as_user(self.member2)
        response = client.get(f'{URL}{task.pk}/')
        self.assertFalse(response.data['can_edit'])
        self.assertEqual(client.patch(f'{URL}{task.pk}/', {'status': 'done'}).status_code, 403)
        self.assertEqual(client.delete(f'{URL}{task.pk}/').status_code, 403)

    def test_assignee_cannot_delete_but_creator_can(self):
        task = self.task(project=self.project, created_by=self.member, assigned_to=self.member2)
        self.assertEqual(self.as_user(self.member2).delete(f'{URL}{task.pk}/').status_code, 403)
        self.assertEqual(self.as_user(self.member).delete(f'{URL}{task.pk}/').status_code, 204)

    def test_owner_edits_and_deletes_any_project_task(self):
        task = self.task(project=self.project, created_by=self.member)
        client = self.as_user(self.owner)
        self.assertEqual(client.patch(f'{URL}{task.pk}/', {'priority': 'high'}).status_code, 200)
        self.assertEqual(client.delete(f'{URL}{task.pk}/').status_code, 204)


class FilterAndStatsTests(TaskTestCase):
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        self.task(title='Kechikkan', due_date=today - timedelta(days=1), priority='high')
        self.task(title='Bugun', due_date=today, assigned_to=self.owner)
        self.task(title='Tayyor', status='done', due_date=today - timedelta(days=3))
        self.task(title='Loyihada', project=self.project, status='in_progress')
        self.client.force_authenticate(self.owner)

    def get(self, **params):
        return self.titles(self.client.get(URL, params))

    def test_filters(self):
        today = timezone.localdate()
        self.assertEqual(self.get(status='done'), ['Tayyor'])
        self.assertEqual(self.get(priority='high'), ['Kechikkan'])
        self.assertEqual(self.get(project=self.project.pk), ['Loyihada'])
        self.assertEqual(self.get(personal='true'), ['Bugun', 'Kechikkan', 'Tayyor'])
        self.assertEqual(self.get(mine='true'), ['Bugun'])
        self.assertEqual(self.get(due_date_from=today.isoformat()), ['Bugun'])
        self.assertEqual(
            self.get(due_date_to=(today - timedelta(days=1)).isoformat()), ['Kechikkan', 'Tayyor']
        )
        self.assertEqual(self.get(search='kech'), ['Kechikkan'])

    def test_stats(self):
        response = self.client.get(f'{URL}stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 4)
        self.assertEqual(
            response.data['by_status'], {'todo': 2, 'in_progress': 1, 'done': 1}
        )
        self.assertEqual(response.data['by_priority']['high'], 1)
        self.assertEqual(response.data['overdue'], 1)
        self.assertEqual(response.data['due_today'], 1)

    def test_stats_not_inflated_by_comments(self):
        task = Task.objects.get(title='Kechikkan')
        for text in ('a', 'b', 'c'):
            Comment.objects.create(task=task, user=self.owner, text=text)
        response = self.client.get(f'{URL}stats/')
        self.assertEqual(response.data['total'], 4)
        self.assertEqual(response.data['by_priority']['high'], 1)

    def test_comments_count(self):
        task = Task.objects.get(title='Bugun')
        Comment.objects.create(task=task, user=self.owner, text='a')
        Comment.objects.create(task=task, user=self.owner, text='b')
        results = self.client.get(URL, {'search': 'Bugun'}).data['results']
        self.assertEqual(results[0]['comments_count'], 2)

    def test_stats_include_project_tasks_created_by_others(self):
        # member hech narsa yaratmagan va unga tayinlanmagan, lekin loyiha taskini ko'radi
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(f'{URL}stats/').data['total'], 1)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(f'{URL}stats/').data['total'], 0)

    def test_stats_match_orm_visibility(self):
        from .sa import task_stats

        for user in (self.owner, self.member, self.outsider):
            visible = Task.objects.visible_to(user)
            stats = task_stats(user.id)
            self.assertEqual(stats['total'], visible.count(), user)
            for status_value, count in stats['by_status'].items():
                self.assertEqual(count, visible.filter(status=status_value).count(), user)

    def test_stats_invalid_project(self):
        response = self.client.get(f'{URL}stats/', {'project': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stats_respects_filters(self):
        response = self.client.get(f'{URL}stats/', {'project': self.project.pk})
        self.assertEqual(response.data['total'], 1)


class TagTests(TaskTestCase):
    def test_tags_are_private_and_unique(self):
        client = self.as_user(self.member)
        self.assertEqual(client.post('/api/tags/', {'name': 'Ish'}).status_code, 201)
        self.assertEqual(client.post('/api/tags/', {'name': 'Ish'}).status_code, 400)
        self.assertEqual(client.post('/api/tags/', {'name': 'X', 'color': 'red'}).status_code, 400)
        self.assertEqual(self.as_user(self.owner).get('/api/tags/').data, [])

    def test_attach_only_own_tags(self):
        mine = Tag.objects.create(name='Mening', user=self.member)
        foreign = Tag.objects.create(name='Begona', user=self.owner)
        task = self.task(project=self.project, assigned_to=self.member)
        client = self.as_user(self.member)
        url = f'{URL}{task.pk}/'
        self.assertEqual(client.patch(url, {'tags': [foreign.pk]}).status_code, 400)
        self.assertEqual(client.patch(url, {'tags': [mine.pk]}).status_code, 200)

    def test_other_members_tags_stay_on_shared_task(self):
        owner_tag = Tag.objects.create(name='Owner tegi', user=self.owner)
        member_tag = Tag.objects.create(name='Member tegi', user=self.member)
        task = self.task(project=self.project, assigned_to=self.member)
        task.tags.add(owner_tag)
        response = self.as_user(self.member).patch(
            f'{URL}{task.pk}/', {'tags': [owner_tag.pk, member_tag.pk]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data['tags']), {owner_tag.pk, member_tag.pk})
        # Boshqa a'zoning tegi ham nomi va rangi bilan keladi
        self.assertEqual(
            {t['name'] for t in response.data['tags_detail']}, {'Owner tegi', 'Member tegi'}
        )


class CommentTests(TaskTestCase):
    def test_project_member_comments_on_project_task(self):
        task = self.task(project=self.project)
        response = self.as_user(self.member2).post('/api/comments/', {'task': task.pk, 'text': 'OK'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        detail = self.client.get(f'{URL}{task.pk}/')
        comment = detail.data['comments'][0]
        self.assertEqual(comment['text'], 'OK')
        self.assertEqual(comment['user'], self.member2.pk)
        self.assertEqual(comment['username'], 'member2')

    def test_comment_length_limit(self):
        task = self.task(project=self.project)
        response = self.as_user(self.owner).post(
            '/api/comments/', {'task': task.pk, 'text': 'x' * 2001}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_cannot_comment(self):
        task = self.task(project=self.project)
        response = self.as_user(self.outsider).post('/api/comments/', {'task': task.pk, 'text': 'X'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_author_edits_but_owner_can_delete(self):
        task = self.task(project=self.project)
        comment = Comment.objects.create(task=task, user=self.member, text='Salom')
        url = f'/api/comments/{comment.pk}/'
        self.assertEqual(self.as_user(self.member2).patch(url, {'text': 'X'}).status_code, 403)
        self.assertEqual(self.as_user(self.member2).delete(url).status_code, 403)
        self.assertEqual(self.as_user(self.owner).patch(url, {'text': 'X'}).status_code, 403)
        self.assertEqual(self.as_user(self.member).patch(url, {'text': 'Yangi'}).status_code, 200)
        self.assertEqual(self.as_user(self.owner).delete(url).status_code, 204)

    def test_comment_cannot_move_to_another_task(self):
        task = self.task(project=self.project)
        other = self.task(project=self.project)
        comment = Comment.objects.create(task=task, user=self.member, text='Salom')
        response = self.as_user(self.member).patch(f'/api/comments/{comment.pk}/', {'task': other.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TaskPagesTests(TaskTestCase):
    def test_task_list_page(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get('/tasks/').status_code, 200)

    def test_task_detail_page_visibility(self):
        task = self.task(title='Loyiha taski', project=self.project)
        self.client.force_login(self.member)
        self.assertContains(self.client.get(f'/tasks/{task.pk}/'), 'Loyiha taski')
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(f'/tasks/{task.pk}/').status_code, 404)
