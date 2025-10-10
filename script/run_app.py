#!/usr/bin/env python3
"""
Run both FastAPI backend and Streamlit frontend for the Air Quality Q&A Agent

Usage:
    python scripts/run_app.py
    
This will start:
- FastAPI backend on http://localhost:8001
- Streamlit frontend on http://localhost:8501
"""

import subprocess
import time
import sys
import os
import signal
from pathlib import Path

# Add src to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

def run_backend():
    """Run FastAPI backend"""
    print("🚀 Starting FastAPI backend on http://localhost:8001...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--reload", "--port", "8001"],
        cwd=str(ROOT)
    )

def run_frontend():
    """Run Streamlit frontend"""
    print("🚀 Starting Streamlit frontend on http://localhost:8501...")
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/ui/streamlit_pm_query.py"],
        cwd=str(ROOT)
    )

def main():
    """Main function to run both services"""
    print("=" * 60)
    print("🌍 Air Quality Q&A Agent")
    print("=" * 60)
    
    # Start backend
    backend_process = run_backend()
    
    # Wait a bit for backend to start
    print("⏳ Waiting for backend to start...")
    time.sleep(3)
    
    # Start frontend
    frontend_process = run_frontend()
    
    print("\n" + "=" * 60)
    print("✅ Both services are running!")
    print("📍 Backend API: http://localhost:8001")
    print("📍 Frontend UI: http://localhost:8501")
    print("=" * 60)
    print("\nPress Ctrl+C to stop both services...")
    
    try:
        # Wait for processes
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("⚠️ Backend process stopped unexpectedly!")
                break
            if frontend_process.poll() is not None:
                print("⚠️ Frontend process stopped unexpectedly!")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        
        # Terminate processes
        backend_process.terminate()
        frontend_process.terminate()
        
        # Wait for them to stop
        backend_process.wait(timeout=5)
        frontend_process.wait(timeout=5)
        
        print("✅ Services stopped successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Make sure to clean up
        try:
            backend_process.terminate()
            frontend_process.terminate()
        except:
            pass

if __name__ == "__main__":
    main()
