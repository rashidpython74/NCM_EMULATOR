"""
Main application entry point for Monetx NCM SSH Emulator
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from config import settings
from integration import NMSIntegration, create_embedded_template

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="SSH Terminal Emulator for Network Configuration Management",
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import routes after app creation
from app import *  # Import all routes from app.py

# Setup NMS integration if enabled
if settings.NMS_INTEGRATION_ENABLED:
    try:
        create_embedded_template()
        nms_integration = NMSIntegration(app, settings.get_nms_config())
        logger.info("NMS integration enabled")
    except Exception as e:
        logger.error(f"Failed to setup NMS integration: {e}")

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"NMS Integration: {settings.NMS_INTEGRATION_ENABLED}")
    
    # Create necessary directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down application")
    
    # Close all active SSH connections
    from app import active_connections, active_shells
    for session_id in list(active_connections.keys()):
        try:
            active_connections[session_id].close()
            logger.info(f"Closed SSH connection: {session_id}")
        except Exception as e:
            logger.error(f"Error closing connection {session_id}: {e}")
    
    # Clear connection dictionaries
    active_connections.clear()
    active_shells.clear()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
