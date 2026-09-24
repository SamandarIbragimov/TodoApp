from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Comment, Tag, Task

User = get_user_model()


class TaskApiTests(APITestCase):
	def setUp(self):
		self.owner = User.objects.create_user(username='owner', password='Strong-password-123')
		self.assignee = User.objects.create_user(username='assignee', password='Strong-password-123')
		self.outsider = User.objects.create_user(username='outsider', password='Strong-password-123')
		self.task = Task.objects.create(
			title='Private task',
			created_by=self.owner,
			assigned_to=self.assignee,
		)

	def test_task_list_only_returns_owned_or_assigned_tasks(self):
		self.client.force_authenticate(self.outsider)

		response = self.client.get(reverse('task-list'))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['count'], 0)

	def test_tag_name_is_trimmed_and_case_insensitive_per_user(self):
		self.client.force_authenticate(self.owner)
		create_url = reverse('tag-list')

		first_response = self.client.post(create_url, {'name': ' Work ', 'color': '#112233'}, format='json')
		duplicate_response = self.client.post(create_url, {'name': 'work', 'color': '#445566'}, format='json')

		self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(first_response.data['name'], 'Work')
		self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_tag_rejects_invalid_color(self):
		self.client.force_authenticate(self.owner)

		response = self.client.post(
			reverse('tag-list'),
			{'name': 'Work', 'color': 'red'},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_only_comment_author_can_edit_or_delete_comment(self):
		comment = Comment.objects.create(task=self.task, user=self.owner, text='Initial')
		self.client.force_authenticate(self.assignee)

		update_response = self.client.patch(
			reverse('comment-detail', args=[comment.pk]),
			{'text': 'Changed'},
			format='json',
		)
		delete_response = self.client.delete(reverse('comment-detail', args=[comment.pk]))

		self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)
		self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)
		self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

	def test_assignee_can_create_comment_on_task(self):
		self.client.force_authenticate(self.assignee)

		response = self.client.post(
			reverse('comment-list'),
			{'task': self.task.pk, 'text': 'I am working on it'},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
