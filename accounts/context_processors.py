def current_user(request):
    """Shablonlarda JS uchun joriy foydalanuvchi (json_script orqali uzatiladi)."""
    user = request.user
    if not user.is_authenticated:
        return {'current_user': None}
    profile = getattr(user, 'profile', None)
    avatar = profile.avatar.url if profile and profile.avatar else None
    return {
        'current_user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name(),
            'avatar': avatar,
        }
    }
