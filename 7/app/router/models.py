from enum import Enum

from fastapi import APIRouter

from ..schemas import ModelRequest


router = APIRouter()


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


@router.get("/models")
async def get_models():
    return {"models": [model.value for model in ModelName]}


@router.post("/models")
async def create_model(model: ModelRequest):
    return {"message": f"Model '{model.name}' created successfully!"}
