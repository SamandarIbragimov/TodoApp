from django.urls import path

from . import web_views

urlpatterns = [
    path('', web_views.dashboard, name='dashboard'),
    path('project/<int:pk>/', web_views.project_detail, name='project-detail'),
    path('project/<int:pk>/members/', web_views.project_members, name='project-members'),
]
