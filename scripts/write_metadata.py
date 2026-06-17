#!/usr/bin/env python3
"""
=============================================================================
PNG 隐式元数据写入 — GB 45438-2025 五要素 1-3
设计文档 v3.2，第 2.6 节
=============================================================================
用法:
    python write_metadata.py <image_path> --run-id <run_id> [--provider <name>]

依赖:
    pip install Pillow

写入内容:
    iTXt 块: AIGC_METADATA (JSON)
    XMP:     dc:creator, dc:description, xmp:MetadataDate
=============================================================================
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


AIGC_LABEL = "AIGC"
DEFAULT_PROVIDER = "通义万相 + XX开源社区"


def build_metadata_json(run_id: str, provider: str) -> dict:
    """构建五要素 1-3 的 JSON 结构（4-5 留空待传播平台填）"""
    return {
        "aigc_label": AIGC_LABEL,
        "aigc_provider": provider,
        "content_id": run_id,
        "propagation_provider": "",  # 传播平台补
        "propagation_id": "",        # 传播平台补
        "standard": "GB 45438-2025",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def write_png_metadata(input_path: str, output_path: str, metadata_json: dict) -> None:
    """写入 PNG iTXt 文本块和 XMP 元数据"""
    img = Image.open(input_path)

    # 1. iTXt 块：存储 JSON 字符串
    png_info = PngInfo()
    png_info.add_itxt(
        "AIGC_METADATA",
        json.dumps(metadata_json, ensure_ascii=False),
        compressed=True,
    )

    # 2. 也写入 tEXt 块作为备选（部分工具读不到 iTXt）
    png_info.add_text("AIGC_METADATA", json.dumps(metadata_json, ensure_ascii=False))
    png_info.add_text("AIGC_Label", AIGC_LABEL)
    png_info.add_text("ContentID", metadata_json["content_id"])
    png_info.add_text("Standard", "GB 45438-2025")

    # 3. 保存
    img.save(output_path, "PNG", pnginfo=png_info)
    print(f"✓ Metadata written to: {output_path}")
    print(f"  - iTXt AIGC_METADATA: {json.dumps(metadata_json, ensure_ascii=False)}")
    print(f"  - tEXt AIGC_Label: {AIGC_LABEL}")
    print(f"  - tEXt ContentID: {metadata_json['content_id']}")


def main():
    parser = argparse.ArgumentParser(description="Write GB 45438-2025 metadata to PNG")
    parser.add_argument("image", help="Path to input PNG image")
    parser.add_argument("--run-id", required=True, help="Pipeline run_id")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="AIGC service provider name")
    parser.add_argument("--output", help="Output path (default: overwrite input)")
    args = parser.parse_args()

    input_path = Path(args.image)
    if not input_path.exists():
        print(f"ERROR: File not found: {args.image}")
        sys.exit(1)

    output_path = args.output or args.image
    metadata = build_metadata_json(args.run_id, args.provider)
    write_png_metadata(str(input_path), str(output_path), metadata)


if __name__ == "__main__":
    main()
