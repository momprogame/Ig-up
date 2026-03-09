import os
import asyncio
import time
import random
import json
from pyrogram import Client, filters
from instagrapi import Client as InstaClient
from instagrapi.exceptions import ChallengeRequired, LoginRequired
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton

# ========== VARIABLES DE ENTORNO ==========
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
INSTAGRAM_USUARIO = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_CONTRASENA = os.getenv('INSTAGRAM_PASSWORD')
ARCHIVO_USUARIOS_AUTORIZADOS = "authorized_users.txt"
ARCHIVO_CAPTION = "caption.txt"
ARCHIVO_MODO_USUARIO = "modos_usuario.txt"
ARCHIVO_SESION = "instagram_session.json"

# ========== VERIFICACIÓN DE VARIABLES ==========
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, INSTAGRAM_USUARIO, INSTAGRAM_CONTRASENA]):
    print("❌ Error: Faltan variables de entorno")
    print("Necesitas configurar:")
    print("  - TELEGRAM_API_ID")
    print("  - TELEGRAM_API_HASH")
    print("  - TELEGRAM_BOT_TOKEN")
    print("  - INSTAGRAM_USERNAME")
    print("  - INSTAGRAM_PASSWORD")
    exit(1)

# ========== DICCIONARIO PARA DATOS TEMPORALES ==========
# {user_id: {'esperando': 'caption', 'ruta_video': 'ruta', 'multiple': False}}
datos_usuario = {}

# ========== FUNCIÓN DE LOGIN DE INSTAGRAM CON MANEJO DE DESAFÍOS ==========
def login_instagram(max_intentos=3):
    """Intenta login con manejo de desafíos"""
    
    cliente = InstaClient()
    
    # Configurar delays aleatorios para simular comportamiento humano
    cliente.request_timeout = 30
    cliente.delay_range = [random.randint(1, 5) for _ in range(2)]
    
    print("=" * 50)
    print("📱 INICIANDO SESIÓN EN INSTAGRAM")
    print("=" * 50)
    
    for intento in range(max_intentos):
        try:
            print(f"🔄 Intento {intento + 1} de {max_intentos}")
            
            # Intentar cargar sesión guardada
            if os.path.exists(ARCHIVO_SESION) and intento == 0:
                print("📂 Cargando sesión guardada...")
                cliente.load_settings(ARCHIVO_SESION)
                
                # Verificar que la sesión funciona
                try:
                    # Intentar una acción simple para verificar la sesión
                    cliente.user_info(cliente.user_id)
                    print("✅ Sesión cargada y válida")
                    return cliente
                except LoginRequired:
                    print("⚠️ Sesión expirada, haciendo login nuevo...")
                except Exception as e:
                    print(f"⚠️ Error verificando sesión: {e}")
            
            # Login normal
            print("🔄 Iniciando sesión con credenciales...")
            time.sleep(random.randint(3, 8))  # Delay humano
            
            # Intentar login
            cliente.login(INSTAGRAM_USUARIO, INSTAGRAM_CONTRASENA)
            
            # Guardar sesión para próximos usos
            cliente.dump_settings(ARCHIVO_SESION)
            print(f"✅ Login exitoso como {INSTAGRAM_USUARIO}")
            
            # Mostrar información de la cuenta
            user_info = cliente.user_info(cliente.user_id)
            print(f"👤 Usuario: {user_info.username}")
            print(f"📊 Seguidores: {user_info.follower_count}")
            print(f"📸 Posts: {user_info.media_count}")
            
            return cliente
            
        except ChallengeRequired as e:
            print(f"⚠️ DESAFÍO REQUERIDO (intento {intento + 1})")
            print("Instagram pide verificación adicional.")
            
            if intento < max_intentos - 1:
                print("📧 Revisa tu email o teléfono y completa la verificación")
                print("⏱️ Esperando 60 segundos...")
                
                # Guardar URL del desafío si está disponible
                if hasattr(e, 'challenge_url'):
                    print(f"🔗 URL del desafío: {e.challenge_url}")
                
                # Intentar obtener el código de verificación
                try:
                    # Esto puede variar según la implementación
                    cliente.challenge_resolve()
                except:
                    pass
                
                time.sleep(60)
            else:
                print("❌ Máximo de intentos alcanzado para el desafío")
                
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            if intento < max_intentos - 1:
                print(f"⏱️ Esperando 30 segundos antes de reintentar...")
                time.sleep(30)
            else:
                print("❌ Máximo de intentos alcanzado")
    
    return None

