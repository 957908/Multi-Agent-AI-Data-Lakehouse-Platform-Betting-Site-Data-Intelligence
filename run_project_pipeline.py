# =====================================================================
# Clean Architecture Unified Runner
# =====================================================================
# This script automates dependency verification, database initialization,
# data simulation, ETL execution, ML model training, and index syncing for
# the newly structured Multi-Agent AI Data Lakehouse Platform.
#
# Usage:
#   python run_project_pipeline.py
# =====================================================================

import os
import sys
import subprocess
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
STORAGE_DIR = os.path.join(ROOT_DIR, "storage")
ML_DIR = os.path.join(ROOT_DIR, "ml_models")
RAG_DIR = os.path.join(ROOT_DIR, "rag_service")
AGENTS_DIR = os.path.join(ROOT_DIR, "agents")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def check_dependencies():
    print_header("1. Checking System Dependencies")
    modules = ["pandas", "numpy", "sklearn", "joblib", "sentence_transformers", "faiss", "fastapi", "uvicorn", "playwright", "sqlalchemy", "jose", "passlib"]
    missing = []
    
    for mod in modules:
        try:
            if mod == "sklearn":
                __import__("sklearn")
            elif mod == "jose":
                __import__("jose")
            elif mod == "passlib":
                __import__("passlib")
            else:
                __import__(mod)
            print(f"[OK] {mod} is installed.")
        except ImportError:
            missing.append(mod)
            print(f"[MISSING] {mod} is NOT installed.")
            
    if missing:
        print(f"\nMissing libraries detected: {missing}")
        choice = input("Would you like to install them now? (y/n): ").strip().lower()
        if choice == 'y':
            packages = " ".join([m if m != "sklearn" else "scikit-learn" for m in missing])
            # Map specific library package names
            packages = packages.replace("jose", "python-jose").replace("passlib", "passlib bcrypt")
            subprocess.run(f"pip install {packages}", shell=True)
            subprocess.run("playwright install", shell=True)
        else:
            print("Please install missing dependencies manually and re-run.")
            sys.exit(1)

def run_script(dir_path, script_name, args=None):
    script_path = os.path.join(dir_path, script_name)
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
        
    print(f"\n[RUNNING] {script_name}...")
    result = subprocess.run(cmd, cwd=dir_path)
    if result.returncode != 0:
        print(f"[ERROR] {script_name} failed with exit code {result.returncode}.")
        return False
    print(f"[SUCCESS] {script_name} completed.")
    return True

def run_initialization_pipeline():
    print_header("2. Executing Medallion Data Ingestion & ML Training")
    
    # Step A: Simulate Bronze data
    if not run_script(STORAGE_DIR, "simulate_bronze.py"):
        return False
        
    # Step B: Run Spark/Pandas ETL
    if not run_script(STORAGE_DIR, "spark_etl.py"):
        return False
        
    # Step C: Train ML Models
    if not run_script(ML_DIR, "train_ml_pipelines.py"):
        return False
        
    # Step D: Sync RAG indices
    if not run_script(RAG_DIR, "lakehouse_rag.py", ["--reindex"]):
        return False
        
    print("\nDatabase initialization, data load, ETL, and ML training successfully completed!")
    return True

def start_services():
    print_header("3. Start Platform Services")
    print("Select an option to start:")
    print(" [1] Start FastAPI Backend Service (Port 8085)")
    print(" [2] Start React Frontend Web Dashboard (Port 3000)")
    print(" [3] Run Multi-Agent Orchestration Simulation")
    print(" [4] Run Setup Pipeline again")
    print(" [5] Exit")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        print("\nStarting FastAPI backend server on http://127.0.0.1:8085...")
        print("Press Ctrl+C to stop backend service.")
        try:
            # We must run uvicorn from the ROOT_DIR or add it to python path
            env = os.environ.copy()
            env["PYTHONPATH"] = ROOT_DIR + os.pathsep + env.get("PYTHONPATH", "")
            subprocess.run([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8085", "--reload"], cwd=ROOT_DIR, env=env)
        except KeyboardInterrupt:
            print("\nBackend stopped.")
            
    elif choice == '2':
        print("\nStarting React Frontend Dashboard client on http://localhost:3000...")
        print("Press Ctrl+C to stop client.")
        try:
            if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
                print("[WARNING] node_modules not found. Installing package dependencies first...")
                subprocess.run("npm install", shell=True, cwd=FRONTEND_DIR)
            subprocess.run("npm run dev", shell=True, cwd=FRONTEND_DIR)
        except KeyboardInterrupt:
            print("\nFrontend stopped.")
            
    elif choice == '3':
        print("\nRunning background Multi-Agent Coordination Simulation...")
        run_script(AGENTS_DIR, "lakehouse_agents.py")
        
    elif choice == '4':
        run_initialization_pipeline()
        
    elif choice == '5':
        print("Exiting pipeline runner.")
        sys.exit(0)
    else:
        print("Invalid option. Please try again.")

def main():
    check_dependencies()
    
    # Prompt to run pipeline setup
    print("\nDo you want to initialize the database and run the ETL/ML pipeline now?")
    choice = input("(Required on first-time setup) (y/n): ").strip().lower()
    
    if choice == 'y':
        if not run_initialization_pipeline():
            print("\nPipeline execution encountered errors. Check logs.")
            
    while True:
        start_services()

if __name__ == "__main__":
    main()
