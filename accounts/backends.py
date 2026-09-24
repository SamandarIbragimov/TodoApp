from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """Login maydoniga username yoki email yozish mumkin."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or '@' not in username:
            return super().authenticate(request, username=username, password=password, **kwargs)
        user = User.objects.filter(email__iexact=username).order_by('id').first()
        if user is None:
            # Foydalanuvchi bor-yo'qligini javob vaqtidan bilib bo'lmasligi uchun
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