# ========== INICIALIZAR CLIENTE DE INSTAGRAM ==========
print("🚀 Iniciando bot de Instagram Reels...")
cliente_insta = login_instagram()

if not cliente_insta:
    print("❌ No se pudo iniciar sesión en Instagram")
    print("El bot continuará pero puede tener problemas para subir videos")
    # No salimos, intentamos continuar sin Instagram

# ========== INICIALIZAR CLIENTE DE TELEGRAM ==========
app = Client(
    "mi_bot",
    api_id=int(TELEGRAM_API_ID),
    api_hash=TELEGRAM_API_HASH,
    bot_token=TELEGRAM_BOT_TOKEN
)

# ========== FUNCIONES PARA GUARDAR Y RECUPERAR EL MODO DEL USUARIO ==========
def guardar_modo_usuario(user_id, modo):
    """Guarda el modo actual del usuario (simple, multiple, normal)"""
    try:
        # Leer archivo existente
        modos = {}
        try:
            with open(ARCHIVO_MODO_USUARIO, "r") as f:
                for linea in f:
                    if ":" in linea:
                        uid, modo_guardado = linea.strip().split(":", 1)
                        modos[uid] = modo_guardado
        except FileNotFoundError:
            pass
        
        # Actualizar modo
        modos[str(user_id)] = modo
        
        # Guardar archivo
        with open(ARCHIVO_MODO_USUARIO, "w") as f:
            for uid, modo_guardado in modos.items():
                f.write(f"{uid}:{modo_guardado}\n")
        return True
    except Exception as e:
        print(f"Error guardando modo: {e}")
        return False

def obtener_modo_usuario(user_id):
    """Obtiene el modo actual del usuario"""
    try:
        with open(ARCHIVO_MODO_USUARIO, "r") as f:
            for linea in f:
                if ":" in linea:
                    uid, modo = linea.strip().split(":", 1)
                    if uid == str(user_id):
                        return modo
    except FileNotFoundError:
        pass
    return "normal"  # Modo por defecto

# ========== FUNCIONES DE AUTORIZACIÓN ==========
def esta_autorizado(user_id):
    try:
        with open(ARCHIVO_USUARIOS_AUTORIZADOS, "r") as file:
            autorizados = [linea.strip() for linea in file.readlines()]
        return str(user_id) in autorizados
    except:
        return False

# ========== FUNCIONES PARA CAPTIONS ==========
def obtener_caption_defecto():
    try:
        with open(ARCHIVO_CAPTION, "r", encoding="utf-8") as file:
            return file.read().strip()
    except:
        return "Video subido desde Telegram"

def guardar_caption_defecto(caption):
    try:
        with open(ARCHIVO_CAPTION, "w", encoding="utf-8") as file:
            file.write(caption)
        return True
    except:
        return False

# ========== FUNCIÓN PARA MOSTRAR ESTADO ==========
async def mostrar_estado_modo(client, chat_id, user_id):
    """Muestra el modo actual al usuario"""
    modo = obtener_modo_usuario(user_id)
    
    if modo == "simple":
        texto = "📌 **Modo actual: Subir un Reels**\n\nEstás en modo de subida individual. Envía un video y te pediré la caption."
    elif modo == "multiple":
        texto = "📌 **Modo actual: Subir Múltiples Reels**\n\nEstás en modo de subida múltiple. Envía varios videos, escribe /listo cuando termines, y todos se subirán con la misma caption."
    else:
        texto = "📌 **Modo actual: Normal**\n\nUsa los botones del menú para seleccionar un modo."
    
    await client.send_message(chat_id, texto)

# ========== HANDLER PARA /start ==========
@app.on_message(filters.command("start"))
async def inicio(client, message):
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        await message.reply(f"⛔ No autorizado. Tu ID: {user_id}")
        return
    
    # Botones inline para seleccionar modo
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Modo: Subir un Reels", callback_data="modo_simple")],
        [InlineKeyboardButton("📤 Modo: Subir Múltiples", callback_data="modo_multiple")],
        [InlineKeyboardButton("🔄 Modo Normal", callback_data="modo_normal")],
        [InlineKeyboardButton("📝 Cambiar Caption", callback_data="cambiar_caption")],
        [InlineKeyboardButton("📊 Ver mi modo", callback_data="ver_modo")]
    ])
    
    # Verificar si Instagram está conectado
    estado_instagram = "✅ Conectado" if cliente_insta else "❌ Desconectado"
    
    await message.reply(
        f"👋 ¡Bienvenido al bot!\n\n"
        f"**Instagram:** {estado_instagram}\n\n"
        "**Selecciona un modo:**\n"
        "• 📤 **Modo Subir un Reels**: Se mantendrá activo hasta que lo cambies.\n"
        "• 📤 **Modo Subir Múltiples**: Se mantendrá activo. Envía varios videos y usa /listo.\n"
        "• 🔄 **Modo Normal**: Solo responde a los botones.\n\n"
        "**El modo se mantiene activo hasta que lo cambies manualmente.**",
        reply_markup=keyboard
    )

