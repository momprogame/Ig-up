import os
import asyncio
from pyrogram import Client, filters
from instagrapi import Client as InstaClient
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, ForceReply

# Variables de entorno
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
INSTAGRAM_USUARIO = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_CONTRASENA = os.getenv('INSTAGRAM_PASSWORD')
ARCHIVO_USUARIOS_AUTORIZADOS = "authorized_users.txt"
ARCHIVO_CAPTION = "caption.txt"
IDIOMA_PREDETERMINADO = "es"

# Diccionario para almacenar datos temporales de usuarios
# {user_id: {'esperando': 'caption', 'ruta_video': 'ruta', 'multiple': False}}
datos_usuario = {}

# Verificar variables
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, INSTAGRAM_USUARIO, INSTAGRAM_CONTRASENA]):
    print("❌ Error: Faltan variables de entorno")
    exit(1)

# Login en Instagram
try:
    cliente_insta = InstaClient()
    cliente_insta.login(INSTAGRAM_USUARIO, INSTAGRAM_CONTRASENA)
    print(f"✅ Login exitoso en Instagram como {INSTAGRAM_USUARIO}")
except Exception as e:
    print(f"❌ Error en login de Instagram: {e}")
    exit(1)

# Cliente de Telegram
app = Client(
    "mi_bot",
    api_id=int(TELEGRAM_API_ID),
    api_hash=TELEGRAM_API_HASH,
    bot_token=TELEGRAM_BOT_TOKEN
)

# Menú principal
menu_principal = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📤 Subir un Reels")],
        [KeyboardButton("📤 Subir Múltiples Reels")],
        [KeyboardButton("📝 Cambiar Caption por Defecto")]
    ],
    resize_keyboard=True
)

# Función de autorización
def esta_autorizado(user_id):
    try:
        with open(ARCHIVO_USUARIOS_AUTORIZADOS, "r") as file:
            autorizados = [linea.strip() for linea in file.readlines()]
        return str(user_id) in autorizados
    except:
        return False

# Función para leer caption por defecto
def obtener_caption_defecto():
    try:
        with open(ARCHIVO_CAPTION, "r", encoding="utf-8") as file:
            return file.read().strip()
    except:
        return "Video subido desde Telegram"

# Función para guardar caption por defecto
def guardar_caption_defecto(caption):
    try:
        with open(ARCHIVO_CAPTION, "w", encoding="utf-8") as file:
            file.write(caption)
        return True
    except:
        return False

# Handlers
@app.on_message(filters.command("start"))
async def inicio(client, message):
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        await message.reply(f"⛔ No autorizado. Tu ID: {user_id}")
        return
    
    await message.reply(
        "👋 ¡Bienvenido al bot!\n\n"
        "Presiona los botones para subir Reels a Instagram:\n"
        "• 📤 Subir un Reels - Sube un video individual\n"
        "• 📤 Subir Múltiples Reels - Sube varios videos\n"
        "• 📝 Cambiar Caption por Defecto - Cambia el texto por defecto",
        reply_markup=menu_principal
    )

@app.on_message(filters.text & filters.regex("^📤 Subir un Reels$"))
async def solicitar_video_unico(client, message):
    user_id = message.from_user.id
    if not esta_autorizado(user_id):
        return
    
    datos_usuario[user_id] = {'esperando': 'video', 'multiple': False}
    
    await message.reply(
        "🎥 Por favor, envía el video que quieres subir como Reel.\n\n"
        "Después de enviar el video, te pediré la caption.",
        reply_markup=ForceReply(selective=True)
    )

@app.on_message(filters.text & filters.regex("^📤 Subir Múltiples Reels$"))
async def solicitar_videos_multiples(client, message):
    user_id = message.from_user.id
    if not esta_autorizado(user_id):
        return
    
    datos_usuario[user_id] = {'esperando': 'videos', 'multiple': True, 'videos': []}
    
    await message.reply(
        "🎥 Envía los videos uno por uno.\n"
        "Escribe /listo cuando termines de enviar todos los videos.\n"
        "Después te pediré la caption para todos.",
        reply_markup=ForceReply(selective=True)
    )

@app.on_message(filters.text & filters.regex("^📝 Cambiar Caption por Defecto$"))
async def cambiar_caption_defecto(client, message):
    user_id = message.from_user.id
    if not esta_autorizado(user_id):
        return
    
    datos_usuario[user_id] = {'esperando': 'caption_defecto'}
    
    actual = obtener_caption_defecto()
    await message.reply(
        f"📝 Caption actual por defecto:\n{actual}\n\n"
        f"Envía la nueva caption por defecto:",
        reply_markup=ForceReply(selective=True)
    )

