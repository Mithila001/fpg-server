# OCI Cloud Deployment Guide — FPG Server
> Academic Presentation Setup · Stability-first · Docker on OCI VM

---

## What Changed in the Codebase

| File | Change |
|---|---|
| `app/core/config.py` | Added `OPTUNA_TRIAL_COUNT`, `OPTUNA_TRIAL_TIMEOUT`, `ENABLE_PLOT_SAVING` as env-driven settings |
| `app/core/fpg_rooms/config_fpg.py` | Wires those settings; adds `ENABLE_PLOT_SAVING` constant used project-wide |
| `app/util/algorithm_manager/fpg_procesors/union_floor_plan.py` | Guards `_plot_union_floor_plan` with `ENABLE_PLOT_SAVING` |
| `app/services/algorithm_manager_v2.py` | Guards `plot_refine_floor_plan`, `plot_final_solver_result`, and `extend_floor_plan_walls` filename |
| `app/algorithms/fpg_rooms/fpg_score/score_critical/inward_pocket.py` | Guards `_debug_steps_plotter` |
| `app/main.py` | CORS origins now read from `CORS_ORIGINS` env var |
| `docker-compose.yml` | Named DB volume, healthcheck, port 5432 exposed, all new env vars added |
| `Dockerfile` | Added `--timeout-keep-alive 120` and `--timeout-graceful-shutdown 10` to uvicorn |
| `.env.example` | Updated with all new variables and explanations |

---

## Part 1 — Provision OCI VM

### 1.1 Create the Instance

