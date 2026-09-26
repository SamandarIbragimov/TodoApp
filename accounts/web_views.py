from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def login_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/login.html')


def register_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/register.html')


@login_required
def profile_page(request):
    return render(request, 'accounts/profile.html')
