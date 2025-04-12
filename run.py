import os
import subprocess
import threading
import time
import webbrowser
import signal
import sys
from database import init_db

def run_streamlit():
    """Run the Streamlit app"""
    subprocess.run(["streamlit", "run", "app.py", "--server.port", "5000", "--server.address", "0.0.0.0"])

def run_api():
    """Run the FastAPI server"""
    subprocess.run(["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"])

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    print("\nShutting down services...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize database
    print("Initializing database...")
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        print("Application will continue but database features might not work properly")
    
    # Start the API server in a separate thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    print("Starting services...")
    print("API server running at http://localhost:8000")
    print("Web interface running at http://localhost:5000")
    
    # Run the Streamlit app in the main thread
    run_streamlit()
