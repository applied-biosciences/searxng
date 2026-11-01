FROM python:3.12-slim
WORKDIR /app
COPY gateway.py .
RUN pip install --no-cache-dir fastapi==0.115.6 httpx==0.28.1 uvicorn==0.34.0
EXPOSE 8080
CMD ["uvicorn", "gateway:app", "--host", "0.0.0.0", "--port", "8080"]
