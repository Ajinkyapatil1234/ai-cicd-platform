FROM python:3.10-slim

RUN apt-get update \
&& apt-get upgrade -y \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir --upgrade wheel setuptools

RUN useradd --create-home --shell /bin/bash appuser

COPY app ./app

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app.main:app"]
