FROM python:3.12-slim

WORKDIR /app

# Install system deps for semgrep and flake8 if needed (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends             git build-essential ca-certificates && rm -rf /var/lib/apt/lists/*

COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script
CMD ["python", "main.py"]
