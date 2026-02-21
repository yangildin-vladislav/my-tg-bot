#!/usr/bin/env python3
"""
Скачивает шрифты TikTok-стилей с Google Fonts.
Запусти один раз: python3 download_fonts.py
"""
import os
import urllib.request

os.makedirs("fonts", exist_ok=True)

FONTS = {
    # Classic (Proxima Nova недоступна бесплатно, берём Nunito Bold — очень похоже)
    "fonts/ProximaNova-Bold.ttf": 
        "https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf",
    # Typewriter
    "fonts/CourierPrime-Bold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/courierprime/CourierPrime-Bold.ttf",
    # Neon (Orbitron)
    "fonts/Orbitron-Bold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf",
    # Serif
    "fonts/PlayfairDisplay-Bold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    # Handwriting
    "fonts/DancingScript-Bold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/dancingscript/DancingScript%5Bwght%5D.ttf",
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

print("\n🎉 Готово! Теперь запускай bot.py")
