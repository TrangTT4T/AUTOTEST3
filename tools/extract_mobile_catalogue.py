"""Extract My Demo App's product catalogue from BaseActivity.populateProductsDb.

python -m tools.extract_mobile_catalogue /tmp/mda tests/data/mobile_catalogue.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from tools.app_source import commit_of

SOURCE = "app/src/main/java/com/saucelabs/mydemoapp/android/utils/base/BaseActivity.java"
TOKEN = re.compile(
    r'setTitle\("([^"]+)"\)'
    r"|setPrice\(([\d.]+)\)"
    r"|declinaisons = Lists\.newArrayList\((.*?)\);"
    r"|for \(ItemVariant decl : declinaisons\) \{(.*?)list\.add\(model\);",
    re.S,
)


def products(java: str) -> list[dict[str, str]]:
    body = java[java.index("populateProductsDb") : java.index("viewModel.insertProducts(list)")]
    found: list[dict[str, str]] = []
    title: str | None = None
    colours: list[str] = []
    for match in TOKEN.finditer(body):
        plain_title, price, variant_list, variant_loop = match.groups()
        if plain_title:
            title = plain_title
        elif price and title:
            found.append({"title": title, "price": price})
            title = None
        elif variant_list:
            colours = re.findall(r'new ItemVariant\("([^"]+)"', variant_list)
        elif variant_loop:
            base = re.search(r'setTitle\("([^"]+) \(" \+ decl\.color \+ "\)"\)', variant_loop)
            loop_price = re.search(r"setPrice\(([\d.]+)\)", variant_loop)
            if base is None or loop_price is None:
                raise ValueError("unexpected variant loop shape in BaseActivity.java")
            found += [{"title": f"{base.group(1)} ({c})", "price": loop_price.group(1)} for c in colours]
    return found


def handle(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def main() -> None:
    src_root, out = Path(sys.argv[1]), Path(sys.argv[2])
    items = products((src_root / SOURCE).read_text(encoding="utf-8"))
    data = {
        "_source": f"saucelabs/my-demo-app-android {commit_of(src_root)}, "
        "BaseActivity.populateProductsDb (static extraction, not run on a device)",
        "currency": "USD",
        "products": [
            {
                "title": p["title"],
                "handle": handle(p["title"]),
                "variants": [{"id": i + 1, "title": "Default", "price": p["price"], "available": True}],
            }
            for i, p in enumerate(items)
        ],
    }
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(len(items), "products")


if __name__ == "__main__":
    main()
