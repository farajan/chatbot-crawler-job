FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=120 -r requirements.txt

COPY app/ ./app/

CMD ["python", "-m", "app.main"]
