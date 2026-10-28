from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=72)
    role:str ="customer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: SecretStr
    new_password: SecretStr = Field(min_length=8, max_length=72)

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
