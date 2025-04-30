from pydantic import BaseModel

class ProfileCreateRequest(BaseModel):
    name: str
    proxy_str: str = ""
