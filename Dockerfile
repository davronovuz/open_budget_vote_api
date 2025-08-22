FROM python:3.12-slim

WORKDIR /app

# Kerakli kutubxonalarni o'rnatish (Chromium uchun zarur, libgconf-2-4 olib tashlandi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip gnupg build-essential \
    libglib2.0-0 libnss3 libxi6 libxcursor1 \
    libxcomposite1 libasound2 libxdamage1 libxrandr2 \
    libatk1.0-0 libcups2 libdrm2 libgbm1 libxkbcommon0 libxext6 libxfixes3 libx11-6 libxrender1 libxtst6 \
    fonts-liberation libappindicator3-1 libnspr4 libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libatk-bridge2.0-0 libgtk-3-0 \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Python kutubxonalari
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=4"]