# ========== HANDLER PARA /listo ==========
@app.on_message(filters.command("listo"))
async def listo_multiples(client, message):
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    modo = obtener_modo_usuario(user_id)
    
    if modo != "multiple":
        await message.reply("❌ No estás en modo múltiple. Usa /start y selecciona 'Modo Subir Múltiples'.")
        return
    
    if user_id in datos_usuario and datos_usuario[user_id].get('esperando') == 'videos':
        videos = datos_usuario[user_id].get('videos', [])
        
        if not videos:
            await message.reply("❌ No recibí ningún video. Envía videos primero.")
            return
        
        # Cambiar a esperar caption
        datos_usuario[user_id]['esperando'] = 'caption'
        datos_usuario[user_id]['multiples_completados'] = True
        
        await message.reply(
            f"✅ {len(videos)} videos recibidos.\n"
            f"Ahora envía la caption para todos los videos (solo una vez):",
            reply_markup=ForceReply(selective=True)
        )
    else:
        await message.reply("❌ No hay videos pendientes. Envía algunos videos primero.")

# ========== HANDLER PARA /modo ==========
@app.on_message(filters.command("modo"))
async def ver_modo_command(client, message):
    user_id = message.from_user.id
    await mostrar_estado_modo(client, message.chat.id, user_id)

