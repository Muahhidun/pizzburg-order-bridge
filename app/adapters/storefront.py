import asyncio
import html
import re
from urllib.parse import urljoin

import httpx

STOREFRONT_NAME_ALIASES = {
    "71": "Донер Куриный (0.75) + халапеньо",
    "103": "Наггетсы + соус",
    "104": "Картофельные дольки + соус",
    "105": "Сырные палочки + соус",
    "108": "6 - Крылышек + соус",
    "109": "12 - Крылышек + соус",
    "110": "24 - Крылышек + соусы",
    "111": "Фри + соус",
    "131": "Донер Куриный (1.00) + халапеньо",
    "132": "Донер Куриный (1.5) + халапеньо",
    "134": "Донер в батоне (Куриный) + халапеньо",
    "178": "Донер-Гриль + халапеньо",
}

# These products are not present in the current home-page catalogue, but their
# active product pages contain the current storefront photo.
STOREFRONT_PRODUCT_PAGES = {
    "120": "/product/404-donernaya",
    "141": "/product/437-chikenchiz-supersyrnyy",
    "179": "/product/648-doner-govyajiy-100-halapeno",
    "180": "/product/650-doner-v-batone-govyajiy-halapeno",
    "181": "/product/649-doner-govyajiy-150-halapeno",
    "182": "/product/647-doner-govyajiy-075-halapeno",
}


def normalize_product_name(value: str) -> str:
    normalized = html.unescape(value).lower().replace("ё", "е")
    return " ".join(re.sub(r"[^a-zа-я0-9]+", " ", normalized).split())


def product_photo_key(product_id: str) -> str:
    return f"poster-product:{product_id}"


def storefront_photo_keys(product_id: str, product_name: str) -> tuple[str, ...]:
    alias = STOREFRONT_NAME_ALIASES.get(product_id)
    keys = [product_photo_key(product_id)]
    if alias is not None:
        keys.append(normalize_product_name(alias))
    keys.append(normalize_product_name(product_name))
    return tuple(dict.fromkeys(keys))


def parse_homepage_photos(page: str) -> dict[str, str]:
    photos: dict[str, str] = {}
    chunks = re.split(r'(?=<div class="ddish(?: |"))', page)[1:]
    for chunk in chunks:
        name_match = re.search(r'<a class="ddish__name" href="[^"]+">\s*([^<]+)', chunk)
        photo_tag = re.search(r'<img[^>]+class="ddish__photo"[^>]*>', chunk)
        if name_match is None or photo_tag is None:
            continue
        photo_match = re.search(r'data-full="([^"]+)"', photo_tag.group(0))
        if photo_match is None:
            continue
        photos[normalize_product_name(name_match.group(1))] = html.unescape(photo_match.group(1))
    return photos


def parse_product_photo(page: str) -> str | None:
    match = re.search(
        r'<link[^>]+itemprop=["\']image["\'][^>]+href=["\']([^"\']+)',
        page,
    )
    return html.unescape(match.group(1)) if match is not None else None


class StorefrontClient:
    def __init__(self, url: str, timeout_seconds: float = 10.0) -> None:
        self._url = url
        self._timeout_seconds = timeout_seconds

    async def get_product_photos(self) -> dict[str, str]:
        urls = [self._url]
        urls.extend(urljoin(self._url, page) for page in STOREFRONT_PRODUCT_PAGES.values())
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            responses = await asyncio.gather(
                *(client.get(url) for url in urls),
                return_exceptions=True,
            )
            for index, response in enumerate(responses):
                if isinstance(response, httpx.Response) and response.is_success:
                    continue
                await asyncio.sleep(0.25)
                try:
                    responses[index] = await client.get(urls[index])
                except httpx.HTTPError:
                    pass

        photos: dict[str, str] = {}
        homepage = responses[0]
        if isinstance(homepage, httpx.Response) and homepage.is_success:
            photos.update(parse_homepage_photos(homepage.text))

        for (product_id, _), response in zip(
            STOREFRONT_PRODUCT_PAGES.items(), responses[1:], strict=True
        ):
            if not isinstance(response, httpx.Response) or not response.is_success:
                continue
            photo_url = parse_product_photo(response.text)
            if photo_url is not None:
                photos[product_photo_key(product_id)] = photo_url
        return photos
