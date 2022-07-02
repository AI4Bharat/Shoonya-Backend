FROM python:3.9.7-slim

RUN apt-get update && apt-get install gcc -y

COPY . /app
WORKDIR /app

RUN python3 -m venv /opt/venv

RUN /opt/venv/bin/pip install -r requirements.txt --use-deprecated=legacy-resolver && \
    chmod +x entrypoint.sh && chmod +x collectstatic.sh && sh collectstatic.sh

ENTRYPOINT ["/app/entrypoint.sh"]