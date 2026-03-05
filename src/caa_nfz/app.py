import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from caa_nfz.database import init_db
from caa_nfz.routes import router
from caa_nfz.scheduler import shutdown_scheduler, start_scheduler
from caa_nfz.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


app = FastAPI(
    title="CAA 禁限航區 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix=settings.api_prefix)
