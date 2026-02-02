import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import router as api_router
from app.adapters.email.listener import start_email_listener
import logging

setup_logging()
logger = logging.getLogger("main")

def _setup_email_listener():
    is_listener_running = False
    for t in threading.enumerate():
        if t.name == "EmailListenerThread":
            is_listener_running = True
            break
    
    if not is_listener_running and settings.EMAIL_PROVIDER != "unknown":
        email_thread = threading.Thread(
            target=start_email_listener, 
            name="EmailListenerThread", 
            daemon=True
        )
        email_thread.start()
        logger.info("Email Listener Thread Started")
    elif is_listener_running:
        logger.warning("⚠️ Email Listener already running, skipping start.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    if settings.ENABLE_BACKGROUND_WORKER:
        _setup_email_listener()
    
    yield
    

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/health")
def health():
    return {"status": "ok"}