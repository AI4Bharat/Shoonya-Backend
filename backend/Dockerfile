FROM python:3.9.7-slim

RUN apt-get update && apt-get install gcc -y

COPY . /app
WORKDIR /app

RUN python3 -m venv /opt/venv

RUN /opt/venv/bin/pip install pip --upgrade && \
    /opt/venv/bin/pip install -r requirements.txt && \
    chmod +x entrypoint.sh

RUN /opt/venv/bin/python manage.py collectstatic

CMD ["/app/entrypoint.sh"]