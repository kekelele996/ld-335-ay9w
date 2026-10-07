from pydantic import BaseModel


class TokenRequest(BaseModel):
    client_id: str
    scopes: list[str] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
