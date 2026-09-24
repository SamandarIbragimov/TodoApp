from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import views as auth_views
from django.forms.utils import ErrorDict
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ratelimit
from .serializers import LoginSerializer, ProfileSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = 'register'


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class LoginView(APIView):
    """Session login (username yoki email). Ketma-ket 5 ta xato urinishdan so'ng 15 daqiqa blok."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(request=LoginSerializer, responses={200: ProfileSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        if ratelimit.is_locked(request, username):
            return Response({'detail': ratelimit.LOCKED_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        user = authenticate(request, username=username, password=serializer.validated_data['password'])
        if user is None:
            ratelimit.register_failure(request, username)
            return Response(
                {'detail': "Login yoki parol noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST
            )
        ratelimit.reset(request, username)
        login(request, user)
        return Response(ProfileSerializer(user, context={'request': request}).data)


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    """Alohida frontend uchun CSRF token (POST/PATCH/DELETE so'rovlarida X-CSRFToken sarlavhasi)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses=inline_serializer('CsrfToken', {'csrfToken': serializers.CharField()}))
    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class RateLimitedLoginView(auth_views.LoginView):
    """DRF browsable API / Swagger uchun login sahifasi, xato urinishlar cheklovi bilan."""

    template_name = 'rest_framework/login.html'

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username', '')
        if ratelimit.is_locked(request, username):
            form = self.get_form()
            # Validatsiya (ya'ni parol tekshiruvi) ishga tushmasligi uchun xatolar qo'lda beriladi
            form.cleaned_data, form._errors = {}, ErrorDict()
            form.add_error(None, ratelimit.LOCKED_MESSAGE)
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        ratelimit.register_failure(self.request, self.request.POST.get('username', ''))
        return super().form_invalid(form)

    def form_valid(self, form):
        ratelimit.reset(self.request, self.request.POST.get('username', ''))
        return super().form_valid(form)
