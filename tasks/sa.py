"""SQLAlchemy orqali tasklar statistikasi.

So'rov SQLAlchemy Core bilan quriladi, lekin Django'ning joriy ulanishi orqali bajariladi:
- SQLite ham, PostgreSQL ham ishlaydi (dialekt Django sozlamasidan olinadi);
- testlarda test bazasi va ochiq tranzaksiya ko'rinadi (alohida engine bunday qilmaydi).
Jadvallarni Django migratsiyalari yaratadi, bu yerda ular faqat o'qiladi.
"""

from django.db import connection
from django.utils import timezone
from sqlalchemy import Column, Date, Integer, MetaData, String, Table, and_, case, func, or_, select
from sqlalchemy.dialects import postgresql, sqlite

metadata = MetaData()

# tasks.models.Task va projects.models.ProjectMember jadvallari (faqat kerakli ustunlar)
task_table = Table(
    'tasks_task',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('status', String(20)),
    Column('priority', String(10)),
    Column('due_date', Date),
    Column('project_id', Integer),
    Column('created_by_id', Integer),
    Column('assigned_to_id', Integer),
)
member_table = Table(
    'projects_projectmember',
    metadata,
    Column('project_id', Integer),
    Column('user_id', Integer),
)

# Django'ning cursor'i %(nom)s ko'rinishidagi parametrlarni ikkala bazada ham qabul qiladi
DIALECTS = {
    'sqlite': sqlite.dialect(paramstyle='pyformat'),
    'postgresql': postgresql.dialect(paramstyle='pyformat'),
}


def _visible_to(user_id):
    """Task.objects.visible_to() ning SQLAlchemy'dagi aynan o'zi."""
    t = task_table
    my_projects = select(member_table.c.project_id).where(member_table.c.user_id == user_id)
    personal = and_(
        t.c.project_id.is_(None),
        or_(t.c.created_by_id == user_id, t.c.assigned_to_id == user_id),
    )
    return or_(personal, t.c.project_id.in_(my_projects))


def _execute(statement):
    compiled = statement.compile(dialect=DIALECTS[connection.vendor])
    with connection.cursor() as cursor:
        cursor.execute(str(compiled), compiled.params)
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, cursor.fetchone(), strict=True))


def task_stats(user_id, project_id=None):
    """Foydalanuvchi ko'ra oladigan tasklar statistikasi (ixtiyoriy: bitta loyiha bo'yicha)."""
    t = task_table
    today = timezone.localdate()
    is_open = t.c.status != 'done'

    def count_if(condition):
        return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)

    statuses = ('todo', 'in_progress', 'done')
    priorities = ('low', 'medium', 'high')
    statement = select(
        func.count().label('total'),
        *(count_if(t.c.status == s).label(f'status_{s}') for s in statuses),
        *(count_if(t.c.priority == p).label(f'priority_{p}') for p in priorities),
        count_if(and_(t.c.due_date < today, is_open)).label('overdue'),
        count_if(and_(t.c.due_date == today, is_open)).label('due_today'),
    ).where(_visible_to(user_id))
    if project_id is not None:
        statement = statement.where(t.c.project_id == project_id)

    row = _execute(statement)
    return {
        'total': row['total'],
        'by_status': {s: row[f'status_{s}'] for s in statuses},
        'by_priority': {p: row[f'priority_{p}'] for p in priorities},
        'overdue': row['overdue'],
        'due_today': row['due_today'],
    }
