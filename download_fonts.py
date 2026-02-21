#!/usr/bin/env python3
"""Скачивает шрифты с поддержкой кириллицы."""
import os
import urllib.request

os.makedirs("fonts", exist_ok=True)

FONTS = {
    "fonts/Classic.ttf":
        "https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf",
    "fonts/Typewriter.ttf":
        "https://github.com/google/fonts/raw/main/ofl/courierPrime/CourierPrime-Regular.ttf",
    "fonts/Neon.ttf":
        "https://github.com/google/fonts/raw/main/ofl/russoto/Russo_One.ttf",
    "fonts/Serif.ttf":
        "https://github.com/google/fonts/raw/main/ofl/ptsserif/PTSerif-Regular.ttf",
    "fonts/Handwriting.ttf":
        "https://github.com/google/fonts/raw/main/ofl/marckscript/MarckScript-Regular.ttf",
}

for path, url in FONTS.items():
    if os.path.exists(path):
        print(f"✅ Уже есть: {path}")
        continue
    print(f"⬇️  Скачиваю {path}...")
    try:
        urllib.request.urlretrieve(url, path)
        print(f"✅ OK: {path}")
    except Exception as e:
        print(f"❌ Ошибка {path}: {e}")

print("\n🎉 Шрифты готовы!")
