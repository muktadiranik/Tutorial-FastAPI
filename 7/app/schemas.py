from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


class UserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50, pattern=r"^\S+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return password


class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDataBase(User):
    hashed_password: str


class ModelRequest(BaseModel):
    name: str
    description: str
    provider: str
    website: HttpUrl


class CourseRequest(BaseModel):
    name: str
    description: str
    price: float
    instructor_id: int | None = Field(default=None, gt=0)


class CourseCreateRequest(CourseRequest):
    instructor_id: int = Field(gt=0)


class CourseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price: float | None
    instructor_id: int | None
    instructor: UserResponse | None

    class Config:
        from_attributes = True


class CourseResponseBulk(BaseModel):
    id: int
    name: str
    description: str | None
    price: float | None
    instructor_id: int | None

    class Config:
        from_attributes = True


class UserWithCoursesResponseBulk(UserResponse):
    courses: list[CourseResponseBulk] = Field(default_factory=list)


class UserWithCoursesResponse(UserResponse):
    courses: CourseResponse | None
