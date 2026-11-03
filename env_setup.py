import subprocess
import os

def main():
    print("=== Starting Project Setup ===\n")

    if not os.path.exists(".venv"):
        print("Creating virtual environment...")
        subprocess.run(["python", "-m", "venv", ".venv"])
    else:
        print("Virtual environment already exists.")

    print("\nInstalling backend dependencies...")
    subprocess.run([r".venv\Scripts\pip.exe", "install", "-r", "requirements.txt"])

    print("\nInstalling frontend dependencies...")
    subprocess.run(["npm", "install"], cwd="./frontend", shell=True)
    
    print("\nConfiguring CMake...")
    subprocess.run(["cmake", "-S", "core", "-B", "build"])

    print("\nBuilding C++ engine...")
    subprocess.run(["cmake", "--build", "build", "--config", "Release"])

    print("\n=== Setup Complete! You can now run 'python run.py' ===")

if __name__ == "__main__":
    main()
