FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-impress fonts-liberation && rm -rf /var/lib/apt/lists/* && install -d -o 65534 -g 65534 /ipc
COPY worker.py /opt/worker.py
USER 65534:65534
ENV HOME=/tmp
CMD ["python", "/opt/worker.py"]
