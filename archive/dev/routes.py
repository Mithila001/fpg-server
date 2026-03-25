from fastapi import APIRouter

# this router is included only in development; it currently has no
# endpoints but the import must succeed when the app starts.

router = APIRouter()

# add dev-specific diagnostic endpoints here if needed
