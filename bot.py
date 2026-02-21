import os
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

from PIL import Image, ImageDraw, ImageFont

# --- НАСТРОЙКИ ---
BOT_TOKEN = "7949631331:AAGdKHx_9hxXAgpDsQh68qbcCKboM0brHOE"

# Состояния диалога
WAIT_IMAGE, WAIT_TEXT1, WAIT_TEXT2 = range(3)

# Шрифт (если нет кастомного — используем стандартный)
FONT_PATH = None  # Можно указать путь к .ttf файлу, например "arial.ttf"


def add_text_to_image(image_bytes: bytes, text: str, position: str = "bottom") -> bytes:
    """Добавляет текст на картинку и возвращает bytes."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    width, height = img.size
    
    # Размер шрифта относительно картинки
    font_size = max(30, width // 20)
    
    try:
        if FONT_PATH and os.path.exists(FONT_PATH):
            font = ImageFont.truetype(FONT_PATH, font_size)
        else:
            # Попробуем найти системный шрифт
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Позиция текста
    x = (width - text_width) // 2  # по центру
    padding = 30
    
    if position == "bottom":
        y = height - text_height - padding
    elif position == "top":
        y = padding
    else:  # center
        y = (height - text_height) // 2

    # Тень / обводка для читаемости
    shadow_offset = max(2, font_size // 15)
    for dx in [-shadow_offset, 0, shadow_offset]:
        for dy in [-shadow_offset, 0, shadow_offset]:
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 200))

    # Основной текст белым
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    # Конвертируем в RGB для JPEG
    output = io.BytesIO()
    img.convert("RGB").save(output, format="JPEG", quality=95)
    return output.getvalue()


# --- ХЕНДЛЕРЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я создаю картинки с текстом.\n\n"
        "📸 Отправь мне картинку чтобы начать"
    )
    return WAIT_IMAGE


async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Отправь картинку!")
        return WAIT_IMAGE

    # Сохраняем картинку
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    else:
        file = await update.message.document.get_file()
    
    image_bytes = await file.download_as_bytearray()
    context.user_data["image"] = bytes(image_bytes)

    await update.message.reply_text(
        "✅ Картинка получена!\n\n"
        "📝 Теперь отправь текст для **первой картинки**\n"
        "(например: `этот трек>>>` или любой другой)",
        parse_mode="Markdown"
    )
    return WAIT_TEXT1


async def receive_text1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["text1"] = update.message.text
    
    await update.message.reply_text(
        "✅ Принято!\n\n"
        "🎵 Теперь отправь текст для **второй картинки** (текст трека)"
    )
    return WAIT_TEXT2


async def receive_text2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text2 = update.message.text
    image = context.user_data["image"]
    text1 = context.user_data["text1"]

    await update.message.reply_text("⏳ Создаю картинки...")

    try:
        # Первая картинка — текст внизу (например "этот трек>>>")
        img1_bytes = add_text_to_image(image, text1, position="bottom")
        
        # Вторая картинка — текст по центру (текст трека)
        img2_bytes = add_text_to_image(image, text2, position="center")

        # Отправляем обе картинки
        await update.message.reply_photo(
            photo=io.BytesIO(img1_bytes),
            caption=f"🖼 Картинка 1: «{text1}»"
        )
        await update.message.reply_photo(
            photo=io.BytesIO(img2_bytes),
            caption=f"🎵 Картинка 2: текст трека"
        )

        await update.message.reply_text(
            "✅ Готово! Хочешь ещё раз? Отправь новую картинку 📸"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

    # Очищаем данные
    context.user_data.clear()
    return WAIT_IMAGE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено. Отправь /start чтобы начать заново")
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_image)
        ],
        states={
            WAIT_IMAGE: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_image)],
            WAIT_TEXT1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text1)],
            WAIT_TEXT2: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text2)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    
    print("🤖 Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
