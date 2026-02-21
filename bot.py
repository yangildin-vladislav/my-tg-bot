import os
import io
import json
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = "7949631331:AAGdKHx_9hxXAgpDsQh68qbcCKboM0brHOE"
TEMPLATE_FILE = "template.json"

(WAIT_IMAGE, WAIT_FONT, WAIT_SIZE, WAIT_TEXT1, WAIT_TEXT2) = range(5)

# Все шрифты с поддержкой кириллиц
FONTS = {
    "1": ("Classic",     "fonts/Classic.ttf"),
    "2": ("Typewriter",  "fonts/Typewriter.ttf"),
    "3": ("Neon",        "fonts/Neon.ttf"),
    "4": ("Serif",       "fonts/Serif.ttf"),
    "5": ("Handwriting", "fonts/Handwriting.ttf"),
}

FONT_MENU = (
    "🎨 Выбери шрифт — отправь цифру:\n\n"
    "1 — Classic (чистый, современный)\n"
    "2 — Typewriter (печатная машинка)\n"
    "3 — Neon (жирный, акцентный)\n"
    "4 — Serif (классика с засечками)\n"
    "5 — Handwriting (рукописный)"
)

SIZE_MENU = (
    "📏 Отправь размер шрифта числом\n\n"
    "Ориентир:\n"
    "40 — мелкий\n"
    "80 — средний\n"
    "120 — крупный\n"
    "180 — очень крупный\n\n"
    "Можешь написать любое число!"
)


def load_template():
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_template(data):
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_font(font_name, size):
    paths = {
        "Classic":     "fonts/Classic.ttf",
        "Typewriter":  "fonts/Typewriter.ttf",
        "Neon":        "fonts/Neon.ttf",
        "Serif":       "fonts/Serif.ttf",
        "Handwriting": "fonts/Handwriting.ttf",
    }
    try:
        p = paths.get(font_name, "")
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
        # Фолбэк — ищем любой системный шрифт с кириллицей
        for fallback in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            if os.path.exists(fallback):
                return ImageFont.truetype(fallback, size)
    except Exception:
        pass
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    # Разбиваем по словам, поддержка кириллицы через split()
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def render_image(image_bytes, text, font_name, font_size, neon=False):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font = get_font(font_name, font_size)
    lines = wrap_text(draw, text, font, int(w * 0.9))
    line_height = font_size + int(font_size * 0.3)
    total_h = line_height * len(lines)
    y_start = (h - total_h) // 2
    shadow = max(2, font_size // 12)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        y = y_start + i * line_height

        if neon:
            for spread in [10, 6, 3]:
                for dx in range(-spread, spread + 1, 2):
                    for dy in range(-spread, spread + 1, 2):
                        draw.text((x+dx, y+dy), line, font=font, fill=(0, 200, 255, 70))
            draw.text((x, y), line, font=font, fill=(180, 255, 255, 255))
        else:
            for dx in [-shadow, 0, shadow]:
                for dy in [-shadow, 0, shadow]:
                    if dx != 0 or dy != 0:
                        draw.text((x+dx, y+dy), line, font=font, fill=(0, 0, 0, 220))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=95)
    return out.getvalue()


async def generate_and_send(update, context, settings):
    image     = context.user_data["image"]
    font_name = settings["font"]
    font_size = settings["font_size"]
    text1     = settings["text1"]
    text2     = settings["text2"]
    neon      = (font_name == "Neon")
    try:
        img1 = render_image(image, text1, font_name, font_size, neon=neon)
        img2 = render_image(image, text2, font_name, font_size, neon=neon)
        await update.message.reply_document(io.BytesIO(img1), filename="track_1.jpg", caption=f"🖼 {text1}")
        await update.message.reply_document(io.BytesIO(img2), filename="track_2.jpg", caption="🎵 Текст трека")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tmpl = load_template()
    if tmpl:
        await update.message.reply_text(
            "👋 Привет!\n\n"
            f"📋 Активный шаблон:\n"
            f"  • Шрифт: {tmpl.get('font')}\n"
            f"  • Размер: {tmpl.get('font_size')}\n"
            f"  • Текст 1: {tmpl.get('text1')}\n"
            f"  • Текст 2: {tmpl.get('text2')}\n\n"
            "📸 Кидай картинку — сразу получишь обе фотки!\n"
            "/newtemplate — изменить шаблон"
        )
    else:
        await update.message.reply_text("👋 Привет!\n\n📸 Кидай картинку чтобы начать!")
    return WAIT_IMAGE


async def new_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(TEMPLATE_FILE):
        os.remove(TEMPLATE_FILE)
    context.user_data.clear()
    await update.message.reply_text("🗑 Шаблон сброшен!\n\n📸 Кидай картинку чтобы настроить заново")
    return WAIT_IMAGE


async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document:
        file = await update.message.document.get_file()
    else:
        await update.message.reply_text("Отправь картинку!")
        return WAIT_IMAGE

    context.user_data["image"] = bytes(await file.download_as_bytearray())

    tmpl = load_template()
    if tmpl:
        await update.message.reply_text("⏳ Применяю шаблон...")
        await generate_and_send(update, context, tmpl)
        context.user_data.clear()
        return WAIT_IMAGE

    await update.message.reply_text(FONT_MENU)
    return WAIT_FONT


async def receive_font(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt not in FONTS:
        await update.message.reply_text("Отправь цифру от 1 до 5 👆")
        return WAIT_FONT
    name, _ = FONTS[txt]
    context.user_data["font"] = name
    await update.message.reply_text(f"✅ Шрифт: {name}\n\n{SIZE_MENU}")
    return WAIT_SIZE


async def receive_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    try:
        size = int(txt)
        if size < 10 or size > 500:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Отправь число от 10 до 500\nНапример: 80")
        return WAIT_SIZE

    context.user_data["font_size"] = size
    await update.message.reply_text(
        f"✅ Размер: {size}\n\n"
        "📝 Отправь текст для первой картинки\n(например: этот трек>>>)"
    )
    return WAIT_TEXT1


async def receive_text1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["text1"] = update.message.text
    await update.message.reply_text("✅ Принято!\n\n🎵 Теперь отправь текст трека для второй картинки")
    return WAIT_TEXT2


async def receive_text2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    settings = {
        "font":      ud.get("font", "Classic"),
        "font_size": ud.get("font_size", 80),
        "text1":     ud.get("text1", "этот трек>>>"),
        "text2":     update.message.text,
    }
    await update.message.reply_text("⏳ Создаю картинки...")
    await generate_and_send(update, context, settings)
    save_template(settings)
    await update.message.reply_text(
        "✅ Готово! Шаблон сохранён 🔖\n\n"
        "Теперь просто кидай картинку!\n"
        "/newtemplate — изменить шаблон"
    )
    context.user_data.clear()
    return WAIT_IMAGE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено. /start чтобы начать")
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("newtemplate", new_template),
            MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_image),
        ],
        states={
            WAIT_IMAGE: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_image),
                CommandHandler("newtemplate", new_template),
            ],
            WAIT_FONT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_font)],
            WAIT_SIZE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_size)],
            WAIT_TEXT1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text1)],
            WAIT_TEXT2: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text2)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