1. Log in to **cloud.oracle.com** → **Compute → Instances → Create Instance**
2. **Shape**: `VM.Standard.E4.Flex` — give it **2 OCPUs + 8 GB RAM** (free-tier eligible shapes: `VM.Standard.A1.Flex` up to 4 OCPUs / 24 GB RAM on Always-Free)
3. **Image**: Oracle Linux 8 **or Ubuntu 22.04** (Ubuntu is easier for Docker)
4. **SSH Key**: Upload your public key (you'll SSH in later)
5. Note the **Public IP** after it provisions

### 1.2 Open Firewall (Security List / NSG)

In OCI Console → VCN → Security Lists → Default Security List:

| Direction | Protocol | Source/Dest | Port | Purpose |
|---|---|---|---|---|
| Ingress | TCP | `0.0.0.0/0` | **22** | SSH |
| Ingress | TCP | **Your laptop IP only** | **8000** | FastAPI (or `0.0.0.0/0` for demo) |
| Ingress | TCP | **Your laptop IP only** | **5432** | PostgreSQL DB client |

> [!TIP]
> Restrict ports 8000 and 5432 to your laptop's IP for the presentation. You can find your IP at [whatismyip.com](https://whatismyip.com).

---

## Part 2 — Prepare the VM

SSH into the instance:

```bash
ssh ubuntu@<OCI_PUBLIC_IP>
```

### 2.1 Install Docker & Docker Compose

```bash
# Update packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # or log out and back in

# Verify
docker --version
docker compose version
```

### 2.2 OS Firewall (iptables / ufw)

Ubuntu 22.04 ships with `ufw`:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 5432/tcp
sudo ufw enable
sudo ufw status
```

> [!IMPORTANT]
> OCI has TWO firewall layers: the VCN Security List (Step 1.2) **and** the OS-level firewall (above). Both must allow a port for traffic to reach your app.

---

## Part 3 — Deploy the Server

### 3.1 Copy the Project to OCI

From your **Windows machine**:

```powershell
# Using rsync via WSL or Git Bash:
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude 'postgres_data' \
  "f:/OnGoinProject/House Plane Generator Projects/fpg-server/" \
  ubuntu@<OCI_PUBLIC_IP>:~/fpg-server/

# Alternatively: push to GitHub and git clone on the VM
```

### 3.2 Configure Environment

On the VM:

```bash
cd ~/fpg-server
cp .env.example .env
nano .env
```

Set these values for the cloud deployment:

```env
DB_URL=postgresql://fpg:fpg@db:5432/fpg_db

FPG_GENERATION_API_TIMEOUT=180
JOB_REGISTRY_CLEANUP_DELAY=60

OPTUNA_TRIAL_COUNT=20
OPTUNA_TRIAL_TIMEOUT=170

# CRITICAL: Turn off all matplotlib disk saves
ENABLE_PLOT_SAVING=false

# Add your laptop's IP if it differs from localhost
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> [!NOTE]
> The `.env` file is **not** used by Docker Compose (those are set inline in `docker-compose.yml`). The `.env` is only for local dev runs (`uvicorn` directly). For Docker, edit the `environment:` section in `docker-compose.yml`.

### 3.3 Start the Stack

```bash
cd ~/fpg-server
docker compose up -d --build
```

Check logs:

```bash
docker compose logs -f api    # FastAPI server logs
docker compose logs -f db     # Postgres logs
```

Verify it's running:

```bash
curl http://localhost:8000/docs   # Should return HTML
# From your laptop:
curl http://<OCI_PUBLIC_IP>:8000/docs
```

---

## Part 4 — SSE / Streaming Stability

Your SSE stream goes: `Browser → OCI → FastAPI (uvicorn)`. Here's what each layer does to keep it alive:

| Layer | Setting | Why |
|---|---|---|
| Uvicorn | `--timeout-keep-alive 120` | Keeps TCP alive 120 s between SSE events |
| App | `yield ": keepalive\n\n"` every 10 s | Prevents proxies/OCI LB from closing idle streams |
| Docker | `restart: always` | Auto-restarts if the container crashes |
| OCI Security List | Port 8000 open | Required for the TCP connection |

> [!NOTE]
> You are connecting **directly** to the VM on port 8000 (no load balancer in between), so there is no OCI LB idle-timeout to worry about. The main risk is the OS TCP keepalive — already covered by uvicorn's `--timeout-keep-alive`.

---

## Part 5 — Frontend (React) Configuration

You do **not** need to change your React code if you just change the base URL. Find where your frontend sets the API base URL and update it:

```js
// Before (local dev)
const API_BASE = "http://localhost:8000";

// After (cloud presentation)
const API_BASE = "http://<OCI_PUBLIC_IP>:8000";
```

If you use a `.env` in the frontend (Vite project):

```env
VITE_API_BASE_URL=http://<OCI_PUBLIC_IP>:8000
```

Then restart Vite (`npm run dev`). The server already allows `localhost:5173` via CORS, so no other changes needed.

---

## Part 6 — Database Access During Presentation

The Postgres DB is exposed on **port 5432** of the OCI public IP.

**DBeaver / TablePlus / psql connection settings:**

| Field | Value |
|---|---|
| Host | `<OCI_PUBLIC_IP>` |
| Port | `5432` |
| Database | `fpg_db` |
| User | `fpg` |
| Password | `fpg` |

> [!WARNING]
> Make sure port 5432 is open in both the OCI Security List AND `ufw` (done in Step 2.2).

---

## Part 7 — Tuning Without Redeployment

Edit `docker-compose.yml` on the VM and restart only the API container:

```bash
# Example: increase Optuna trials to 30
nano ~/fpg-server/docker-compose.yml
# Change: - OPTUNA_TRIAL_COUNT=30

docker compose restart api
```

No rebuild needed — environment variables are injected at start time.

---

## Part 8 — Ghost Runner Prevention

The app already has safeguards:

1. **Watchdog timeout thread** (`_watchdog_timeout` in `job_lifecycle.py`) — kills the subprocess after `FPG_GENERATION_API_TIMEOUT` seconds even if it never finishes.
2. **`daemon=True` on worker processes** — if the main uvicorn process dies, all child generation processes die with it automatically.
3. **`process.terminate()` + `process.kill()`** on cancel/timeout — hard-kills the subprocess.
4. **`restart: always`** on Docker — if the container itself crashes and restarts, there are no orphaned processes left from before (Docker kills the old container entirely).

> [!TIP]
> If you ever suspect a ghost job is running, you can check inside the container:
> ```bash
> docker exec fpg_server_api ps aux
> ```
> Any `python` worker processes will show up there. Kill with `docker compose restart api` if needed.

---

## Part 9 — Useful Commands (Quick Reference)

```bash
# Start everything
docker compose up -d --build

# View live logs
docker compose logs -f

# Restart only the API (after config change)
docker compose restart api

# Stop everything
docker compose down

# Stop and WIPE database (fresh start)
docker compose down -v

# Connect to API container shell
docker exec -it fpg_server_api bash

# Check running processes inside container
docker exec fpg_server_api ps aux

# Check disk usage (plots are off, but verify)
docker exec fpg_server_api du -sh /app/test/outputs/ 2>/dev/null || echo "No outputs dir"
```

---

## Part 10 — Pre-Presentation Checklist

- [ ] OCI VM is running and SSH accessible
- [ ] VCN Security List: ports 22, 8000, 5432 open for your IP
- [ ] `ufw` on VM: same ports allowed  
- [ ] `docker compose up -d --build` ran successfully
- [ ] `curl http://<OCI_PUBLIC_IP>:8000/docs` returns page
- [ ] DB client (DBeaver) connects to `<OCI_PUBLIC_IP>:5432`
- [ ] Frontend `.env` / base URL points to OCI IP
- [ ] `ENABLE_PLOT_SAVING=false` in docker-compose.yml environment
- [ ] `CORS_ORIGINS` includes your laptop IP if needed
- [ ] Test a full generation end-to-end from your laptop before the presentation
