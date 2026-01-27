#!/bin/sh

# O script para se der erro (segurança)
set -e

# Loop para esperar o Postgres acordar
# Ele usa o host 'psql' e a porta '5432' que definimos no .env
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  echo "🟡 Waiting for Postgres Database Startup ($POSTGRES_HOST:$POSTGRES_PORT) ..."
  sleep 2
done

echo "✅ Postgres Database Started Successfully ($POSTGRES_HOST:$POSTGRES_PORT)"

# Roda as migrações e o servidor
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py runserver 0.0.0.0:8000