import asyncio
from html import escape as escape_html
from pathlib import Path

from app.core.config import Settings
from app.services.poster_menu import PosterMenuService

OUTPUT_PATH = Path("docs/yandex-menu-review.md")
HTML_OUTPUT_PATH = Path("docs/yandex-menu-review.html")


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def modifier_summary(item) -> str:
    return "; ".join(
        f"{group.name}: {' / '.join(modifier.name for modifier in group.modifiers)}"
        for group in item.modifier_groups
    )


async def main() -> None:
    menu = await PosterMenuService(Settings()).get_menu()
    items_by_category = {
        category.id: [item for item in menu.items if item.category_id == category.id]
        for category in menu.categories
    }
    lines = [
        "# Предпросмотр меню Яндекс Еды",
        "",
        (f"Подготовлено категорий: **{len(menu.categories)}**, позиций: **{len(menu.items)}**."),
        "",
        "В меню попадают только включённые категории и позиции основного Poster. "
        "Цены берутся из источника Wolt.",
        "Фотография показана прямо в таблице; под ней указано, взята она с сайта или из Poster.",
        "",
    ]
    html_lines = [
        "<!doctype html>",
        '<html lang="ru"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>Предпросмотр меню Яндекс Еды</title>",
        "<style>",
        "body{font:15px -apple-system,BlinkMacSystemFont,sans-serif;margin:24px;color:#202124}",
        "h1{margin-bottom:8px}h2{margin-top:36px}",
        "table{border-collapse:collapse;width:100%;margin-bottom:28px}",
        "th,td{border:1px solid #ddd;padding:8px;vertical-align:top;text-align:left}",
        "th{background:#f5f5f5;position:sticky;top:0}",
        "img{width:140px;height:105px;object-fit:cover;border-radius:8px;background:#eee}",
        ".num{white-space:nowrap}.source{display:block;margin-top:4px}",
        "</style></head><body>",
        "<h1>Предпросмотр меню Яндекс Еды</h1>",
        f"<p>Подготовлено категорий: <b>{len(menu.categories)}</b>, "
        f"позиций: <b>{len(menu.items)}</b>.</p>",
        "<p>Только включённые позиции основного Poster. Цены берутся из источника Wolt.</p>",
    ]
    for category in menu.categories:
        lines.extend(
            [
                f"## {category.name}",
                "",
                "| ID | Позиция | Цена | Размер | Описание | Выбор | Фото |",
                "|---:|---|---:|---:|---|---|---|",
            ]
        )
        html_lines.extend(
            [
                f"<h2>{escape_html(category.name)}</h2>",
                "<table><thead><tr><th>ID</th><th>Позиция</th><th>Цена</th>"
                "<th>Размер</th><th>Описание</th><th>Выбор</th>"
                "<th>Фото</th></tr></thead><tbody>",
            ]
        )
        for item in items_by_category[category.id]:
            image_url = str(item.images[0].url)
            image_source = "Сайт" if "foodpicasso.com" in image_url else "Poster"
            unit = "г" if item.measure_unit == "g" else "мл"
            modifiers = modifier_summary(item)
            lines.append(
                "| {id} | {name} | {price:g} ₸ | {measure} {unit} | {description} | "
                "{modifiers} | "
                '<img src="{url}" alt="{name}" width="120"><br>[{source}]({url}) |'.format(
                    id=item.id,
                    name=escape_cell(item.name),
                    price=item.price,
                    measure=item.measure,
                    unit=unit,
                    description=escape_cell(item.description or ""),
                    modifiers=escape_cell(modifiers),
                    source=image_source,
                    url=image_url,
                )
            )
            html_lines.append(
                "<tr><td class=num>{id}</td><td>{name}</td><td class=num>{price:g} ₸</td>"
                "<td class=num>{measure} {unit}</td><td>{description}</td>"
                "<td>{modifiers}</td>"
                '<td><img src="{url}" alt="{name}" loading="lazy">'
                '<a class="source" href="{url}">{source}</a></td></tr>'.format(
                    id=escape_html(item.id),
                    name=escape_html(item.name),
                    price=item.price,
                    measure=item.measure,
                    unit=unit,
                    description=escape_html(item.description or ""),
                    modifiers=escape_html(modifiers),
                    source=image_source,
                    url=escape_html(image_url, quote=True),
                )
            )
        lines.append("")
        html_lines.append("</tbody></table>")

    html_lines.append("</body></html>")

    await asyncio.to_thread(OUTPUT_PATH.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(OUTPUT_PATH.write_text, "\n".join(lines), encoding="utf-8")
    await asyncio.to_thread(
        HTML_OUTPUT_PATH.write_text,
        "\n".join(html_lines),
        encoding="utf-8",
    )
    print(f"Generated review files with {len(menu.items)} items")


if __name__ == "__main__":
    asyncio.run(main())
