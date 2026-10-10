"""Start ThreatDefender AI:  python run.py"""
import uvicorn

from app import config

if __name__ == "__main__":
    print(f"\n  ThreatDefender AI -> http://{config.HOST}:{config.PORT}   (API docs: /docs)\n")
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, log_level="info")
