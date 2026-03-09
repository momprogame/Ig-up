import os
import asyncio
from pyrogram import Client, filters
from instagrapi import Client as InstaClient
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

# Variables de entorno
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
AUTHORIZED_USERS_FILE = "authorized_users.txt"
CAPTION_FILE = "caption.txt"
DEFAULT_LANGUAGE = "en"

# Verificar variables
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
    print("❌ Error: Faltan variables de entorno")
    exit(1)

# Login en Instagram
try:
    insta_client = InstaClient()
    insta_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
    print(f"✅ Login exitoso en Instagram como {INSTAGRAM_USERNAME}")
except Exception as e:
    print(f"❌ Error en login de Instagram: {e}")
    exit(1)

# Cliente de Telegram
app = Client(
    "my_bot",
    api_id=int(TELEGRAM_API_ID),
    api_hash=TELEGRAM_API_HASH,
    bot_token=TELEGRAM_BOT_TOKEN
)

# Menús
main_menu_en = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📤 Upload a Reels")],
        [KeyboardButton("📤 Upload Multiple Reels")]
    ],
    resize_keyboard=True
)

main_menu_fa = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📤 ارسال یک Reels")],
        [KeyboardButton("📤 ارسال چند Reels همزمان")]
    ],
    resize_keyboard=True
)

# Funciones de idioma
def save_language(user_id, language):
    try:
        with open("languages.txt", "a") as file:
            file.write(f"{user_id}:{language}\n")
    except Exception as e:
        print(f"Error saving language: {e}")

def get_language(user_id):
    try:
        with open("languages.txt", "r") as file:
            lines = file.readlines()
            for line in lines:
                uid, lang = line.strip().split(":")
                if uid == str(user_id):
                    return lang
    except FileNotFoundError:
        return DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE

# Función de autorización
def is_authorized(user_id):
    try:
        with open(AUTHORIZED_USERS_FILE, "r") as file:
            authorized = [line.strip() for line in file.readlines()]
        return str(user_id) in authorized
    except:
        return False

# Handlers
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        await message.reply(f"⛔ No autorizado. Tu ID: {user_id}")
        return
    
    language = get_language(user_id)
    
    if language == "fa":
        await message.reply(
            "👋 به ربات خوش آمدید!\nبرای آپلود یک Reels یا چند Reels همزمان، روی دکمه‌های زیر کلیک کنید.",
            reply_markup=main_menu_fa
        )
    else:
        await message.reply(
            "👋 Welcome to the bot!\nClick on the buttons below to upload a Reels or multiple Reels at once.",
            reply_markup=main_menu_en
        )

@app.on_message(filters.text & filters.regex("^📤 Upload a Reels$"))
async def request_single_reels_en(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply("🎥 Please send your video.")

@app.on_message(filters.text & filters.regex("^📤 ارسال یک Reels$"))
async def request_single_reels_fa(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply("🎥 لطفاً فیلم خود را ارسال کنید.")

@app.on_message(filters.text & filters.regex("^📤 Upload Multiple Reels$"))
async def request_multiple_reels_en(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply("🎥 Please send your videos. The bot will upload them one by one with a 30-second gap.")

@app.on_message(filters.text & filters.regex("^📤 ارسال چند Reels همزمان$"))
async def request_multiple_reels_fa(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply("🎥 لطفاً چند ویدئوی خود را ارسال کنید.")

@app.on_message(filters.video)
async def upload_reels(client, message):
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        return
    
    language = get_language(user_id)
    
    try:
        # Descargar video
        video_path = await message.download()
        
        # Leer caption
        try:
            with open(CAPTION_FILE, "r", encoding="utf-8") as file:
                caption = file.read().strip()
        except:
            caption = "Video uploaded from Telegram"
        
        # Subir a Instagram
        await message.reply("🔄 Subiendo a Instagram...")
        
        insta_client.clip_upload(video_path, caption)
        
        # Mensaje de éxito
        if language == "fa":
            await message.reply("✅ فیلم با موفقیت به عنوان Reels در اینستاگرام پست شد.")
        else:
            await message.reply("✅ The video was successfully uploaded as a Reels on Instagram.")
        
        # Esperar 30 segundos para el próximo video
        await asyncio.sleep(30)
        
    except Exception as e:
        if language == "fa":
            await message.reply(f"⚠️ خطا: {str(e)[:100]}")
        else:
            await message.reply(f"⚠️ Error: {str(e)[:100]}")

if __name__ == "__main__":
    print("🚀 Bot iniciado!")
    app.run()
