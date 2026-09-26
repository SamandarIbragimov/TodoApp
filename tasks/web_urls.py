from django.urls import path

from . import web_views

urlpatterns = [
    path('', web_views.task_list, name='task-list-page'),
    path('<int:pk>/', web_views.task_detail, name='task-detail-page'),
]
