FROM python:3.11-slim

WORKDIR /app

COPY kopf_controller.py requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt
CMD ["kopf", "run", "/app/kopf_controller.py"]
