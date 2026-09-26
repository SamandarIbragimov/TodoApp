# TodoApp

Django asosidagi jamoaviy Task/ToDo boshqaruv tizimi: loyihalar, a'zolar (owner/admin/member),
tasklar, teglar va izohlar......

## Ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # lokal ishlash uchun DEBUG=True bo'lishi shart
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Ilova: http://localhost:8000/
- Swagger: http://localhost:8000/api/docs/ (yoki `/docs/`)
- ReDoc: http://localhost:8000/api/redoc/
- Admin: http://localhost:8000/admin/

Testlar: `python manage.py test`

## Docker

Lokal (PostgreSQL bilan birga):

```bash
docker compose up --build
docker compose exec web python manage.py createsuperuser
```

Ilova: http://localhost:8000/. Migratsiyalar konteyner ishga tushganda avtomatik qo'llanadi.

Faqat image (masalan, Docker Hub uchun):

```bash
docker build -t <login>/todo-app .
docker run -p 8000:8000 \
  -e SECRET_KEY=... -e ALLOWED_HOSTS=example.com \
  -e CSRF_TRUSTED_ORIGINS=https://example.com \
  -e DATABASE_URL=postgres://user:pass@host:5432/db \
  <login>/todo-app
docker push <login>/todo-app
```

`DATABASE_URL` berilmasa konteyner ichidagi SQLite ishlatiladi va konteyner o'chirilganda ma'lumotlar yo'qoladi.

Render: `render.yaml` (Blueprint) repo ildizida.

## Sahifalar

| URL | Sahifa |
|---|---|
| `/accounts/login/` · `/accounts/register/` | Kirish (username yoki email) · Ro'yxatdan o'tish |
| `/accounts/profile/` | Profil, avatar va teglar |
| `/` | Bosh sahifa: takliflar, statistika, loyihalar, yaqin muddatlar |
| `/tasks/` | Mening vazifalarim: filtrlar, ro'yxat/doska ko'rinishi |
| `/tasks/<id>/` | Vazifa tafsiloti va izohlar |
| `/project/<id>/` | Loyiha: Kanban doska (sudrab status o'zgartirish) va ro'yxat |
| `/project/<id>/members/` | A'zolar, takliflar, rollar, egalikni o'tkazish |

## Frontend tuzilmasi

Sahifalar Django shablonlari, ma'lumotlar esa REST API'dan `fetch` orqali olinadi
(build bosqichi yo'q, oddiy ES modullar).

```
templates/
  layouts/base.html        # <head>, mavzu (yorug'/qorong'i), CSS
  layouts/app.html         # yon panelli ilova karkasi
  layouts/auth.html        # kirish/ro'yxatdan o'tish karkasi
  accounts/ projects/ tasks/   # har bir app o'z sahifalari
static/
  css/app.css              # dizayn tizimi (ranglar tokenlarda, :root va [data-theme=dark])
  js/api.js                # barcha API chaqiruvlari shu yerda
  js/ui.js                 # el(), ikonlar, modal, toast, formatlash
  js/app.js                # yon panel, mavzu, chiqish
  js/components/           # task-view (filtr+ro'yxat+doska), task-form, project-form
  js/pages/                # har bir sahifaning skripti
```

Yangi sahifa qo'shish: app'ning `web_views.py`/`web_urls.py` ga view, `templates/<app>/` ga
`layouts/app.html` dan meros olgan shablon va `static/js/pages/` ga skript.

## Sozlamalar (.env)

| O'zgaruvchi | Tavsif |
|---|---|
| `DEBUG` | `True` / `False` (sukut: `False`) |
| `SECRET_KEY` | `DEBUG=False` bo'lganda majburiy |
| `ALLOWED_HOSTS` | Vergul bilan: `example.com,www.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Vergul bilan: `https://example.com` |
| `DATABASE_URL` | Bo'sh bo'lsa SQLite. PostgreSQL: `postgres://user:pass@host:5432/db` |
| `SECURE_SSL_REDIRECT` | Production: HTTP → HTTPS (sukut: `True`) |
| `SECURE_HSTS_SECONDS` | Production: HSTS muddati (sukut: `3600`) |
| `LOG_LEVEL` | `INFO`, `WARNING`, ... |

## API

| Endpoint | Tavsif |
|---|---|
| `POST /api/accounts/register/` | Ro'yxatdan o'tish (email majburiy, soatiga 10 ta) |
| `POST /api/accounts/login/` | Kirish: username yoki email (5 ta xatodan so'ng 15 daqiqa blok) |
| `POST /api/accounts/logout/` | Chiqish |
| `GET /api/accounts/csrf/` | CSRF token (alohida frontend uchun) |
| `GET/PATCH /api/accounts/profile/` | Profil (avatar ≤ 2 MB) |
| `/api/projects/` | Loyihalar CRUD (faqat a'zo bo'lganlari ko'rinadi) |
| `GET /api/projects/{id}/members/` | A'zolar ro'yxati |
| `PATCH/DELETE /api/projects/{id}/members/{member_id}/` | Rolni o'zgartirish / chiqarish |
| `POST /api/projects/{id}/transfer-ownership/` | Egalikni boshqa a'zoga o'tkazish |
| `GET/POST /api/projects/{id}/invitations/` | Kutilayotgan takliflar / taklif yuborish |
| `DELETE /api/projects/{id}/invitations/{invitation_id}/` | Taklifni bekor qilish |
| `GET /api/invitations/` | Menga kelgan takliflar |
| `POST /api/invitations/{id}/accept/` · `decline/` | Taklifni qabul qilish / rad etish |
| `/api/tasks/` | Tasklar CRUD |
| `GET /api/tasks/stats/` | Statistika (status, priority, muddati o'tgan) |
| `/api/tags/` | Shaxsiy teglar |
| `/api/comments/` | Izohlar (`?task=<id>`) |

Task filtrlari: `status`, `priority`, `project`, `assigned_to`, `tags`, `due_date`,
`due_date_from`, `due_date_to`, `personal=true` (loyihasiz), `mine=true` (menga tayinlangan),
`search`, `ordering` (`due_date`, `priority`, `status`, `created_at`, oldiga `-` qo'yilsa teskari).

## Huquqlar

| Amal | Owner | Admin | Member |
|---|---|---|---|
| Loyihani ko'rish | ✅ | ✅ | ✅ |
| Loyihani tahrirlash | ✅ | ✅ | ❌ |
| Loyihani o'chirish | ✅ | ❌ | ❌ |
| A'zo taklif qilish | ✅ | ✅ | ❌ |
| Egalikni o'tkazish | ✅ | ❌ | ❌ |
| A'zoni chiqarish | ✅ | faqat member'larni | faqat o'zini |
| Rolni o'zgartirish | ✅ | ❌ | ❌ |
| Task yaratish | ✅ | ✅ | ✅ |
| Taskni boshqaga tayinlash | ✅ | ✅ | faqat o'ziga |
| Taskni tahrirlash | ✅ | ✅ | yaratgan yoki tayinlangan bo'lsa |
| Taskni o'chirish | ✅ | ✅ | yaratgan bo'lsa |

Shaxsiy tasklarni (loyihasiz) faqat yaratuvchisi va tayinlangan kishi ko'radi.

Foydalanuvchi o'chirilsa uning loyiha tasklari va izohlari saqlanib qoladi (muallif bo'sh bo'ladi).
Egasi o'chirilgan loyiha eng eski admin'ga (u bo'lmasa eng eski a'zoga) o'tadi.
