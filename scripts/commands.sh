#!/bin/sh

# O script para se der erro imediatamente caso algum comando falhe

set -e

# Loop para esperar o Postgres acordar

if [ -n "$POSTGRES_HOST" ]; then
  while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    echo "🟡 Waiting for Postgres Database Startup ($POSTGRES_HOST:$POSTGRES_PORT) ..."
    sleep 2
  done
  echo "✅ Postgres Database Started Successfully ($POSTGRES_HOST:$POSTGRES_PORT)"
fi

python manage.py collectstatic --noinput
python manage.py migrate

if [ "$DEBUG" = "True" ]; then
    echo "🔧 Modo Desenvolvimento: Rodando runserver..."
    python manage.py runserver 0.0.0.0:8000
else
    echo "🚀 Modo Produção: Rodando Gunicorn..."
    # Inicia o servidor profissional Gunicorn
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 4
fi