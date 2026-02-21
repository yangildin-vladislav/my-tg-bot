import os
import io
import json
import urllib.request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = "7949631331:AAGdKHx_9hxXAgpDsQh68qbcCKboM0brHOE"
TEMPLATE_FILE = "template.json"

(WAIT_IMAGE, WAIT_FONT, WAIT_SIZE, WAIT_TEXT1, WAIT_TEXT2) = range(5)

# Один универсальный шрифт с кириллицей для всех стилей
# Скачивается автоматически при старте
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/opensans/OpenSans%5Bwdth%2Cwght%5D.ttf"
FONT_PATH = "fonts/OpenSans.ttf"

FONT_MENU = (
    "🎨 Выбери стиль — отправь цифру:\n\n"
    "1 — Обычный\n"
    "2 — Жирный (bold эффект через тень)\n"
    "3 — Неон (голубое свечение)\n"
    "4 — Тень снизу\n"
    "5 — Белый с чёрной обводкой"
)

SIZE_MENU = (
    "📏 Отправь размер шрифта числом:\n\n"
    "60  — мелкий\n"
    "100 — средний\n"
    "150 — крупный\n"
    "200 — очень крупный\n\n"
    "Напиши любое число от 20 до 400"
)


def ensure_font():
    """Скачивает шрифт если его нет."""
    os.makedirs("fonts", exist_ok=True)
    if not os.path.exists(FONT_PATH):
        print("⬇️ Скачиваю шрифт...")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        print("✅ Шрифт скачан!")


def get_font(size):
    try:
        if os.path.exists(FONT_PATH):
            return ImageFont.truetype(FONT_PATH, size)
        for fallback in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]:
            if os.path.exists(fallback):
                return ImageFont.truetype(fallback, size)
    except Exception as e:
        print(f"Ошибка шрифта: {e}")
    return ImageFont.load_default()


def load_template():
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_template(data):
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def wrap_text(draw, text, font, max_width):
    """Поддерживает переносы через Enter и автоперенос длинных строк."""
    result = []
    # Сначала разбиваем по энтерам
    for paragraph in text.split("\n"):
        if paragraph.strip() == "":
            result.append("")  # пустая строка сохраняется
            continue
        # Внутри каждого абзаца — автоперенос по ширине
        words = paragraph.split()
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                current = test
            else:
                if current:
                    result.append(current)
                current = word
        if current:
            result.append(current)
    return result or [""]


def render_image(image_bytes, text, style, font_size):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font = get_font(font_size)
    lines = wrap_text(draw, text, font, int(w * 0.88))
    line_height = int(font_size * 1.4)
    total_h = line_height * len(lines)
    y_start = (h - total_h) // 2

    for i, line in enumerate(lines):
        y = y_start + i * line_height
        if line == "": continue
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2

        if style == "1":  # Обычный — белый с тёмной тенью
            s = max(3, font_size // 15)
            draw.text((x+s, y+s), line, font=font, fill=(0, 0, 0, 180))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

        elif style == "2":  # Жирный — многослойная тень
            for d in range(4, 0, -1):
                draw.text((x+d, y+d), line, font=font, fill=(0, 0, 0, 120))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

        elif style == "3":  # Неон
            for spread in [12, 8, 4]:
                for dx in range(-spread, spread+1, 2):
                    for dy in range(-spread, spread+1, 2):
                        draw.text((x+dx, y+dy), line, font=font, fill=(0, 200, 255, 60))
            draw.text((x, y), line, font=font, fill=(200, 255, 255, 255))

        elif style == "4":  # Тень снизу-справа
            s = max(4, font_size // 10)
            draw.text((x+s, y+s), line, font=font, fill=(0, 0, 0, 200))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

        elif style == "5":  # Чёрная обводка
            s = max(3, font_size // 20)
            for dx in range(-s, s+1):
                for dy in range(-s, s+1):
                    if abs(dx) == s or abs(dy) == s:
                        draw.text((x+dx, y+dy), line, font=font, fill=(0, 0, 0, 255))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=95)
    return out.getvalue()


async def generate_and_send(update, context, settings):
    image     = context.user_data["image"]
    style     = settings["style"]
    font_size = int(settings["font_size"])
    text1     = settings["text1"]
    text2     = settings["text2"]
    try:
        img1 = render_image(image, text1, style, font_size)
        img2 = render_image(image, text2, style, font_size)
        await update.message.reply_document(io.BytesIO(img1), filename="track_1.jpg", caption=f"🖼 {text1}")
        await update.message.reply_document(io.BytesIO(img2), filename="track_2.jpg", caption="🎵 Текст трека")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tmpl = load_template()
    style_names = {"1":"Обычный","2":"Жирный","3":"Неон","4":"Тень","5":"Обводка"}
    if tmpl:
        await update.message.reply_text(
            "👋 Привет!\n\n"
            f"📋 Активный шаблон:\n"
            f"  • Стиль: {style_names.get(tmpl.get('style','1'), '?')}\n"
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
    if txt not in ["1","2","3","4","5"]:
        await update.message.reply_text("Отправь цифру от 1 до 5 👆")
        return WAIT_FONT
    context.user_data["style"] = txt
    styles = {"1":"Обычный","2":"Жирный","3":"Неон","4":"Тень","5":"Обводка"}
    await update.message.reply_text(f"✅ Стиль: {styles[txt]}\n\n{SIZE_MENU}")
    return WAIT_SIZE


async def receive_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    try:
        size = int(txt)
        if size < 20 or size > 400:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Напиши число от 20 до 400\nНапример: 100")
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
        "style":     ud.get("style", "1"),
        "font_size": ud.get("font_size", 100),
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
    ensure_font()  # Скачиваем шрифт при старте
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
