from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class MenuCategory(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(max_length=64)
    name: str
    sort_order: int = Field(default=100, alias="sortOrder")


class MenuItemImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hash: str = Field(min_length=40, max_length=40, pattern=r"^[0-9a-f]{40}$")
    url: HttpUrl


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
    images: list[MenuItemImage] = Field(min_length=1)


class MenuComposition(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    categories: list[MenuCategory]
    items: list[MenuItem]
    last_change: str = Field(alias="lastChange")
