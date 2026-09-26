from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Project


def _my_project(request, pk):
    return get_object_or_404(Project, pk=pk, memberships__user=request.user)


@login_required
def dashboard(request):
    return render(request, 'projects/dashboard.html')


@login_required
def project_detail(request, pk):
    return render(request, 'projects/detail.html', {'project': _my_project(request, pk)})


@login_required
def project_members(request, pk):
    return render(request, 'projects/members.html', {'project': _my_project(request, pk)})
