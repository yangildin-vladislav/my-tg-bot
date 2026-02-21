import os
import io
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────
BOT_TOKEN = "7949631331:AAGdKHx_9hxXAgpDsQh68qbcCKboM0brHOE"
TEMPLATE_FILE = "template.json"

# ─── СОСТОЯНИЯ ───────────────────────────
(
    WAIT_IMAGE,
    WAIT_TEXT1,
    WAIT_TEXT2,
    CHOOSE_FONT,
    CHOOSE_SIZE,
) = range(5)

# ─── ШРИФТЫ ──────────────────────────────
FONTS = {
    "Classic":     "fonts/ProximaNova-Bold.ttf",
    "Typewriter":  "fonts/CourierPrime-Bold.ttf",
    "Neon":        "fonts/Orbitron-Bold.ttf",
    "Serif":       "fonts/PlayfairDisplay-Bold.ttf",
    "Handwriting": "fonts/DancingScript-Bold.ttf",
}

FONT_LABELS = {
    "Classic":     "Classic — чистый и современный",
    "Typewriter":  "Typewriter — печатная машинка",
    "Neon":        "Neon — неон / глоу эффект",
    "Serif":       "Serif — классика с засечками",
    "Handwriting": "Handwriting — рукописный",
}

SIZES = {
    "S":  0.03,
    "M":  0.05,
    "L":  0.07,
    "XL": 0.10,
}

# ─── ШАБЛОН ──────────────────────────────
def load_template() -> dict:
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_template(data: dict):
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── РЕНДЕР ──────────────────────────────
def get_font(font_name: str, size: int):
    path = FONTS.get(font_name)
    try:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
        for fallback in [
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]:
            if os.path.exists(fallback):
                return ImageFont.truetype(fallback, size)
    except Exception:
        pass
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def render_image(image_bytes, text, font_name, size_key, neon=False):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font_size = max(20, int(h * SIZES.get(size_key, 0.05)))
    font = get_font(font_name, font_size)

    lines = wrap_text(draw, text, font, int(w * 0.9))
    line_height = font_size + int(font_size * 0.3)
    total_h = line_height * len(lines)

    # Всегда по центру
    y_start = (h - total_h) // 2
    shadow = max(2, font_size // 12)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        y = y_start + i * line_height

        if neon:
            for spread in [8, 5, 3]:
                for dx in range(-spread, spread + 1, 2):
                    for dy in range(-spread, spread + 1, 2):
                        draw.text((x + dx, y + dy), line, font=font, fill=(0, 200, 255, 80))
            draw.text((x, y), line, font=font, fill=(180, 255, 255, 255))
        else:
            for dx in [-shadow, 0, shadow]:
                for dy in [-shadow, 0, shadow]:
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 200))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=95)
    return out.getvalue()


# ─── КЛАВИАТУРЫ ──────────────────────────
def font_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(FONT_LABELS[f], callback_data=f"font_{f}")]
        for f in FONTS
    ])

def size_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("S — мелкий",    callback_data="size_S"),
        InlineKeyboardButton("M — средний",   callback_data="size_M"),
    ],[
        InlineKeyboardButton("L — крупный",   callback_data="size_L"),
        InlineKeyboardButton("XL — огромный", callback_data="size_XL"),
    ]])


# ─── ХЕНДЛЕРЫ ────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tmpl = load_template()
    if tmpl:
        await update.message.reply_text(
            "👋 Привет!\n\n"
            f"📋 Активный шаблон:\n"
            f"  • Шрифт: {tmpl.get('font','?')}\n"
            f"  • Размер: {tmpl.get('size','?')}\n"
            f"  • Текст 1: {tmpl.get('text1','?')}\n"
            f"  • Текст 2: {tmpl.get('text2','?')}\n\n"
            "📸 Просто кидай картинку — сразу получишь обе фотки!\n"
            "/newtemplate — изменить шаблон"
        )
    else:
        await update.message.reply_text(
            "👋 Привет!\n\n"
            "📸 Кидай картинку чтобы начать\n"
            "Один раз настроишь шаблон — потом просто кидай фото!"
        )
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
        # Шаблон есть — сразу делаем обе картинки без вопросов
        await update.message.reply_text("⏳ Применяю шаблон...")
        await generate_and_send(update, context, tmpl["text2"], tmpl)
        context.user_data.clear()
        return WAIT_IMAGE

    # Нет шаблона — начинаем настройку
    await update.message.reply_text("✅ Картинка получена!\n\n🎨 Выбери шрифт:", reply_markup=font_keyboard())
    return CHOOSE_FONT


async def choose_font(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["font"] = query.data.replace("font_", "")
    await query.edit_message_text(
        f"✅ Шрифт: {context.user_data['font']}\n\n📏 Выбери размер текста:",
        reply_markup=size_keyboard()
    )
    return CHOOSE_SIZE


async def choose_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["size"] = query.data.replace("size_", "")
    await query.edit_message_text(
        f"✅ Размер: {context.user_data['size']}\n\n"
        "📝 Отправь текст для первой картинки\n_(например: `этот трек>>>`)_",
        parse_mode="Markdown"
    )
    return WAIT_TEXT1


async def receive_text1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["text1"] = update.message.text
    await update.message.reply_text("✅ Принято!\n\n🎵 Теперь отправь текст трека для второй картинки")
    return WAIT_TEXT2


async def receive_text2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text2 = update.message.text
    ud = context.user_data

    settings = {
        "font":  ud.get("font", "Classic"),
        "size":  ud.get("size", "M"),
        "text1": ud.get("text1", "этот трек>>>"),
        "text2": text2,
    }

    await update.message.reply_text("⏳ Создаю картинки...")
    await generate_and_send(update, context, text2, settings)

    save_template(settings)
    await update.message.reply_text(
        "✅ Готово! Шаблон сохранён 🔖\n\n"
        "Теперь просто кидай картинку — сразу получишь обе фотки!\n"
        "/newtemplate — изменить шаблон"
    )
    context.user_data.clear()
    return WAIT_IMAGE


async def generate_and_send(update, context, text2, settings):
    """Генерирует и отправляет обе картинки."""
    image   = context.user_data["image"]
    font    = settings["font"]
    size    = settings["size"]
    text1   = settings["text1"]
    is_neon = (font == "Neon")

    try:
        img1 = render_image(image, text1, font, size, neon=is_neon)
        img2 = render_image(image, text2, font, size, neon=is_neon)
        await update.message.reply_document(document=io.BytesIO(img1), filename="track_1.jpg", caption=f"🖼 «{text1}»")
        await update.message.reply_document(document=io.BytesIO(img2), filename="track_2.jpg", caption="🎵 Текст трека")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено. /start чтобы начать")
    return ConversationHandler.END


# ─── MAIN ────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("newtemplate", new_template),
            MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_image),
        ],
        states={
            WAIT_IMAGE:  [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_image),
                CommandHandler("newtemplate", new_template),
            ],
            CHOOSE_FONT: [CallbackQueryHandler(choose_font, pattern="^font_")],
            CHOOSE_SIZE: [CallbackQueryHandler(choose_size, pattern="^size_")],
            WAIT_TEXT1:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text1)],
            WAIT_TEXT2:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text2)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
