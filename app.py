"""
FastAPI application for Reference Data Management Cost Calculator.
Main entry point for the backend service.
License: MIT
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import ValidationError

from models.schemas import (
    UserRequest,
    CostCalculationResponse,
    ErrorResponse,
    ExtractedParameters,
)
from services.llm_extractor import ParameterExtractor
from services.cost_calculator import CostCalculator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Global service instances
extractor: ParameterExtractor | None = None
calculator: CostCalculator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for initializing services."""
    global extractor, calculator
    
    logger.info("Starting up application...")
    
    # Initialize paths
    base_dir = Path(__file__).parent
    model_path = base_dir / "models" / "qwen2.5-3b-instruct-q4_k_m.gguf"
    data_dir = base_dir / "data"
    
    # Check if model exists
    if not model_path.exists():
        logger.warning(
            f"Model not found at {model_path}. Run 'python setup_model.py' first."
        )
        logger.warning("LLM extraction will be unavailable until model is downloaded.")
        extractor = None
    else:
        try:
            extractor = ParameterExtractor(model_path)
            logger.info("ParameterExtractor initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ParameterExtractor: {e}")
            extractor = None
    
    # Initialize calculator
    try:
        calculator = CostCalculator(
            development_effort_path=data_dir / "development_effort.csv",
            support_effort_path=data_dir / "support_effort.csv",
            hourly_rates_path=data_dir / "hourly_rates.csv",
        )
        logger.info("CostCalculator initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize CostCalculator: {e}")
        raise
    
    yield
    
    logger.info("Shutting down application...")


app = FastAPI(
    title="Reference Data Management Cost Calculator",
    description="Local web application for estimating development and support costs of reference data management projects.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    index_path = Path(__file__).parent / "templates" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/calculate", response_model=CostCalculationResponse)
async def calculate_cost(request: UserRequest):
    """
    Calculate development and support costs based on text description.
    
    Args:
        request: UserRequest with text description
        
    Returns:
        CostCalculationResponse with detailed breakdown
    """
    if extractor is None:
        raise HTTPException(
            status_code=503,
            detail="LLM model not available. Please run 'python setup_model.py' first.",
        )
    
    if calculator is None:
        raise HTTPException(
            status_code=503,
            detail="Cost calculator not initialized.",
        )
    
    try:
        # Step 1: Extract parameters using LLM
        logger.info(f"Extracting parameters from input: {request.description[:100]}...")
        params = extractor.extract_parameters(request.description)
        logger.info(f"Extracted parameters: {params.model_dump()}")
        
        # Step 2: Calculate costs
        result = calculator.calculate(params)
        
        if not result.success:
            logger.warning(f"Calculation failed: {result.error_message}")
            raise HTTPException(
                status_code=400,
                detail=result.error_message,
            )
        
        logger.info(
            f"Calculation successful: Development={result.development_total_cost_rub} RUB, "
            f"Support={result.support_total_cost_per_year_rub} RUB/year"
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Parameter extraction error: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract parameters: {str(e)}",
        )
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": extractor is not None,
        "calculator_ready": calculator is not None,
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "error_code": "NOT_FOUND"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "error_code": "INTERNAL_ERROR"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
