FROM python:3.12-slim

# ffmpeg — video + audio merge-ku kandippa thevai
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py .
COPY templates/ templates/

# downloads folder — volume-maari mount pannalam
RUN mkdir -p /app/downloads
VOLUME /app/downloads

EXPOSE 5000

# gunicorn: 2 workers, 300s timeout (fetch slow-a irukkalam, so long timeout)
CMD ["gunicorn", "-w", "2", "-t", "300", "-b", "0.0.0.0:5000", "app:app"]
