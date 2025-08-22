FROM python:3.12-slim

WORKDIR /app

# Chrome va kerakli kutubxonalar
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip gnupg build-essential \
    libglib2.0-0 libnss3 libgconf-2-4 libxi6 libxcursor1 \
    libxcomposite1 libasound2 libxdamage1 libxrandr2 \
    libatk1.0-0 libcups2 libdrm2 libgbm1 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome stable
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb

# Python kutubxonalarini o‘rnatish
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=4"]
