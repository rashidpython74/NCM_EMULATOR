"""
Integration module for Monetx NCM SSH Emulator
This module provides endpoints and utilities for integrating with existing NMS
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class NMSIntegration:
    """Integration handler for existing NMS"""
    
    def __init__(self, app: FastAPI, nms_config: Dict[str, Any] = None):
        self.app = app
        self.nms_config = nms_config or {}
        self.templates = Jinja2Templates(directory="templates")
        self.active_sessions = {}
        self.setup_integration_routes()
    
    def setup_integration_routes(self):
        """Setup integration endpoints for NMS"""
        
        @self.app.get("/nms/embedded", response_class=HTMLResponse)
        async def embedded_emulator(request: Request):
            """Embedded SSH emulator for NMS integration"""
            return self.templates.TemplateResponse(
                "embedded.html", 
                {"request": request, "config": self.nms_config}
            )
        
        @self.app.post("/nms/api/auth")
        async def nms_auth(request: Request):
            """Authenticate NMS user and generate session token"""
            try:
                # Get NMS auth token from request
                nms_token = request.headers.get("X-NMS-Token")
                if not nms_token:
                    raise HTTPException(status_code=401, detail="NMS token required")
                
                # Verify NMS token (implement based on your NMS auth system)
                user_data = await self.verify_nms_token(nms_token)
                
                # Generate SSH emulator session token
                session_token = self.generate_session_token(user_data)
                
                return {
                    "session_token": session_token,
                    "expires_in": 3600,
                    "user": user_data
                }
                
            except Exception as e:
                logger.error(f"NMS auth error: {str(e)}")
                raise HTTPException(status_code=401, detail="Authentication failed")
        
        @self.app.post("/nms/api/device-connect")
        async def device_connect(request: Request):
            """Connect to specific device from NMS"""
            try:
                data = await request.json()
                
                # Validate session token
                session_token = request.headers.get("X-Session-Token")
                user_data = self.verify_session_token(session_token)
                
                # Extract device connection details
                device_info = {
                    "host": data.get("device_ip"),
                    "port": data.get("port", 22),
                    "username": data.get("username"),
                    "password": data.get("password"),
                    "device_id": data.get("device_id"),
                    "device_name": data.get("device_name")
                }
                
                # Log the connection attempt for audit
                await self.log_connection_attempt(user_data, device_info)
                
                # Create SSH connection
                from app import connect_ssh
                result = await connect_ssh(device_info)
                
                return {
                    "success": True,
                    "session_id": result["session_id"],
                    "device_info": device_info
                }
                
            except Exception as e:
                logger.error(f"Device connection error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")
        
        @self.app.get("/nms/api/device-info/{device_id}")
        async def get_device_info(device_id: str, request: Request):
            """Get device information from NMS"""
            try:
                session_token = request.headers.get("X-Session-Token")
                user_data = self.verify_session_token(session_token)
                
                # Fetch device info from your NMS database
                device_info = await self.fetch_device_from_nms(device_id, user_data)
                
                return device_info
                
            except Exception as e:
                logger.error(f"Device info error: {str(e)}")
                raise HTTPException(status_code=404, detail="Device not found")
        
        @self.app.get("/nms/api/user-sessions")
        async def get_user_sessions(request: Request):
            """Get user's active SSH sessions"""
            try:
                session_token = request.headers.get("X-Session-Token")
                user_data = self.verify_session_token(session_token)
                
                # Return user's active sessions
                user_sessions = [
                    session for session in self.active_sessions.values()
                    if session.get("user_id") == user_data.get("user_id")
                ]
                
                return {"sessions": user_sessions}
                
            except Exception as e:
                logger.error(f"Get sessions error: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to get sessions")
    
    async def verify_nms_token(self, token: str) -> Dict[str, Any]:
        """Verify NMS authentication token"""
        # Implement based on your NMS authentication system
        # This is a placeholder implementation
        
        if token == "demo-nms-token":
            return {
                "user_id": "demo_user",
                "username": "admin",
                "permissions": ["ssh_connect", "device_manage"]
            }
        
        # In production, verify against your NMS auth system
        # Example: JWT verification, database lookup, etc.
        raise HTTPException(status_code=401, detail="Invalid NMS token")
    
    def generate_session_token(self, user_data: Dict[str, Any]) -> str:
        """Generate session token for SSH emulator"""
        payload = {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "permissions": user_data.get("permissions", []),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        
        # Use your JWT secret key
        secret_key = self.nms_config.get("jwt_secret", "your-secret-key")
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        return token
    
    def verify_session_token(self, token: str) -> Dict[str, Any]:
        """Verify SSH emulator session token"""
        if not token:
            raise HTTPException(status_code=401, detail="Session token required")
        
        try:
            secret_key = self.nms_config.get("jwt_secret", "your-secret-key")
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Session expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid session token")
    
    async def log_connection_attempt(self, user_data: Dict[str, Any], device_info: Dict[str, Any]):
        """Log SSH connection attempts for auditing"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "device_id": device_info.get("device_id"),
            "device_ip": device_info.get("host"),
            "action": "ssh_connect_attempt"
        }
        
        # Log to your audit system
        logger.info(f"SSH connection attempt: {log_entry}")
        
        # Store in active sessions
        session_id = secrets.token_hex(16)
        self.active_sessions[session_id] = log_entry
    
    async def fetch_device_from_nms(self, device_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch device information from NMS database"""
        # Implement based on your NMS database structure
        # This is a placeholder implementation
        
        if device_id == "demo-device-001":
            return {
                "device_id": "demo-device-001",
                "device_name": "Core Router 01",
                "device_ip": "192.168.1.1",
                "device_type": "router",
                "vendor": "Cisco",
                "model": "ISR4321",
                "location": "Data Center Rack 1",
                "status": "online"
            }
        
        raise HTTPException(status_code=404, detail="Device not found")

def create_embedded_template():
    """Create embedded template for NMS integration"""
    template_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCM SSH Emulator - Embedded</title>
    <link rel="stylesheet" href="/static/style.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            background: transparent !important;
        }
        .container {
            max-width: 100%;
            padding: 10px;
        }
        .glass-header {
            display: none;
        }
        .connection-panel {
            display: none;
        }
        .terminal-section {
            margin: 0;
        }
        .quick-commands {
            display: none;
        }
        .embedded-controls {
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
        }
        .embedded-btn {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 8px 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 5px;
        }
        .embedded-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="embedded-controls">
            <button class="embedded-btn" onclick="toggleFullscreen()">
                <i class="fas fa-expand"></i> Fullscreen
            </button>
            <button class="embedded-btn" onclick="closeEmulator()">
                <i class="fas fa-times"></i> Close
            </button>
        </div>
        
        <main class="main-content">
            <section class="terminal-section glass-card">
                <div class="terminal-header">
                    <h2><i class="fas fa-terminal"></i> SSH Terminal</h2>
                    <div class="terminal-controls">
                        <button id="clear-terminal-btn" class="btn btn-sm btn-outline">
                            <i class="fas fa-trash"></i> Clear
                        </button>
                        <button id="copy-btn" class="btn btn-sm btn-outline">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                    </div>
                </div>
                
                <div class="terminal-container">
                    <div id="terminal-output" class="terminal-output"></div>
                    <div class="terminal-input-container">
                        <input type="text" id="terminal-input" class="terminal-input" placeholder="Enter command..." disabled>
                        <button id="send-btn" class="btn btn-primary btn-sm" disabled>
                            <i class="fas fa-paper-plane"></i> Send
                        </button>
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script src="/static/script.js"></script>
    <script>
        // Embedded mode specific functions
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        }
        
        function closeEmulator() {
            if (window.parent !== window) {
                // Send message to parent window to close
                window.parent.postMessage({action: 'close_ssh_emulator'}, '*');
            }
        }
        
        // Auto-connect if device info is provided
        window.addEventListener('load', async () => {
            const urlParams = new URLSearchParams(window.location.search);
            const deviceId = urlParams.get('device_id');
            const sessionToken = urlParams.get('session_token');
            
            if (deviceId && sessionToken) {
                try {
                    // Fetch device info and auto-connect
                    const response = await fetch(`/nms/api/device-info/${deviceId}`, {
                        headers: {
                            'X-Session-Token': sessionToken
                        }
                    });
                    
                    if (response.ok) {
                        const deviceInfo = await response.json();
                        // Auto-connect to device
                        // This would be implemented based on your needs
                    }
                } catch (error) {
                    console.error('Auto-connect failed:', error);
                }
            }
        });
    </script>
</body>
</html>
    '''
    
    import os
    os.makedirs("templates", exist_ok=True)
    with open("templates/embedded.html", "w") as f:
        f.write(template_content)

# Example configuration for NMS integration
NMS_CONFIG = {
    "jwt_secret": "your-jwt-secret-key-change-in-production",
    "nms_base_url": "https://your-nms-domain.com",
    "allowed_origins": ["https://your-nms-domain.com"],
    "audit_log_enabled": True,
    "session_timeout": 3600,  # 1 hour
    "max_sessions_per_user": 5
}
