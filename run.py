import subprocess

def main():
    print("Starting servers. Press Ctrl+C to stop both...")
    
    backend = subprocess.Popen(
        [r".venv\Scripts\python.exe", "-m", "uvicorn", "main:app", "--reload"],
        cwd="./backend" 
    )
    
    frontend = subprocess.Popen(
        ["npm", "run", "dev"], 
        cwd="./frontend", 
        shell=True
    )
    
    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nCtrl+C detected! Shutting down servers...")
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    main()
