# R2 Setup

Cloudflare R2 is optional. Use it when the lake needs to outgrow local disk or when multiple workers need shared access to the same artifacts.

Set `STORAGE_MODE=r2`, `R2_ENDPOINT`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY`. Run `make r2-check` before starting remote jobs. Do not hardcode credentials.
