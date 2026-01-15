FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port (not strictly necessary with host networking but good practice)
EXPOSE 8000

RUN chmod +x entrypoint.sh

CMD ["sh", "./entrypoint.sh"]
