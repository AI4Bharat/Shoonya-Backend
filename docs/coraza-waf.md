# OWASP Coraza WAF Integration

This document describes how the [OWASP Coraza](https://www.coraza.io/) Web Application
Firewall, running the [OWASP Core Rule Set (CRS)](https://coreruleset.org/), is wired into
the Shoonya deployment, plus the manual server-side steps that are **not** in this repo.

## Why this approach

Coraza has no production-grade native NGINX module (the `coraza-nginx` connector is
experimental and requires compiling `libcoraza` from source). The supported path for an
NGINX-fronted stack is the official
[`coreruleset/coraza-crs-docker`](https://github.com/coreruleset/coraza-crs-docker) image,
which runs Coraza + CRS as a reverse proxy and forwards to a `BACKEND`. We insert it as a
new hop between the existing TLS-terminating NGINX and the `web` (gunicorn) container.

```
Internet ──▶ nginx (TLS termination, certbot, vhost routing — UNCHANGED)
                 │
                 ▼
           coraza-waf  (OWASP Coraza + CRS, DetectionOnly by default)
                 │
                 ▼
             web:8000  (gunicorn / Django)
```

## What changed in this repo

- `docker-compose-prod.yml` / `docker-compose-dev.yml`
  - New `coraza-waf` service (`ghcr.io/coreruleset/coraza-crs:nginx`) listening on `8080`,
    forwarding to `BACKEND=web:8000`.
  - The existing `nginx` service now has `depends_on: [coraza-waf]`.

The NGINX container, certbot, and TLS config are **untouched** — the WAF is transparent to them.

## Manual server-side steps (NOT tracked in git)

`vhosts/` and `config.env` are gitignored and live only on the deployment host.

### 1. Repoint the vhost upstream to the WAF

In each `vhosts/<domain>.conf`, change the upstream from `web` to `coraza-waf`:

```nginx
location / {
    # before: proxy_pass http://web:8000;
    proxy_pass http://coraza-waf:8080;

    # Keep/ensure these so Coraza + CRS see the real client and correct host:
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Leave `/.well-known/acme-challenge/` and any static-file `location` blocks pointing where
they already do — only proxy the dynamic app traffic through the WAF.

### 2. (Optional) Tune the WAF via `config.env`

The compose service reads these with safe defaults, but you can override them in `config.env`:

| Variable                 | Default          | Purpose                                            |
|--------------------------|------------------|----------------------------------------------------|
| `CORAZA_RULE_ENGINE`     | `DetectionOnly`  | `DetectionOnly` = log only, `On` = block, `Off`    |
| `CORAZA_PARANOIA`        | `1`              | CRS paranoia level (1–4); higher = stricter        |
| `CORAZA_ANOMALY_INBOUND` | `5`              | Inbound anomaly score threshold to block           |
| `CORAZA_ANOMALY_OUTBOUND`| `4`              | Outbound anomaly score threshold                   |
| `CORAZA_REQ_BODY_LIMIT`  | `104857600`      | Max inspected request body in bytes (100 MB)       |

## Rollout procedure

1. **Deploy in `DetectionOnly`** (the default). Nothing is blocked; the WAF only logs what it
   *would* have blocked.
2. **Watch the audit log** for a few days of real annotator traffic:
   ```bash
   docker compose -f docker-compose-prod.yml logs -f coraza-waf
   ```
   Look for false positives on legitimate payloads — rich-text annotations, JSON bodies with
   special characters, and large media uploads are the usual suspects.
3. **Add exclusions** for any confirmed false positives (per-path or per-rule-ID CRS
   exclusions) before enforcing.
4. **Enforce**: set `CORAZA_RULE_ENGINE=On` in `config.env` and redeploy.

## Known considerations for Shoonya

- **Large uploads**: `CORAZA_REQ_BODY_LIMIT` is raised to 100 MB. Uploads that go through
  presigned object-storage URLs bypass the WAF path entirely and are unaffected. Confirm which
  upload endpoints route through NGINX before enforcing.
- **`flower` (port 5555) and `web` (port 8000)** are still published directly in the compose
  files and do **not** pass through the WAF. Restrict them at the host firewall / security group
  if they should not be publicly reachable.
- **Log shipping**: to surface blocked/flagged requests alongside app logs, mount a shared log
  volume into the `coraza-waf` service and extend `logstash_prod.conf` with an input for the
  WAF audit log.
