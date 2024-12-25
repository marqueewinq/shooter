FROM python:3.12.7-slim AS base

WORKDIR /work/
RUN apt-get update && apt-get install -y \
    bzip2 \
    gnupg \
    libasound2-dev \
    libatk-bridge2.0-dev \
    libatk1.0-dev \
    libcups2-dev \
    libdbus-1-3 \
    libdbus-glib-1-2 \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libgtk-3-0 \
    libnss3-dev \
    libpango1.0-dev \
    libpci-dev \
    libsm6 \
    libx11-xcb-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxext6 \
    libxkbcommon-dev \
    libxrandr-dev \
    libxrender-dev \
    libxt6 \
    libxtst6 \
    openssl \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and ChromeDriver
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
RUN apt-get update && apt search google-chrome-stable && apt-get install -y "google-chrome-stable=130.0.6723.*" && rm -rf /var/lib/apt/lists/*
RUN wget -N https://storage.googleapis.com/chrome-for-testing-public/130.0.6723.58/linux64/chromedriver-linux64.zip -P /tmp
RUN unzip /tmp/chromedriver-linux64.zip -d /tmp/chromedriver-extract
RUN find /tmp/chromedriver-extract -type f -exec mv {} /usr/local/bin/ \;
RUN chmod +x /usr/local/bin/chromedriver

# Install Firefox & GeckoDriver
RUN wget -O /tmp/geckodriver.tar.gz -N https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz
RUN tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver
RUN wget -O /tmp/firefox.tar.bz2 "https://archive.mozilla.org/pub/firefox/releases/131.0/linux-x86_64/en-US/firefox-131.0.tar.bz2"
RUN tar -xjf /tmp/firefox.tar.bz2 -C /opt/ \
    && ln -s /opt/firefox/firefox /usr/local/bin/firefox

COPY ./pyproject.toml /work/pyproject.toml
RUN pip install --no-cache-dir -e .

COPY shooter /work/shooter/

ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV GECKODRIVER_PATH=/usr/local/bin/geckodriver
ENV PYTHONPATH=/work/shooter/
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
