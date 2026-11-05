FROM python:3.11-slim AS local

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  build-essential \
  default-libmysqlclient-dev \
  pkg-config \
  netcat-traditional \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script first
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copy application files
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Set Python path and environment
ENV PYTHONPATH=/app
ENV ENVIRONMENT=development

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Default build is production. The local Compose file explicitly selects `local`.
FROM local AS production
RUN groupadd --gid 10001 researchiq \
  && useradd --uid 10001 --gid 10001 --create-home researchiq \
  && mkdir -p /home/researchiq/.cache/huggingface \
  && chown -R 10001:10001 /app/uploads /home/researchiq
ENV ENVIRONMENT=production PYTHONDONTWRITEBYTECODE=1 HF_HOME=/home/researchiq/.cache/huggingface
USER 10001:10001
