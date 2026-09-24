"""SQLAlchemy orqali Django'ning SQLite bazasi (db.sqlite3) bilan ishlash.

Jadvallarni Django migratsiyalari yaratadi, SQLAlchemy esa ularni faqat o'qiydi.
"""
from datetime import date

from django.conf import settings
from sqlalchemy import Column, Date, Integer, MetaData, String, Table, case, create_engine, func, or_, select
from sqlalchemy.orm import sessionmaker

engine = create_engine(f"sqlite:///{settings.DATABASES['default']['NAME']}")
Session = sessionmaker(bind=engine)

metadata = MetaData()

# tasks.models.Task jadvali (faqat kerakli ustunlar)
task_table = Table(
    'tasks_task',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('status', String(20)),
    Column('priority', String(10)),
    Column('due_date', Date),
    Column('created_by_id', Integer),
    Column('assigned_to_id', Integer),
)


def task_stats(user_id):
    """Foydalanuvchi yaratgan yoki unga tayinlangan tasklar statistikasi."""
    t = task_table
    not_done = t.c.status != 'done'
    query = (
        select(
            func.count().label('total'),
            func.sum(case((t.c.status == 'todo', 1), else_=0)).label('todo'),
            func.sum(case((t.c.status == 'in_progress', 1), else_=0)).label('in_progress'),
            func.sum(case((t.c.status == 'done', 1), else_=0)).label('done'),
            func.sum(case((t.c.priority == 'high', 1), else_=0)).label('high_priority'),
            func.sum(case(((t.c.due_date < date.today()) & not_done, 1), else_=0)).label('overdue'),
        )
        .where(or_(t.c.created_by_id == user_id, t.c.assigned_to_id == user_id))
    )
    with Session() as session:
        row = session.execute(query).mappings().one()
    return {key: value or 0 for key, value in row.items()}
