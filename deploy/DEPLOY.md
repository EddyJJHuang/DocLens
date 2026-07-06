# Deploying DocLens

DocLens runs as a systemd-managed uvicorn service behind nginx, matching the
other apps on the host. Backend on `127.0.0.1:8005`; nginx serves the static
React build and reverse-proxies `/api`. TLS via Let's Encrypt (certbot).

- **App root:** `/var/www/doclens.eddyislearning.ai/`
  - `backend/` — FastAPI app + `.env` (gitignored; holds API keys)
  - `db_knowledge/` — schema knowledge base (ingested into a vector index)
  - `.venv/` — Python 3.12 virtualenv
  - `frontend/dist/` — static React build (built locally with `VITE_API_BASE_URL=/api`)
  - `data/` — runtime indexes + SQLite DB (auto-seeded on first boot)
- **Service:** `doclens-backend.service` (see this dir)
- **nginx site:** `nginx-doclens.conf` (see this dir); certbot adds the 443 block.

## Prerequisites
1. DNS `A` record: `doclens.eddyislearning.ai` → the droplet IP.
2. If the domain is behind a proxy (e.g. Cloudflare), **disable it** during certbot
   so the HTTP-01 challenge reaches the origin; re-enable afterwards.

## Steps (run from a clone of this repo)
```bash
IP=root@<droplet-ip>
APP=/var/www/doclens.eddyislearning.ai

# 1. Build the frontend for production (relative API base so it calls /api on the same host)
( cd frontend && VITE_API_BASE_URL=/api npm ci && npm run build )

# 2. Upload code, knowledge base, frontend build, and .env
ssh $IP "mkdir -p $APP/backend $APP/frontend"
rsync -az --delete --exclude 'venv/' --exclude 'data/' --exclude '__pycache__/' \
      --exclude '.pytest_cache/' --exclude '*.pyc' ./backend/ $IP:$APP/backend/
rsync -az --delete ./db_knowledge/ $IP:$APP/db_knowledge/
rsync -az --delete ./frontend/dist/ $IP:$APP/frontend/dist/
scp .env $IP:$APP/backend/.env   # contains OPENAI/ANTHROPIC/GOOGLE keys

# 3. Python venv + deps
ssh $IP "python3.12 -m venv $APP/.venv && $APP/.venv/bin/pip install -U pip && \
         $APP/.venv/bin/pip install -r $APP/backend/requirements.txt"

# 4. systemd service
scp deploy/doclens-backend.service $IP:/etc/systemd/system/
ssh $IP "systemctl daemon-reload && systemctl enable --now doclens-backend && \
         sleep 3 && curl -s localhost:8005/health"

# 5. nginx site (HTTP) then TLS
scp deploy/nginx-doclens.conf $IP:/etc/nginx/sites-available/doclens.eddyislearning.ai
ssh $IP "ln -sf /etc/nginx/sites-available/doclens.eddyislearning.ai /etc/nginx/sites-enabled/ && \
         nginx -t && systemctl reload nginx"
ssh $IP "certbot --nginx -d doclens.eddyislearning.ai --non-interactive --agree-tos --redirect"
```

## Updating after a code change
Re-run steps 1–2 (and 3 if deps changed), then `ssh $IP systemctl restart doclens-backend`.
