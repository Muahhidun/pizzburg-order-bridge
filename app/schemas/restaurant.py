from pydantic import BaseModel


class RestaurantPlace(BaseModel):
    id: str
    title: str
    address: str


class RestaurantList(BaseModel):
    places: list[RestaurantPlace]
