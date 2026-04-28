from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db
from routers import auth, watchlist, scanner, alerts, analysis
from services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Stock Tool API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
app.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])


@app.get("/health")
async def health():
    return {"status": "ok"}
