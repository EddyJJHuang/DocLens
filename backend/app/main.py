from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup resources (load FAISS/BM25 indices) on startup
    yield
    # Cleanup resources on shutdown

app = FastAPI(title="DocLens API", version="1.0.0", lifespan=lifespan)

# Allow React Frontend origins (Update for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
