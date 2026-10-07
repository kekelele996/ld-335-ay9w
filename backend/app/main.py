from fastapi import FastAPI, Request

from app.api.router import api_router
from app.core.logging import logger
from app.db.session import Base, engine
from app.models import settlement

app = FastAPI(title="gbinsureapi 医保智能结算API网关", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("gbinsureapi started")


@app.middleware("http")
async def audit_request(request: Request, call_next):
    response = await call_next(request)
    logger.info("audit path=%s status=%s", request.url.path, response.status_code)
    return response


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gbinsureapi"}


app.include_router(api_router, prefix="/api")
