# Use a small official Python image
FROM python:3.11-slim

# Do not buffer Python output (better logs)
ENV PYTHONUNBUFFERED=1

# Create working directory inside the container
WORKDIR /app

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Cloud Run will inject PORT (e.g. 8080)
ENV PORT=8080

# Start FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
