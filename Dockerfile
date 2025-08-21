
FROM python:3.12-slim


WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc curl wget netcat-openbsd \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=4"]
