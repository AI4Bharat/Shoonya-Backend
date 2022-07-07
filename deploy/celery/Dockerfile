FROM python:3.9.7-slim

ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update
RUN apt-get install -y gcc
RUN apt-get install -y g++
RUN apt-get install -y libpq-dev

USER root
RUN useradd -ms /bin/bash celery
RUN usermod -a -G celery celery
RUN usermod -a -G celery root

WORKDIR /usr/src/app
COPY ./ ./

RUN pip install -r requirements.txt --use-deprecated=legacy-resolver

COPY ./deploy/celery/celeryd /etc/init.d/
COPY ./deploy/celery/config/celeryd /etc/default/

RUN ["chmod", "755", "/etc/init.d/celeryd"]
RUN ["chmod", "640", "/etc/default/celeryd"]
RUN ["chmod", "+x", "./deploy/celery/entry.sh"]

ENTRYPOINT ["./deploy/celery/entry.sh"]