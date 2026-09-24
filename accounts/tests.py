from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.ratelimit import MAX_FAILURES

User = get_user_model()


class AccountsTestCase(APITestCase):
    def setUp(self):
        cache.clear()  # throttle va login cheklovi hisoblagichlari testlar orasida o'tmasin


class RegisterTests(AccountsTestCase):
    url = '/api/accounts/register/'

    def payload(self, **overrides):
        data = {
            'username': 'ali',
            'email': 'Ali@Example.com',
            'password': 'Kuchli-parol-123',
            'password2': 'Kuchli-parol-123',
        }
        return {**data, **overrides}

    def test_register_creates_user_with_profile(self):
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)
        user = User.objects.get(username='ali')
        self.assertEqual(user.email, 'ali@example.com')
        self.assertTrue(user.check_password('Kuchli-parol-123'))
        self.assertIsNotNone(user.profile)

    def test_passwords_must_match(self):
        response = self.client.post(self.url, self.payload(password2='boshqa-parol-123'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data)

    def test_email_required_and_unique(self):
        response = self.client.post(self.url, self.payload(email=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.client.post(self.url, self.payload())
        response = self.client.post(self.url, self.payload(username='vali', email='ALI@example.com'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_is_throttled(self):
        for i in range(10):
            self.client.post(self.url, self.payload(username=f'u{i}', email=f'u{i}@example.com'))
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class LoginTests(AccountsTestCase):
    url = '/api/accounts/login/'

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('ali', 'ali@example.com', 'parol12345')

    def test_login_with_username_or_email(self):
        for login in ('ali', 'ALI@example.com'):
            response = self.client.post(self.url, {'username': login, 'password': 'parol12345'})
            self.assertEqual(response.status_code, status.HTTP_200_OK, login)
            self.assertEqual(response.data['username'], 'ali')
            self.assertEqual(self.client.get('/api/accounts/profile/').status_code, 200)
            self.client.post('/api/accounts/logout/')
            self.assertEqual(self.client.get('/api/accounts/profile/').status_code, 403)

    def test_wrong_password(self):
        response = self.client.post(self.url, {'username': 'ali', 'password': 'xato'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, {'username': 'ali', 'password': 'parol12345'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lockout_after_repeated_failures(self):
        for _ in range(MAX_FAILURES):
            self.client.post(self.url, {'username': 'ali', 'password': 'xato'})
        # Blok vaqtida to'g'ri parol ham qabul qilinmaydi
        response = self.client.post(self.url, {'username': 'ali', 'password': 'parol12345'})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_success_resets_failures(self):
        for _ in range(MAX_FAILURES - 1):
            self.client.post(self.url, {'username': 'ali', 'password': 'xato'})
        self.client.post(self.url, {'username': 'ali', 'password': 'parol12345'})
        response = self.client.post(self.url, {'username': 'ali', 'password': 'xato'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_browsable_login_page_is_rate_limited(self):
        url = '/api-auth/login/'
        for _ in range(MAX_FAILURES):
            self.client.post(url, {'username': 'ali', 'password': 'xato'})
        response = self.client.post(url, {'username': 'ali', 'password': 'parol12345'})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, '15 daqiqadan', status_code=429)

    def test_basic_auth_is_disabled(self):
        import base64

        credentials = base64.b64encode(b'ali:parol12345').decode()
        response = self.client.get(
            '/api/accounts/profile/', HTTP_AUTHORIZATION=f'Basic {credentials}'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_csrf_endpoint(self):
        response = self.client.get('/api/accounts/csrf/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['csrfToken'])


class ProfileTests(AccountsTestCase):
    url = '/api/accounts/profile/'

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('ali', 'ali@example.com', 'parol12345')

    def test_requires_login(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_get_and_update_profile(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(self.url, {'first_name': 'Ali', 'username': 'hacker'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ali')
        self.assertEqual(self.user.username, 'ali')

    def test_email_cannot_be_taken_or_blank(self):
        User.objects.create_user('vali', 'vali@example.com', 'parol12345')
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.patch(self.url, {'email': 'VALI@example.com'}).status_code, 400)
        self.assertEqual(self.client.patch(self.url, {'email': ''}).status_code, 400)


class AuthPagesTests(AccountsTestCase):
    def test_login_and_register_pages_are_public(self):
        for url in ('/accounts/login/', '/accounts/register/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_logged_in_user_is_redirected_from_auth_pages(self):
        user = User.objects.create_user('ali', 'ali@example.com', 'parol12345')
        self.client.force_login(user)
        for url in ('/accounts/login/', '/accounts/register/'):
            self.assertRedirects(self.client.get(url), '/', fetch_redirect_response=False)

    def test_profile_page_requires_login(self):
        response = self.client.get('/accounts/profile/')
        self.assertRedirects(response, '/accounts/login/?next=/accounts/profile/', fetch_redirect_response=False)

    def test_current_user_is_passed_to_js(self):
        user = User.objects.create_user('ali', 'ali@example.com', 'parol12345')
        self.client.force_login(user)
        response = self.client.get('/accounts/profile/')
        self.assertContains(response, 'id="current-user"')
        self.assertEqual(response.context['current_user']['username'], 'ali')
