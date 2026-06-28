import sys
import os

# Append backend directory to search path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Import the FastAPI app instance from backend/main.py
from backend.main import app

if __name__ == "__main__":
    import uvicorn
    # Start the application
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
