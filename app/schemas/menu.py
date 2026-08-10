from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MenuCategory(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(max_length=64)
    name: str
    sort_order: int = Field(default=100, alias="sortOrder")


class MenuItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(max_length=64)
    category_id: str = Field(alias="categoryId", max_length=64)
    name: str
    description: str | None = None
    price: float = Field(gt=0)
    measure: int = Field(gt=0)
    measure_unit: Literal["г", "мл", "g", "ml"] = Field(alias="measureUnit")
    is_catchweight: bool = Field(default=False, alias="isCatchweight")
    sort_order: int = Field(default=100, alias="sortOrder")


class MenuComposition(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    categories: list[MenuCategory]
    items: list[MenuItem]
    last_change: str = Field(alias="lastChange")
