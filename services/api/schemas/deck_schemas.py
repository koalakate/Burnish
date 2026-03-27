from pydantic import BaseModel


class DeckResponse(BaseModel):
    id: str
    name: str
    slide_count: int
