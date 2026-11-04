from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from exceptions import StoryException
from router import blog, item, user, store
from auth import authentication
import models
from database import engine


app = FastAPI()
app.include_router(authentication.router)
app.include_router(blog.router)
app.include_router(item.router)
app.include_router(user.router)
app.include_router(store.router)


@app.exception_handler(StoryException)
async def story_exception_handler(request: Request, exception: StoryException):
    return JSONResponse(
        status_code=status.HTTP_418_IM_A_TEAPOT,
        content={"message": exception.name},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exception: HTTPException):
    return PlainTextResponse(str(exception.detail), status_code=exception.status_code)


models.Base.metadata.create_all(engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    tags=["home"],
    summary="Home Page",
    description="Home Page",
    response_description="Home Page",
)
async def index():
    return {"message": "Hello World"}


@app.get(
    "/about",
    status_code=status.HTTP_201_CREATED,
    tags=["about"],
    summary="About Page",
    description="About Page",
    response_description="About Page",
)
async def about():
    return {"message": "Hello World from about"}


@app.get(
    "/contact",
    tags=["contact"],
    summary="Contact Page",
    description="Contact Page",
    response_description="Contact Page",
)
async def contact():
    return {"message": "Hello World from contact"}


@app.post("/")
async def post(request: Request):
    data = await request.form()
    return {"message": data}
