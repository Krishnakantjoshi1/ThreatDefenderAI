"""ThreatDefender AI - local API + web dashboard."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import (routes_health, routes_history, routes_protection, routes_quarantine,
                     routes_scan, routes_settings)
from app.database.database import init_db
from app.modes import network_monitor
from app.utils.logger import get_logger

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    network_monitor.start_background_monitor()
    log.info("%s v%s ready on http://%s:%s", config.APP_NAME, config.APP_VERSION, config.HOST, config.PORT)
    yield


app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION, lifespan=lifespan)

# Only this computer's pages and our own browser extension may call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://[a-z]+|https?://(127\.0\.0\.1|localhost)(:\d+)?)$",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {type(exc).__name__}"})


for _r in (routes_health, routes_scan, routes_history, routes_quarantine, routes_protection, routes_settings):
    app.include_router(_r.router)

if config.frontend_dir().exists():
    # Mounted last so /api/* routes win.
    app.mount("/", StaticFiles(directory=str(config.frontend_dir()), html=True), name="frontend")
