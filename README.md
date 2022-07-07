# Shoonya Backend (Updated with CI-CD and k8s support!)

## Quick Start using `docker-compose` -

### Pre-requisites:

- Docker (Setup Guide for docker on Ubuntu 20.04 can be found [here](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04)!)
- Docker-Compose (Setup Guide for docker-compose can be found [here](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-compose-on-ubuntu-20-04)!)

### Start Docker Containers:

```bash
docker-compose build
docker-compose up
```
> Note: By default, environment variables will be picked from `.env-sample` file. Modify the file, if required.

Access Django's admin panel at `http://localhost:8000/admin`. Superuser credentials for logging in are:
```
username: test@test.com
password: test123
```
