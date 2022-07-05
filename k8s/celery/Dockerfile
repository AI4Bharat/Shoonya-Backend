FROM python:3.9.7-slim

ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y gcc
RUN apt-get install -y g++
RUN apt-get install -y build-essential
RUN apt-get install -y wget

USER root
RUN useradd -ms /bin/bash celery
RUN usermod -a -G celery celery
RUN usermod -a -G celery root

WORKDIR /usr/src/app
COPY ./ ./

RUN pip install -r ./backend/requirements.txt --use-deprecated=legacy-resolver

COPY ./k8s/celery/celeryd /etc/init.d/
COPY ./k8s/celery/config/celeryd /etc/default/
RUN ["chmod", "755", "/etc/init.d/celeryd"]
RUN ["chmod", "640", "/etc/default/celeryd"]

RUN ["chmod", "+x", "./k8s/celery/entry.sh"]
ENTRYPOINT ["./k8s/celery/entry.sh"]
