"""
Noto'g'ri parol urinishlarini cheklash (brute-force himoyasi).

Hisob (IP + login) juftligi bo'yicha yuritiladi. Proksi ortida (Railway/Render) REMOTE_ADDR
barcha uchun bir xil bo'lishi mumkin — u holda cheklov amalda login bo'yicha ishlaydi.
Django cache ishlatiladi: bir nechta server jarayonida umumiy cache (Redis) sozlash kerak.
"""

from django.core.cache import cache

MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60
LOCKED_MESSAGE = "Juda ko'p noto'g'ri urinish. 15 daqiqadan so'ng qayta urinib ko'ring."


def _key(request, login):
    ip = request.META.get('REMOTE_ADDR', '')
    return f'login-failures:{ip}:{(login or "").strip().lower()}'


def is_locked(request, login):
    return cache.get(_key(request, login), 0) >= MAX_FAILURES


def register_failure(request, login):
    key = _key(request, login)
    cache.add(key, 0, LOCKOUT_SECONDS)
    try:
        cache.incr(key)
    except ValueError:  # kalit shu orada muddati tugab o'chgan
        cache.set(key, 1, LOCKOUT_SECONDS)


def reset(request, login):
    cache.delete(_key(request, login))
