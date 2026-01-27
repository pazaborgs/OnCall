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

# --- FASE 1: Dependências do Sistema (Linux) ---
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# --- FASE 2: Dependências do Python e Configuração ---
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r requirements.txt && \
    adduser --disabled-password --no-create-home duser && \
    mkdir -p /data/web/static && \
    mkdir -p /data/web/media && \
    chown -R duser:duser /venv && \
    chown -R duser:duser /data/web/static && \
    chown -R duser:duser /data/web/media && \
    chmod -R 755 /data/web/static && \
    chmod -R 755 /data/web/media && \
    chmod -R +x /scripts

# Adiciona scripts e venv ao PATH para não precisar digitar o caminho completo
ENV PATH="/scripts:/venv/bin:$PATH"

# Muda para o usuário sem privilégios (Segurança)
USER duser

# Inicia o script de entrada
CMD ["commands.sh"]