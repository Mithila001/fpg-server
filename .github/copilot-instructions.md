# Role: Python Backend Developer Assistant

## Backend Environment Integrity

Before running any commands, ensure the virtual environment is active:

- **Windows:** `.venv\Scripts\activate`
- **Ubuntu/Linux:** `source .venv/bin/activate`

## Project Architecture

- **Dev Files:** The `/app/dev` folder is a temporary testing area. Ignore it when analyzing the core architecture.
- **Dependencies:** Assume all packages in `requirements.txt` are already installed.

## Code Quality Standards

After editing Python files, run the following to ensure syntax integrity:

```bash
# Insert your preferred linting command here, e.g.:
python -m flake8 .
```
