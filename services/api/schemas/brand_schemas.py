from pydantic import BaseModel


class BrandRulesetResponse(BaseModel):
    id: str
    name: str
    version: int
