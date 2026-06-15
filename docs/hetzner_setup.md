# Hetzner Setup

Hetzner is an optional shared-deployment target for the control plane: Postgres, Qdrant, backend, frontend, and Nginx. It is not required for local product validation.

Start with:

```bash
docker compose -f docker-compose.hetzner.yml up -d
```
