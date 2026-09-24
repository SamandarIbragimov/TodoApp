from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Profile

User = get_user_model()


class AccountApiTests(APITestCase):
	def test_register_creates_user_with_hashed_password_and_profile(self):
		response = self.client.post(
			reverse('register'),
			{
				'username': 'new-user',
				'email': 'new@example.com',
				'password': 'Strong-password-123',
				'password2': 'Strong-password-123',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		user = User.objects.get(username='new-user')
		self.assertTrue(user.check_password('Strong-password-123'))
		self.assertTrue(Profile.objects.filter(user=user).exists())

	def test_register_rejects_mismatched_passwords(self):
		response = self.client.post(
			reverse('register'),
			{
				'username': 'new-user',
				'password': 'Strong-password-123',
				'password2': 'different-password-123',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
