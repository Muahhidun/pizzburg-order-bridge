from typing import Literal

from pydantic import BaseModel


class RestaurantResponse(BaseModel):
    id: str
    name: str
    active: bool
    mode: Literal["dry-run", "live"]
