FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless curl ca-certificates && rm -rf /var/lib/apt/lists/*
ENV PYTHONPATH=/app/pipeline
ENV SPARK_UI_ENABLED=false

COPY pipeline/requirements.txt /app/pipeline/requirements.txt
RUN pip install --no-cache-dir -r /app/pipeline/requirements.txt

COPY pipeline /app/pipeline

CMD ["python", "pipeline/jobs/00_profile_sources.py", "--help"]
