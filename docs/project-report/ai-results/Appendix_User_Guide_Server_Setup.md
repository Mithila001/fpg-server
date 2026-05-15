# Appendix: User Guide — Server Setup

This section provides instructions for setting up and running the House Plan Generator backend server using Docker. The containerized approach automatically handles database creation, seeding, and dependency management.

---

## Prerequisites

Ensure **Docker** and **Docker Compose** are installed on your system:

- Download from [docker.com](https://www.docker.com/)
- Verify installation:
  ```bash
  docker --version
  docker-compose --version
  ```

---

## Quick Start with Docker

### Step 1: Navigate to Project Directory

```bash
cd /path/to/fpg-server
```

### Step 2: Start Both Server and Database

From the project root (where `docker-compose.yml` is located), run:

```bash
docker-compose up --build
```

This command:

- Builds the API container from the `Dockerfile`
- Starts a PostgreSQL 18 database container
- Automatically creates all database tables
- **Seeds the database with default room configurations**
- Starts both services and maintains logs in your terminal

**Expected output:**

```
fpg_server_api | INFO:     Application startup complete
postgres_db_fpg | database system is ready to accept connections
```

### Step 3: Verify Services are Running

In a separate terminal, check that both containers are active:

```bash
docker-compose ps
```

You should see:

- `fpg_server_api` running on port `8000`
- `postgres_db_fpg` running on port `5433`

### Step 4: Access the API

Test the API in your browser or terminal:

```bash
curl http://localhost:8000/docs
```

Visit `http://localhost:8000/docs` to view the **Swagger UI** — an interactive interface for exploring and testing all available endpoints.

### Step 5: Stop the Services

To stop the containers:

```bash
docker-compose down
```

To also remove persistent database data:

```bash
docker-compose down -v
```

---

## What Docker Handles Automatically

The containerized setup eliminates manual configuration:

| Task                     | Status      |
| ------------------------ | ----------- |
| Python environment setup | ✓ Automated |
| Dependency installation  | ✓ Automated |
| Database creation        | ✓ Automated |
| Database seeding         | ✓ Automated |
| API server startup       | ✓ Automated |
| Network configuration    | ✓ Automated |

---

## Accessing the Database

If you need to inspect the database directly:

```bash
docker exec -it postgres_db_fpg psql -U fpg -d fpg_db
```

This opens an interactive PostgreSQL shell inside the running container. Use standard SQL commands to query or manage data.

---

## Troubleshooting

| Issue                             | Solution                                                                                                                   |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| "Port 8000 already in use"        | Stop other services or use `docker-compose down`                                                                           |
| "Cannot connect to Docker daemon" | Ensure Docker Desktop is running                                                                                           |
| "Database connection refused"     | Wait 10–15 seconds for PostgreSQL to fully initialize, then retry                                                          |
| "CORS errors from frontend"       | The server accepts `localhost:5173` by default. If your frontend runs elsewhere, update `allow_origins` in the server code |

---

## Next Steps

1. **Explore the API**: Visit `http://localhost:8000/docs` to browse endpoints and test requests interactively.
2. **Review Server Logs**: Watch terminal output for errors or important information during operation.
3. **Connect Your Frontend**: Point your frontend application to `http://localhost:8000` as the API base URL.
4. **Check Seeded Data**: Use the database connection above to verify default room configurations have been loaded.

---

## Summary

You now have a fully functional backend server with a pre-populated database, all initialized and running in isolated containers. Docker ensures consistent setup across all environments with zero additional configuration needed.
