FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Static fayllar image ichida yig'iladi (whitenoise beradi).
# SECRET_KEY faqat shu qadam uchun — ishga tushganda haqiqiy kalit beriladi
RUN SECRET_KEY=build-only-key python manage.py collectstatic --no-input \
    && chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/media \
    && chown -R app:app /app/data /app/media

USER app

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["sh", "-c", "gunicorn todo_project.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-3} --access-logfile -"]
