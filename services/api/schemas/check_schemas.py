from pydantic import BaseModel


class CheckRunResponse(BaseModel):
    id: str
    status: str
    dqs_overall: float | None = None
