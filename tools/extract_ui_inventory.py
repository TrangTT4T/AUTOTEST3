"""Extract every android:id and content description per layout from My Demo App's source.

git clone --depth 1 https://github.com/saucelabs/my-demo-app-android.git /tmp/mda
python -m tools.extract_ui_inventory /tmp/mda tests/data/mobile_ui_inventory.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from tools.app_source import commit_of, strings_of

TAG = re.compile(r"<([\w.]+)\s([^>]*?)/?>", re.S)
ATTR = re.compile(r'(android:id|android:contentDescription|android:text)="([^"]*)"')


def inventory(src_root: Path) -> dict[str, object]:
    res = src_root / "app" / "src" / "main" / "res"
    strings = strings_of(res)

    def resolve(value: str | None) -> str | None:
        match = re.match(r"@string/(.+)", value or "")
        return strings.get(match.group(1), value) if match else value

    layouts: dict[str, dict[str, dict[str, str | None]]] = {}
    for path in sorted((res / "layout").glob("*.xml")):
        items: dict[str, dict[str, str | None]] = {}
        for tag in TAG.finditer(path.read_text(encoding="utf-8")):
            attrs = dict(ATTR.findall(tag.group(2)))
            if "android:id" in attrs:
                items[attrs["android:id"].replace("@+id/", "")] = {
                    "class": tag.group(1).split(".")[-1],
                    "content_description": resolve(attrs.get("android:contentDescription")),
                    "text": resolve(attrs.get("android:text")),
                }
        layouts[path.stem] = items
    return {
        "_source": f"saucelabs/my-demo-app-android {commit_of(src_root)}, res/layout (static extraction)",
        "package": "com.saucelabs.mydemoapp.android",
        "launch_activity": ".view.activities.SplashActivity",
        "layouts": layouts,
    }


def main() -> None:
    src_root, out = Path(sys.argv[1]), Path(sys.argv[2])
    data = inventory(src_root)
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    layouts = data["layouts"]
    if not isinstance(layouts, dict):
        raise TypeError(f"expected a dict of layouts, got {type(layouts).__name__}")
    print(len(layouts), "layouts,", sum(len(v) for v in layouts.values()), "ids")


if __name__ == "__main__":
    main()
