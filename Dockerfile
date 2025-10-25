FROM python:3.11-slim

WORKDIR /app
COPY web.py .
CMD ["python", "web.py"]
