from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import json
import subprocess
import psutil
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
import glob

app = FastAPI(title="Free Range Chess RL Training Server")

TRAINING_STATE_FILE = "training_state.json"
LOGS_DIR = "./logs"
MODELS_DIR = "./models"

training_process: Optional[subprocess.Popen] = None
training_state: Dict[str, Any] = {
    "status": "idle",
    "current_run": None,
    "start_time": None,
    "pid": None,
}

class TrainingConfig(BaseModel):
    timesteps: int = 1_000_000
    n_envs: int = 8
    opponent: str = "random"
    learning_rate: float = 3e-4
    batch_size: int = 256
    n_steps: int = 2048

def load_state():
    global training_state
    if os.path.exists(TRAINING_STATE_FILE):
        try:
            with open(TRAINING_STATE_FILE, 'r') as f:
                training_state = json.load(f)
                if training_state.get("pid") and not psutil.pid_exists(training_state["pid"]):
                    training_state["status"] = "idle"
                    training_state["pid"] = None
        except Exception as e:
            print(f"Error loading state: {e}")

def save_state():
    try:
        with open(TRAINING_STATE_FILE, 'w') as f:
            json.dump(training_state, f, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}")

@app.on_event("startup")
async def startup_event():
    load_state()
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

@app.get("/")
async def read_root():
    return FileResponse("web/index.html")

@app.get("/api/status")
async def get_status():
    global training_state, training_process
    
    if training_state.get("pid"):
        if not psutil.pid_exists(training_state["pid"]):
            training_state["status"] = "completed"
            training_state["pid"] = None
            training_process = None
            save_state()
    
    return training_state

@app.post("/api/train/start")
async def start_training(config: TrainingConfig, background_tasks: BackgroundTasks):
    global training_state, training_process
    
    if training_state["status"] == "running":
        raise HTTPException(status_code=400, detail="Training already running")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"ppo_chess_{config.opponent}_{timestamp}"
    
    cmd = [
        "python", "train_ppo.py",
        "--mode", "train",
        "--timesteps", str(config.timesteps),
        "--n-envs", str(config.n_envs),
        "--opponent", config.opponent,
    ]
    
    log_file = os.path.join(LOGS_DIR, f"{run_name}.log")
    
    try:
        with open(log_file, 'w') as f:
            training_process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
        
        training_state = {
            "status": "running",
            "current_run": run_name,
            "start_time": timestamp,
            "pid": training_process.pid,
            "config": config.dict(),
            "log_file": log_file,
        }
        save_state()
        
        return {"message": "Training started", "run_name": run_name, "pid": training_process.pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")

@app.post("/api/train/stop")
async def stop_training():
    global training_state, training_process
    
    if training_state["status"] != "running":
        raise HTTPException(status_code=400, detail="No training running")
    
    try:
        if training_process:
            training_process.terminate()
            training_process.wait(timeout=10)
        elif training_state.get("pid"):
            process = psutil.Process(training_state["pid"])
            process.terminate()
            process.wait(timeout=10)
        
        training_state["status"] = "stopped"
        training_state["pid"] = None
        training_process = None
        save_state()
        
        return {"message": "Training stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop training: {str(e)}")

@app.get("/api/logs")
async def get_logs():
    try:
        log_files = glob.glob(os.path.join(LOGS_DIR, "*.log"))
        log_files.sort(key=os.path.getmtime, reverse=True)
        
        logs_info = []
        for log_file in log_files[:10]:
            stat = os.stat(log_file)
            logs_info.append({
                "name": os.path.basename(log_file),
                "path": log_file,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        return logs_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@app.get("/api/logs/{log_name}")
async def get_log_content(log_name: str, lines: int = 100):
    log_path = os.path.join(LOGS_DIR, log_name)
    
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    
    try:
        with open(log_path, 'r') as f:
            all_lines = f.readlines()
            return {"lines": all_lines[-lines:], "total_lines": len(all_lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log: {str(e)}")

@app.get("/api/models")
async def get_models():
    try:
        model_dirs = [d for d in glob.glob(os.path.join(MODELS_DIR, "*")) if os.path.isdir(d)]
        model_dirs.sort(key=os.path.getmtime, reverse=True)
        
        models_info = []
        for model_dir in model_dirs:
            stat = os.stat(model_dir)
            
            checkpoints = glob.glob(os.path.join(model_dir, "*.zip"))
            
            models_info.append({
                "name": os.path.basename(model_dir),
                "path": model_dir,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "checkpoints": len(checkpoints),
            })
        
        return models_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@app.get("/api/metrics")
async def get_metrics():
    if not training_state.get("current_run"):
        return {"metrics": []}
    
    return {"metrics": [], "message": "Metrics coming from tensorboard"}

@app.get("/api/system")
async def get_system_info():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3),
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import sys
    
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    print(f"Starting Free Range Chess Training Server on port {port}")
    print(f"Open http://localhost:{port} in your browser")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
