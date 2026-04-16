"""
FastAPI приложение для оценки стоимости разработки справочников.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os

from download_model import load_model, extract_parameters
from calculator import CostCalculator

# Инициализация
load_model()
calculator = CostCalculator()

app = FastAPI(
    title="Оценка стоимости справочников",
    description="Система для оценки экономической эффективности передачи разработки и поддержки справочников",
    version="1.0.0"
)

# Монтирование статики
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


class EstimateRequest(BaseModel):
    """Запрос на оценку."""
    description: str
    custom_support_hours: Optional[int] = None


class TaskItem(BaseModel):
    """Элемент задачи."""
    type: str
    hours: int
    note: Optional[str] = None


class BreakdownDetail(BaseModel):
    """Детализация расходов."""
    hours: int
    cost: int


class DevelopmentBreakdown(BaseModel):
    """Детализация разработки."""
    development: BreakdownDetail
    qa: BreakdownDetail
    analysis: BreakdownDetail
    tasks: List[TaskItem]


class SupportBreakdown(BaseModel):
    """Детализация поддержки."""
    monthly_hours: int
    yearly_hours: int
    cost: int
    types: List[TaskItem]


class EstimateResponse(BaseModel):
    """Ответ с оценкой."""
    success: bool
    error: Optional[str] = None
    development_cost: Optional[int] = None
    support_cost_yearly: Optional[int] = None
    total_first_year: Optional[int] = None
    development_breakdown: Optional[dict] = None
    support_breakdown: Optional[dict] = None
    summary: Optional[str] = None
    detected_tasks: Optional[List[str]] = None
    tech_stack: Optional[List[str]] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница приложения."""
    index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse(content="<h1>Ошибка: файл index.html не найден</h1>", status_code=500)


@app.post("/api/estimate", response_model=EstimateResponse)
async def estimate(request: EstimateRequest):
    """
    Оценить стоимость разработки и поддержки справочника.
    
    Принимает текстовое описание и возвращает расчет стоимости.
    """
    # Проверка входных данных
    if not request.description or len(request.description.strip()) < 10:
        return EstimateResponse(
            success=False,
            error="Описание должно содержать минимум 10 символов"
        )
    
    # Извлечение параметров через NLP
    params = extract_parameters(request.description)
    
    # Проверка на соответствие целевому сценарию
    if params.get("error") == "out_of_scope":
        return EstimateResponse(
            success=False,
            error="Запрос выходит за рамки оценки справочников. Система предназначена только для расчета задач по разработке и поддержке справочников и реестров в сфере Reference Data Management и Master Data Management."
        )
    
    # Проверка на валидность извлечения
    if not params.get("is_valid"):
        return EstimateResponse(
            success=False,
            error="Не удалось определить тип задачи. Пожалуйста, опишите справочник более подробно (тип, функции, интеграции)."
        )
    
    # Расчет стоимости разработки
    dev_cost, dev_breakdown = calculator.calculate_development_cost(
        tasks=params["tasks"],
        include_qa=True,
        include_analysis=True
    )
    
    # Расчет стоимости поддержки
    support_cost, support_breakdown = calculator.calculate_support_cost(
        support_types=params["support"],
        custom_hours_per_month=request.custom_support_hours,
        months=12
    )
    
    # Генерация обоснования
    summary = calculator.generate_summary(
        dev_cost=dev_cost,
        dev_breakdown=dev_breakdown,
        support_cost=support_cost,
        support_breakdown=support_breakdown,
        tech_stack=params["tech_stack"]
    )
    
    return EstimateResponse(
        success=True,
        development_cost=dev_cost,
        support_cost_yearly=support_cost,
        total_first_year=dev_cost + support_cost,
        development_breakdown=dev_breakdown,
        support_breakdown=support_breakdown,
        summary=summary,
        detected_tasks=params["tasks"],
        tech_stack=params["tech_stack"]
    )


@app.get("/api/norms/development")
async def get_development_norms():
    """Получить нормативы на разработку."""
    norms = []
    for _, row in calculator.dev_norms.iterrows():
        norms.append({
            "task_type": row["task_type"],
            "description": row["description"],
            "hours": int(row["hours"])
        })
    return {"norms": norms}


@app.get("/api/norms/support")
async def get_support_norms():
    """Получить нормативы на поддержку."""
    norms = []
    for _, row in calculator.support_norms.iterrows():
        norms.append({
            "task_type": row["task_type"],
            "description": row["description"],
            "hours_per_month": int(row["hours_per_month"])
        })
    return {"norms": norms}


@app.get("/api/rates")
async def get_hourly_rates():
    """Получить часовые ставки."""
    rates = []
    for _, row in calculator.hourly_rates.iterrows():
        rates.append({
            "role": row["role"],
            "description": row["description"],
            "hourly_rate": int(row["hourly_rate"])
        })
    return {"rates": rates}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
