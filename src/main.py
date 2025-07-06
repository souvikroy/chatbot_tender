"""
Main entry point for the Tender Information Extraction API
This file serves as the application entry point, separating it from the service logic
"""

import uvicorn
from tender_service import app

if __name__ == "__main__":
    print("[INFO] Starting Tender Information Extraction API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
