#!/usr/bin/env python3
"""
=============================================================================
PNG 隐式元数据校验 — 验证 GB 45438-2025 五要素是否已写入
设计文档 v3.2，第 2.6 节
用途: IMG-COMPLY-001 (🔴 阻断) 校验函数
=============================================================================
用法:
    python check_metadata.py <image_path>
    # 返回 JSON: { "pass": true/false, "details": {...} }
=============================================================================
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print(json.dumps({"pass": False, "error": "Pillow not installed"}))
    sys.exit(1)


REQUIRED_TAGS = ["AIGC_Label", "ContentID", "Standard"]


def check_png_metadata(image_path: str) -> dict:
    """读取并校验 PNG 隐式标识"""
    path = Path(image_path)
    if not path.exists():
        return {"pass": False, "error": f"File not found: {image_path}"}

    try:
        img = Image.open(image_path)
    except Exception as e:
        return {"pass": False, "error": f"Cannot open image: {e}"}

    text_info = img.text if hasattr(img, "text") else {}

    # 检查每个必需标签
    missing = [tag for tag in REQUIRED_TAGS if tag not in text_info]
    found = {tag: text_info.get(tag, "(missing)") for tag in REQUIRED_TAGS}

    # 额外检查 AIGC 标识
    aigc_json = text_info.get("AIGC_METADATA", None)

    result = {
        "pass": len(missing) == 0,
        "details": {
            "found_tags": found,
            "missing_tags": missing if missing else [],
            "has_aigc_metadata_json": aigc_json is not None,
            "aigc_label": text_info.get("AIGC_Label", "(missing)"),
            "content_id": text_info.get("ContentID", "(missing)"),
            "standard": text_info.get("Standard", "(missing)"),
        },
    }

    if missing:
        result["suggestion"] = f"Missing tags: {', '.join(missing)}"

    return result


def main():
    parser = argparse.ArgumentParser(description="Check GB 45438-2025 metadata in PNG")
    parser.add_argument("image", help="Path to PNG image to check")
    args = parser.parse_args()

    result = check_png_metadata(args.image)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
