"""Official Python Backend Runner for BlockBrain AI & Flutter Desktop HUD.
Runs the FastAPI REST API + WebSocket server on port 8844.
"""

import os
import sys
from pathlib import Path

# Ensure repo root and blockbrain package are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn
from blockbrain.web.server import app

def main():
    port = int(os.environ.get("BLOCKBRAIN_PORT", 8844))
    host = os.environ.get("BLOCKBRAIN_HOST", "0.0.0.0")
    print(f"⚡ Starting BlockBrain Python Brain on http://{host}:{port} ...")
    print(f"🔌 WebSocket stream ready at ws://127.0.0.1:{port}/ws")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
