FROM python:alpine3.16

WORKDIR /app
COPY proxy.py .

ENTRYPOINT ["python3", "/app/proxy.py"]