from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Task


@login_required
def task_list(request):
    return render(request, 'tasks/list.html')


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task.objects.visible_to(request.user), pk=pk)
    return render(request, 'tasks/detail.html', {'task': task})
