from django.urls import path

from .views import CsrfView, LoginView, LogoutView, ProfileView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='api-login'),
    path('logout/', LogoutView.as_view(), name='api-logout'),
    path('csrf/', CsrfView.as_view(), name='csrf'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
