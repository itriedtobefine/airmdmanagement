"""
Главный файл приложения FastAPI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import engine, Base
from routes import auth, spreadsheets

# Создание таблиц БД
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Spreadsheet App API",
    description="API для веб-приложения таблиц (аналог NextCloud/Excel в Web)",
    version="1.0.0"
)

# CORS middleware для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов
app.include_router(auth.router, prefix="/api")
app.include_router(spreadsheets.router, prefix="/api")

# Раздача статических файлов фронтенда
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/")
async def serve_frontend():
    """Сервинг главного HTML файла."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Spreadsheet App API - Visit /docs for API documentation"}


@app.get("/{path:path}")
async def serve_static(path: str):
    """Сервинг статических файлов."""
    file_path = os.path.join(frontend_dir, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
