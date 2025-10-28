# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy files
COPY . .

# Install dependencies using uv
RUN uv pip install --system --no-cache -r requirements.txt

# Expose the Flask port
EXPOSE 5000

RUN chmod +x /app/entrypoint.sh

# Define the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
