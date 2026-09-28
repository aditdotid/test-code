FROM python:3.11-slim

# Prevent Python from writing .pyc files & buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (ffmpeg is needed for video remuxing from HLS .m3u8)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first for efficient layer caching
COPY requirements-bot.txt /app/
RUN pip install --no-cache-dir -r requirements-bot.txt

# Copy application files and install local pinterest-dl package
COPY . /app
RUN pip install --no-cache-dir -e .

# Run the Telegram bot
CMD ["python", "bot.py"]
