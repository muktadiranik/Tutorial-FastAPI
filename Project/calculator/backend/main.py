from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .calculator import CalculationError, calculate


app = FastAPI(title="calcula API", version="1.0.0")


class CalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str = Field(min_length=1, max_length=256)


class CalculationResponse(BaseModel):
    expression: str
    result: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/calculate", response_model=CalculationResponse)
def calculate_expression(request: CalculationRequest) -> CalculationResponse:
    try:
        result = calculate(request.expression)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CalculationResponse(expression=request.expression.strip(), result=result)


frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
