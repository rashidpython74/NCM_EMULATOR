from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import paramiko
import asyncio
import json
import uuid
from typing import Dict
import logging

# Import settings
try:
    from config import settings
except ImportError:
    # Fallback settings if config.py is not available
    class Settings:
        SSH_TIMEOUT = 10
        SSH_MAX_SESSIONS = 100
        SSH_SESSION_TIMEOUT = 3600
    settings = Settings()

# Create FastAPI app (will be overridden by main.py)
app = FastAPI(title="Monetx NCM Emulator", version="1.0.0")

# Configure CORS for integration with existing NMS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure with your NMS domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store active SSH connections
active_connections: Dict[str, paramiko.SSHClient] = {}
active_shells: Dict[str, paramiko.Channel] = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    """Serve the main emulator page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/health")
async def health_check():
    """Health check endpoint for NMS integration"""
    return {"status": "healthy", "service": "ncm-ssh-emulator"}

@app.post("/api/connect")
async def connect_ssh(connection_data: dict):
    """Connect to SSH server"""
    try:
        session_id = str(uuid.uuid4())
        hostname = connection_data.get("host")
        port = connection_data.get("port", 22)
        username = connection_data.get("username")
        password = connection_data.get("password")
        
        if not all([hostname, username, password]):
            raise HTTPException(status_code=400, detail="Host, username, and password required")
        
        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port, username, password, timeout=settings.SSH_TIMEOUT)
        
        # Create shell
        shell = client.invoke_shell()
        shell.settimeout(0.1)
        
        # Store connection
        active_connections[session_id] = client
        active_shells[session_id] = shell
        
        logger.info(f"SSH connection established: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "connected",
            "message": "SSH connection successful"
        }
        
    except Exception as e:
        logger.error(f"SSH connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@app.post("/api/disconnect/{session_id}")
async def disconnect_ssh(session_id: str):
    """Disconnect SSH session"""
    try:
        if session_id in active_connections:
            active_connections[session_id].close()
            del active_connections[session_id]
        
        if session_id in active_shells:
            del active_shells[session_id]
        
        logger.info(f"SSH connection closed: {session_id}")
        return {"status": "disconnected", "message": "Session closed"}
        
    except Exception as e:
        logger.error(f"Error disconnecting: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Disconnection failed: {str(e)}")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time terminal communication"""
    await websocket.accept()
    
    try:
        if session_id not in active_shells:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid session ID"
            }))
            return
        
        shell = active_shells[session_id]
        
        # Start background task to read shell output
        async def read_shell_output():
            while True:
                try:
                    if shell.recv_ready():
                        data = shell.recv(4096).decode('utf-8', errors='ignore')
                        if data:
                            await websocket.send_text(json.dumps({
                                "type": "output",
                                "data": data
                            }))
                    await asyncio.sleep(0.1)
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Shell read error: {str(e)}"
                    }))
                    break
        
        # Start reading task
        read_task = asyncio.create_task(read_shell_output())
        
        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "command":
                    command = data.get("command", "")
                    if shell and shell.send_ready():
                        shell.send(command)
                        logger.info(f"Command sent: {command[:50]}...")
                
                elif data.get("type") == "resize":
                    # Handle terminal resize if needed
                    pass
                    
                elif data.get("type") == "filelist":
                    # Handle file listing for tab completion
                    path = data.get("path", "")
                    if shell and shell.send_ready():
                        # Send ls command to get file listing
                        ls_command = f"ls -F {path} 2>/dev/null || echo 'No such directory'\n"
                        shell.send(ls_command)
                        
                        # Read the output
                        await asyncio.sleep(0.1)  # Give time for command to execute
                        output = ""
                        while shell.recv_ready():
                            output += shell.recv(1024).decode('utf-8', errors='ignore')
                        
                        # Parse the output to get file/directory names
                        files = []
                        if output and "No such directory" not in output:
                            # ls -F adds / to directories, * to executables, @ to symlinks
                            for item in output.strip().split('\n'):
                                if item.strip():
                                    # Keep the trailing slash for directories
                                    files.append(item.strip())
                        
                        await websocket.send_json({
                            "type": "filelist",
                            "path": path,
                            "files": files
                        })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                break
        
        # Cleanup
        read_task.cancel()
        
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
    finally:
        await websocket.close()

@app.get("/api/sessions")
async def list_sessions():
    """List active SSH sessions (for admin monitoring)"""
    sessions = []
    for session_id in active_connections:
        sessions.append({
            "session_id": session_id,
            "status": "active"
        })
    return {"sessions": sessions}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