@app.on_message(filters.command("listo"))
async def listo_multiples(client, message):
    user_id = message.from_user.id
    
    if user_id in datos_usuario and datos_usuario[user_id].get('esperando') == 'videos' and datos_usuario[user_id].get('multiple'):
        videos = datos_usuario[user_id].get('videos', [])
        
        if not videos:
            await message.reply("❌ No recibí ningún video. Envía videos primero.")
            return
        
        # Cambiar a esperar caption
        datos_usuario[user_id]['esperando'] = 'caption'
        datos_usuario[user_id]['multiples_completados'] = True
        
        await message.reply(
            f"✅ {len(videos)} videos recibidos.\n"
            f"Ahora envía la caption para todos los videos:",
            reply_markup=ForceReply(selective=True)
        )
    else:
        await message.reply("❌ No hay una sesión de subida múltiple activa.")

@app.on_message(filters.video)
async def manejar_video(client, message):
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    if user_id not in datos_usuario:
        await message.reply("❌ Primero selecciona 'Subir un Reels' en el menú.")
        return
    
    estado = datos_usuario[user_id]
    
    if estado.get('esperando') == 'video':
        # Video único: descargar y esperar caption
        ruta_video = await message.download()
        datos_usuario[user_id]['ruta_video'] = ruta_video
        datos_usuario[user_id]['esperando'] = 'caption'
        
        await message.reply(
            "✅ ¡Video recibido!\n"
            "Ahora envía la caption que quieres para este Reel:",
            reply_markup=ForceReply(selective=True)
        )
    
    elif estado.get('esperando') == 'videos' and estado.get('multiple'):
        # Múltiples videos: coleccionarlos
        ruta_video = await message.download()
        datos_usuario[user_id]['videos'].append(ruta_video)
        
        cantidad = len(datos_usuario[user_id]['videos'])
        await message.reply(
            f"✅ Video {cantidad} recibido!\n"
            f"Envía más videos o escribe /listo cuando termines."
        )

@app.on_message(filters.text)
async def manejar_texto(client, message):
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    if user_id not in datos_usuario:
        return
    
    estado = datos_usuario[user_id]
    
    if estado.get('esperando') == 'caption':
        caption = message.text
        
        if estado.get('multiple') and estado.get('multiples_completados'):
            # Subir múltiples videos con la misma caption
            videos = estado.get('videos', [])
            await message.reply(f"🔄 Subiendo {len(videos)} videos a Instagram...")
            
            for i, ruta_video in enumerate(videos, 1):
                try:
                    await message.reply(f"📤 Subiendo video {i}/{len(videos)}...")
                    cliente_insta.clip_upload(ruta_video, caption)
                    
                    if i < len(videos):
                        await asyncio.sleep(30)  # Esperar 30 segundos entre subidas
                        
                except Exception as e:
                    await message.reply(f"⚠️ Error en video {i}: {str(e)[:100]}")
            
            await message.reply("✅ ¡Todos los videos subidos correctamente!")
            
            # Limpiar archivos temporales
            for ruta_video in videos:
                try:
                    os.remove(ruta_video)
                except:
                    pass
            
            del datos_usuario[user_id]
            
        else:
            # Video único
            ruta_video = estado.get('ruta_video')
            if ruta_video:
                await message.reply("🔄 Subiendo a Instagram...")
                
                try:
                    cliente_insta.clip_upload(ruta_video, caption)
                    await message.reply("✅ ¡Video subido correctamente como Reel!")
                    
                    # Limpiar archivo temporal
                    os.remove(ruta_video)
                    
                except Exception as e:
                    await message.reply(f"⚠️ Error: {str(e)[:100]}")
                
                del datos_usuario[user_id]
            else:
                await message.reply("❌ No se encontró el video. Por favor, empieza de nuevo.")
    
    elif estado.get('esperando') == 'caption_defecto':
        caption = message.text
        
        if guardar_caption_defecto(caption):
            await message.reply(f"✅ ¡Caption por defecto actualizada!\n\nNueva caption:\n{caption}")
        else:
            await message.reply("❌ Error al guardar la caption.")
        
        del datos_usuario[user_id]

if __name__ == "__main__":
    print("🚀 Bot iniciado!")
    app.run()
