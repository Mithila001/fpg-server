# Backend Environment Integrity

When working within the ./backend directory, always ensure the dedicated Python virtual environment is active. Verify the environment state before executing scripts or installing dependencies to prevent local package conflicts.

# Temporary Dev Files

backend\app\dev folder is a temporary developer personal testing area. It will later be removed and should not be considered as a part of the project.

# Code Quality Checks

After major implementations or when editing Python files, run `ruff check <filename>` to ensure there are no syntax errors and to maintain code quality. Agents should execute this check before committing changes

# Database Info
Look at docker-compose.yml for database connection details.

