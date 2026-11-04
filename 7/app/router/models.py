from enum import Enum

from fastapi import APIRouter

from ..schemas import ModelRequest


router = APIRouter(prefix="/models", tags=["Models"])


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


@router.get("/", response_model=dict[str, list[str]])
async def get_models():
    return {"models": [model.value for model in ModelName]}


@router.post("/", response_model=dict[str, str])
async def create_model(model: ModelRequest):
    return {"message": f"Model '{model.name}' created successfully!"}
