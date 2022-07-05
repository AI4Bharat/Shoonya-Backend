# Shoonya Backend (Updated with CI-CD and k8s support!)

## Quick Start

The installation and setup instructions have been tested on the following platforms:

- Docker
- Docker-Compose
- Ubuntu 20.04

If you are using a different operating system, you will have to look at external resources (eg. StackOverflow) to correct any errors.

### Using `docker-compose`

In the base(root) folder of the repo, run following:

```bash
docker-compose build
```

To run the containers:

```bash
docker-compose up
```

Access Django's admin panel at `http://localhost:8000/admin`. Superuser credentials for logging in are:
```
username: test@test.com
password: test123
```
