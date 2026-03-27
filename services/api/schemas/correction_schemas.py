from pydantic import BaseModel


class CorrectionResponse(BaseModel):
    id: str
    status: str