# ========== CALLBACKS PARA BOTONES INLINE ==========
@app.on_callback_query()
async def manejar_callbacks(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if not esta_autorizado(user_id):
        await callback_query.answer("⛔ No autorizado", show_alert=True)
        return
    
    if data == "modo_simple":
        guardar_modo_usuario(user_id, "simple")
        await callback_query.message.edit_text(
            "✅ **Modo activado: Subir un Reels**\n\n"
            "Ahora puedes enviar videos uno por uno. Por cada video te pediré la caption.\n"
            "Este modo se mantendrá activo hasta que lo cambies desde /start.\n\n"
            "**Comandos útiles:**\n"
            "/modo - Ver tu modo actual\n"
            "/start - Cambiar de modo"
        )
        
    elif data == "modo_multiple":
        guardar_modo_usuario(user_id, "multiple")
        await callback_query.message.edit_text(
            "✅ **Modo activado: Subir Múltiples Reels**\n\n"
            "Ahora puedes enviar varios videos. Sigue estos pasos:\n"
            "1️⃣ Envía todos los videos que quieras subir\n"
            "2️⃣ Cuando termines, escribe /listo\n"
            "3️⃣ Envía UNA SOLA caption para todos los videos\n\n"
            "Este modo se mantendrá activo hasta que lo cambies desde /start.\n\n"
            "**Comandos útiles:**\n"
            "/modo - Ver tu modo actual\n"
            "/listo - Cuando termines de enviar videos"
        )
        
    elif data == "modo_normal":
        guardar_modo_usuario(user_id, "normal")
        await callback_query.message.edit_text(
            "✅ **Modo Normal activado**\n\n"
            "Ahora el bot solo responderá a los botones del menú.\n"
            "Usa /start para seleccionar otro modo cuando quieras."
        )
        
    elif data == "cambiar_caption":
        datos_usuario[user_id] = {'esperando': 'caption_defecto'}
        await callback_query.message.edit_text(
            "📝 Envía la nueva caption por defecto:"
        )
        
    elif data == "ver_modo":
        modo = obtener_modo_usuario(user_id)
        textos_modo = {
            "simple": "📤 Subir un Reels (individual)",
            "multiple": "📤 Subir Múltiples Reels",
            "normal": "🔄 Modo Normal"
        }
        texto = f"📊 **Tu modo actual:** {textos_modo.get(modo, 'Desconocido')}"
        await callback_query.message.edit_text(texto)
    
    await callback_query.answer()

# ========== HANDLER PARA VIDEOS ==========
@app.on_message(filters.video)
async def manejar_video(client, message):
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    # Verificar si Instagram está conectado
    if not cliente_insta:
        await message.reply("❌ Instagram no está conectado. El bot no puede subir videos.")
        return
    
    modo = obtener_modo_usuario(user_id)
    
    if modo == "normal":
        await message.reply("❌ Estás en modo normal. Usa /start y selecciona un modo de subida.")
        return
    
    if modo == "simple":
        # Modo simple: por cada video, pedir caption
        await message.reply("📥 Descargando video...")
        ruta_video = await message.download()
        
        datos_usuario[user_id] = {
            'ruta_video': ruta_video,
            'esperando': 'caption',
            'multiple': False
        }
        
        await message.reply(
            "✅ **Video recibido en modo individual**\n\n"
            "Ahora envía la caption para este video:",
            reply_markup=ForceReply(selective=True)
        )
    
    elif modo == "multiple":
        # Modo múltiple: acumular videos
        if user_id not in datos_usuario:
            datos_usuario[user_id] = {'videos': [], 'esperando': 'videos', 'multiple': True}
        
        if datos_usuario[user_id].get('esperando') == 'videos':
            await message.reply("📥 Descargando video...")
            ruta_video = await message.download()
            datos_usuario[user_id]['videos'].append(ruta_video)
            
            cantidad = len(datos_usuario[user_id]['videos'])
            await message.reply(
                f"✅ **Video {cantidad} recibido en modo múltiple**\n\n"
                f"Puedes seguir enviando más videos.\n"
                f"Cuando termines, escribe /listo"
            )
        else:
            await message.reply("❌ Ya estás procesando un lote. Termina con /listo primero.")

# ========== HANDLER PARA TEXTO ==========
@app.on_message(filters.text & ~filters.command(["start", "listo", "modo"]))
async def manejar_texto(client, message):
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    # Verificar si Instagram está conectado
    if not cliente_insta:
        await message.reply("❌ Instagram no está conectado. El bot no puede subir videos.")
        return
    
    # Verificar si está esperando caption o caption por defecto
    if user_id in datos_usuario:
        estado = datos_usuario[user_id]
        
        if estado.get('esperando') == 'caption':
            caption = message.text
            
            if estado.get('multiple'):
                # Subir múltiples videos
                videos = estado.get('videos', [])
                await message.reply(f"🔄 Subiendo {len(videos)} videos a Instagram...")
                
                for i, ruta_video in enumerate(videos, 1):
                    try:
                        await message.reply(f"📤 Subiendo video {i}/{len(videos)}...")
                        cliente_insta.clip_upload(ruta_video, caption)
                        
                        if i < len(videos):
                            await message.reply(f"⏱️ Esperando 30 segundos antes del siguiente video...")
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
                
                # Mantener el modo activo, pero limpiar datos temporales
                if user_id in datos_usuario:
                    del datos_usuario[user_id]
                
                # Recordar que el modo sigue activo
                await message.reply(
                    "📌 **El modo múltiple sigue activo**\n"
                    "Puedes seguir enviando más videos. Usa /listo cuando termines cada lote."
                )
                
            else:
                # Subir video único
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
                    
                    # Mantener el modo activo, pero limpiar datos temporales
                    if user_id in datos_usuario:
                        del datos_usuario[user_id]
                    
                    # Recordar que el modo sigue activo
                    await message.reply(
                        "📌 **El modo individual sigue activo**\n"
                        "Puedes seguir enviando más videos. Por cada video te pediré la caption."
                    )
                else:
                    await message.reply("❌ No se encontró el video. Intenta de nuevo.")
        
        elif estado.get('esperando') == 'caption_defecto':
            caption = message.text
            
            if guardar_caption_defecto(caption):
                await message.reply(f"✅ ¡Caption por defecto actualizada!\n\nNueva caption:\n{caption}")
            else:
                await message.reply("❌ Error al guardar la caption.")
            
            del datos_usuario[user_id]
    else:
        # Si no está esperando nada, mostrar el modo actual
        await mostrar_estado_modo(client, message.chat.id, user_id)

# ========== HANDLER PARA CUANDO EL BOT SE DETIENE ==========
@app.on_message(filters.command("stop") & filters.user("self"))
async def stop_bot(client, message):
    await message.reply("🛑 Deteniendo el bot...")
    await client.stop()

# ========== INICIO DEL BOT ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 BOT DE INSTAGRAM REELS INICIADO")
    print("=" * 50)
    print(f"📱 Instagram: {INSTAGRAM_USUARIO}")
    print(f"✅ Conectado: {cliente_insta is not None}")
    print("=" * 50)
    
    app.run()
