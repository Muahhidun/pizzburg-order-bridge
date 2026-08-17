from app.adapters.storefront import (
    parse_homepage_photos,
    parse_product_photo,
    product_photo_key,
    storefront_photo_keys,
)


def test_storefront_aliases_match_current_site_names():
    assert "6 крылышек соус" in storefront_photo_keys("108", "Крылышки - 6шт")
    assert "донер куриный 1 00 халапеньо" in storefront_photo_keys(
        "131", "Донер стандартный"
    )


def test_direct_product_photo_has_priority_key():
    assert storefront_photo_keys("120", "Донерная")[0] == product_photo_key("120")


def test_parse_homepage_photos():
    page = """
    <div class="ddish ddish--with-photo">
      <img data-full="https://cdn.example/wings.jpg" class="ddish__photo">
      <a class="ddish__name" href="/product/389">6&nbsp;- Крылышек +&nbsp;соус</a>
    </div>
    """

    assert parse_homepage_photos(page) == {
        "6 крылышек соус": "https://cdn.example/wings.jpg"
    }


def test_parse_direct_product_photo():
    page = '<link itemprop="image" href="https://cdn.example/doner.jpg"/>'

    assert parse_product_photo(page) == "https://cdn.example/doner.jpg"
