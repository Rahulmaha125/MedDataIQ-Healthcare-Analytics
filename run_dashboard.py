"""
MedDataIQ — One-Click Streamlit Dashboard Launcher
Smart auto-detects free port if 8501 is busy and launches local dashboard.
"""
import socket
import subprocess
import sys


def find_free_port(start_port: int = 8501) -> int:
    """Finds an available TCP port starting from start_port."""
    port = start_port
    while port < start_port + 20:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return start_port


if __name__ == "__main__":
    free_port = find_free_port(8501)
    print("==================================================================")
    print(f"  Starting MedDataIQ Healthcare Intelligence Dashboard on Port {free_port}")
    print(f"  Local URL: http://localhost:{free_port}")
    print("==================================================================")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app/app.py",
        "--server.port",
        str(free_port),
    ]
    subprocess.run(cmd)
