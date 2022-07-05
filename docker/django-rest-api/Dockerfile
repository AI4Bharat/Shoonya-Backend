FROM python:3.9.7-slim

EXPOSE 8000

ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update
RUN apt-get install -y gcc
RUN apt-get install -y g++

WORKDIR /usr/src/app
COPY ./ ./

RUN pip install -r requirements.txt --use-deprecated=legacy-resolver

RUN ["chmod", "+x", "./docker/django-rest-api/entry.sh"]

ENTRYPOINT ["./docker/django-rest-api/entry.sh"]