from django.urls import path

from . import web_views

urlpatterns = [
    path('login/', web_views.login_page, name='login'),
    path('register/', web_views.register_page, name='register-page'),
    path('profile/', web_views.profile_page, name='profile-page'),
]
