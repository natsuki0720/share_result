#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py — result/ 以下を走査して index.json を生成

既定の想定構成:
  result/
    result_en/html/video{n}/case{m}.html (または case{mm}.html)
    result_ja/html/video{n}/case{m}.html (または case{mm}.html)

使い方:
  python scripts/build_index.py \
    --root . \
    --base-en result/result_en/html \
    --base-ja result/result_ja/html \
    --out result/index.json
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from datetime import datetime, timezone

VIDEO_DIR_RE = re.compile(r"video(\d+)$")
CASE_FILE_RE = re.compile(r"case(\d+)\.html$", re.IGNORECASE)

def scan_language(base_dir: Path) -> dict[int, list[dict]]:
    """
    指定言語の base_dir を走査し、{video番号: [ {case, filename, relpath} ]} を返す
    """
    out: dict[int, list[dict]] = {}
    if not base_dir.exists():
        return out

    # videoX ディレクトリを列挙
    for video_dir in sorted(base_dir.glob("video*")):
        if not video_dir.is_dir():
            continue
        m_video = VIDEO_DIR_RE.search(video_dir.name)
        if not m_video:
            continue
        vnum = int(m_video.group(1))

        cases = []
        # case*.html を列挙（case1.html / case01.html の両方を拾う）
        for html in sorted(video_dir.glob("case*.html")):
            if not html.is_file():
                continue
            m_case = CASE_FILE_RE.search(html.name)
            if not m_case:
                continue
            case_num = int(m_case.group(1))   # 数値として扱ってソートしやすく
            rel = html.relative_to(base_dir.parent.parent).as_posix()
            cases.append({
                "case": case_num,
                "filename": html.name,
                "relpath": rel,   # リポジトリルートからの相対
            })

        # case が一つでもあれば登録
        if cases:
            # case番号で昇順ソート
            cases.sort(key=lambda x: x["case"])
            out[vnum] = cases

    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="リポジトリのルート（相対パス基準）")
    ap.add_argument("--base-en", default="result/result_en/html", help="英語ページのベースディレクトリ")
    ap.add_argument("--base-ja", default="result/result_ja/html", help="日本語ページのベースディレクトリ")
    ap.add_argument("--out", default="result/index.json", help="出力する index.json のパス")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    base_en = (root / args.base_en).resolve()
    base_ja = (root / args.base_ja).resolve()
    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    en_map = scan_language(base_en)
    ja_map = scan_language(base_ja)

    # 出力スキーマ（シンプル & 検索しやすい）
    # videos.<lang> は { video番号: [ {case, filename, relpath} ] } 形式
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": {
            "en": Path(args.base_en).as_posix(),
            "ja": Path(args.base_ja).as_posix(),
        },
        "counts": {
            "en": sum(len(v) for v in en_map.values()),
            "ja": sum(len(v) for v in ja_map.values()),
        },
        "videos": {
            "en": {str(k): v for k, v in sorted(en_map.items())},
            "ja": {str(k): v for k, v in sorted(ja_map.items())},
        },
    }

    # JSON を整形出力
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
