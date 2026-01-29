FROM python:3.14-slim
LABEL maintainer="patsrgsreis@gmail.com"

# Impede que o Python grave arquivos .pyc (lixo) no disco

ENV PYTHONDONTWRITEBYTECODE 1

# Garante que os logs do Python apareçam na hora no terminal

ENV PYTHONUNBUFFERED 1

COPY . /djangoapp
COPY scripts /scripts

WORKDIR /djangoapp

EXPOSE 8000

# --- Dependências do Sistema (Linux) ---

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# --- Dependências do Python e Configuração ---

RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r requirements.txt && \
    mkdir -p /djangoapp/staticfiles && \
    mkdir -p /djangoapp/media && \
    adduser --disabled-password --gecos "" --no-create-home duser && \
    chown -R duser:duser /venv && \
    chown -R duser:duser /djangoapp && \
    chmod -R +x /scripts


# Adiciona scripts e venv ao PATH

ENV PATH="/scripts:/venv/bin:$PATH"

# Muda para o usuário sem privilégios (Segurança)

USER duser

# Inicia o script de entrada

CMD ["commands.sh"]