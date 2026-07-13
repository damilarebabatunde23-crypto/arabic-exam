web: python manage.py migrate --noinput && python manage.py ensure_admin && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --log-file -
