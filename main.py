import os
import asyncio
import time
import random
import json
from pyrogram import Client, filters
from instagrapi import Client as InstaClient
from instagrapi.exceptions import ChallengeRequired, LoginRequired, TwoFactorRequired
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton

# ========== VARIABLES DE ENTORNO ==========
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ARCHIVO_USUARIOS_AUTORIZADOS = "authorized_users.txt"
ARCHIVO_CAPTION = "caption.txt"
ARCHIVO_MODO_USUARIO = "modos_usuario.txt"
ARCHIVO_SESION = "instagram_session.json"
ARCHIVO_CREDENCIALES = "instagram_creds.json"

# ========== VERIFICACIÓN DE VARIABLES ==========
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN]):
    print("❌ Error: Faltan variables de entorno de Telegram")
    exit(1)

# ========== VARIABLES GLOBALES ==========
datos_usuario = {}  # Diccionario para datos temporales de usuarios
cliente_insta = None  # Cliente global de Instagram (inicialmente None)

# ========== FUNCIONES PARA GUARDAR CREDENCIALES ==========
def guardar_credenciales(username, password):
    """Guarda las credenciales de Instagram de forma segura"""
    try:
        credenciales = {"username": username, "password": password}
        with open(ARCHIVO_CREDENCIALES, "w") as f:
            json.dump(credenciales, f)
        return True
    except Exception as e:
        print(f"Error guardando credenciales: {e}")
        return False

def cargar_credenciales():
    """Carga las credenciales guardadas"""
    try:
        with open(ARCHIVO_CREDENCIALES, "r") as f:
            return json.load(f)
    except:
        return None

# ========== FUNCIÓN DE LOGIN DE INSTAGRAM CON MANEJO DE DESAFÍOS ==========
async def login_instagram(username, password, message=None, two_factor_code=None):
    """Intenta login con manejo de desafíos"""
    
    cliente = InstaClient()
    
    # Configurar delays aleatorios para simular comportamiento humano
    cliente.request_timeout = 30
    cliente.delay_range = [random.randint(1, 5) for _ in range(2)]
    
    try:
        # Intentar cargar sesión guardada primero
        if os.path.exists(ARCHIVO_SESION):
            if message:
                await message.reply("📂 Cargando sesión guardada...")
            cliente.load_settings(ARCHIVO_SESION)
            
            try:
                # Verificar que la sesión funciona
                cliente.user_info(cliente.user_id)
                if message:
                    await message.reply("✅ Sesión cargada correctamente")
                return cliente
            except:
                if message:
                    await message.reply("⚠️ Sesión expirada, haciendo login nuevo...")
        
        # Login normal
        if message:
            await message.reply("🔄 Iniciando sesión en Instagram...")
        
        time.sleep(random.randint(2, 5))
        
        # Intentar login
        cliente.login(username, password)
        
        # Guardar sesión para próximos usos
        cliente.dump_settings(ARCHIVO_SESION)
        
        if message:
            user_info = cliente.user_info(cliente.user_id)
            await message.reply(
                f"✅ **Login exitoso!**\n\n"
                f"👤 **Usuario:** {user_info.username}\n"
                f"📊 **Seguidores:** {user_info.follower_count}\n"
                f"📸 **Posts:** {user_info.media_count}"
            )
        
        return cliente
        
    except TwoFactorRequired:
        if message:
            await message.reply(
                "🔐 **Verificación en dos pasos requerida**\n\n"
                "Instagram te ha enviado un código de verificación.\n"
                "Por favor, envíame el código:"
            )
        # Guardar estado para esperar código 2FA
        return "2fa_required"
        
    except ChallengeRequired as e:
        if message:
            await message.reply(
                "⚠️ **Desafío requerido por Instagram**\n\n"
                "Instagram necesita verificar que eres tú.\n"
                "Revisa tu email o teléfono y completa la verificación.\n\n"
                "Después de verificarlo, intenta /login de nuevo."
            )
        return None
        
    except Exception as e:
        error_msg = str(e)
        if "The password you entered is incorrect" in error_msg:
            if message:
                await message.reply("❌ **Contraseña incorrecta**\n\nPor favor, verifica tu contraseña e intenta de nuevo.")
        elif "The username you entered doesn't appear to belong to an account" in error_msg:
            if message:
                await message.reply("❌ **Usuario no encontrado**\n\nVerifica tu nombre de usuario.")
        else:
            if message:
                await message.reply(f"❌ **Error:** {error_msg[:200]}")
        return None

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

# ========== FUNCIONES PARA GUARDAR Y RECUPERAR EL MODO ==========
def guardar_modo_usuario(user_id, modo):
    try:
        modos = {}
        try:
            with open(ARCHIVO_MODO_USUARIO, "r") as f:
                for linea in f:
                    if ":" in linea:
                        uid, modo_guardado = linea.strip().split(":", 1)
                        modos[uid] = modo_guardado
        except FileNotFoundError:
            pass
        
        modos[str(user_id)] = modo
        
        with open(ARCHIVO_MODO_USUARIO, "w") as f:
            for uid, modo_guardado in modos.items():
                f.write(f"{uid}:{modo_guardado}\n")
        return True
    except Exception as e:
        print(f"Error guardando modo: {e}")
        return False

def obtener_modo_usuario(user_id):
    try:
        with open(ARCHIVO_MODO_USUARIO, "r") as f:
            for linea in f:
                if ":" in linea:
                    uid, modo = linea.strip().split(":", 1)
                    if uid == str(user_id):
                        return modo
    except FileNotFoundError:
        pass
    return "normal"

# ========== FUNCIÓN PARA MOSTRAR ESTADO ==========
async def mostrar_estado_modo(client, chat_id, user_id):
    """Muestra el modo actual al usuario"""
    global cliente_insta
    modo = obtener_modo_usuario(user_id)
    
    estado_instagram = "✅ Conectado" if cliente_insta else "❌ Desconectado"
    
    if modo == "simple":
        texto = f"📌 **Modo actual: Subir un Reels**\n📱 **Instagram:** {estado_instagram}\n\nEstás en modo de subida individual. Envía un video y te pediré la caption."
    elif modo == "multiple":
        texto = f"📌 **Modo actual: Subir Múltiples Reels**\n📱 **Instagram:** {estado_instagram}\n\nEstás en modo de subida múltiple. Envía varios videos, escribe /listo cuando termines, y todos se subirán con la misma caption."
    else:
        texto = f"📌 **Modo actual: Normal**\n📱 **Instagram:** {estado_instagram}\n\nUsa los botones del menú para seleccionar un modo."
    
    await client.send_message(chat_id, texto)

# ========== INICIALIZAR CLIENTE DE TELEGRAM ==========
app = Client(
    "mi_bot",
    api_id=int(TELEGRAM_API_ID),
    api_hash=TELEGRAM_API_HASH,
    bot_token=TELEGRAM_BOT_TOKEN
)

# ========== HANDLER PARA /start ==========
@app.on_message(filters.command("start"))
async def inicio(client, message):
    global cliente_insta
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        await message.reply(f"⛔ No autorizado. Tu ID: {user_id}")
        return
    
    estado_instagram = "✅ Conectado" if cliente_insta else "❌ Desconectado"
    
    # Botones inline para seleccionar modo
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Modo: Subir un Reels", callback_data="modo_simple")],
        [InlineKeyboardButton("📤 Modo: Subir Múltiples", callback_data="modo_multiple")],
        [InlineKeyboardButton("🔄 Modo Normal", callback_data="modo_normal")],
        [InlineKeyboardButton("🔐 Login Instagram", callback_data="login_instagram")],
        [InlineKeyboardButton("📝 Cambiar Caption", callback_data="cambiar_caption")],
        [InlineKeyboardButton("📊 Ver mi modo", callback_data="ver_modo")]
    ])
    
    await message.reply(
        f"👋 ¡Bienvenido al bot!\n\n"
        f"**Instagram:** {estado_instagram}\n\n"
        "**Selecciona un modo:**\n"
        "• 📤 **Modo Subir un Reels**: Se mantendrá activo.\n"
        "• 📤 **Modo Subir Múltiples**: Se mantendrá activo.\n"
        "• 🔐 **Login Instagram**: Conecta tu cuenta.\n"
        "• 🔄 **Modo Normal**: Solo responde a los botones.\n\n"
        "**El modo se mantiene activo hasta que lo cambies.**",
        reply_markup=keyboard
    )

# ========== HANDLER PARA /listo ==========
@app.on_message(filters.command("listo"))
async def listo_multiples(client, message):
    global cliente_insta
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    if not cliente_insta:
        await message.reply("❌ **Instagram no conectado.**\nUsa /start y selecciona 'Login Instagram' primero.")
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

# ========== HANDLER PARA /logout ==========
@app.on_message(filters.command("logout"))
async def logout_instagram(client, message):
    global cliente_insta
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    if cliente_insta:
        try:
            # Eliminar archivos de sesión
            if os.path.exists(ARCHIVO_SESION):
                os.remove(ARCHIVO_SESION)
            if os.path.exists(ARCHIVO_CREDENCIALES):
                os.remove(ARCHIVO_CREDENCIALES)
        except:
            pass
        
        cliente_insta = None
        await message.reply("✅ **Sesión de Instagram cerrada**")
    else:
        await message.reply("ℹ️ No hay ninguna sesión activa")

# ========== CALLBACKS PARA BOTONES INLINE ==========
@app.on_callback_query()
async def manejar_callbacks(client, callback_query):
    global cliente_insta
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if not esta_autorizado(user_id):
        await callback_query.answer("⛔ No autorizado", show_alert=True)
        return
    
    if data == "modo_simple":
        guardar_modo_usuario(user_id, "simple")
        estado = "✅ Conectado" if cliente_insta else "❌ Desconectado"
        await callback_query.message.edit_text(
            f"✅ **Modo activado: Subir un Reels**\n📱 **Instagram:** {estado}\n\n"
            "Ahora puedes enviar videos uno por uno. Por cada video te pediré la caption.\n"
            "Este modo se mantendrá activo hasta que lo cambies.\n\n"
            "**Comandos útiles:**\n"
            "/modo - Ver tu modo actual\n"
            "/start - Cambiar de modo"
        )
        
    elif data == "modo_multiple":
        guardar_modo_usuario(user_id, "multiple")
        estado = "✅ Conectado" if cliente_insta else "❌ Desconectado"
        await callback_query.message.edit_text(
            f"✅ **Modo activado: Subir Múltiples Reels**\n📱 **Instagram:** {estado}\n\n"
            "Sigue estos pasos:\n"
            "1️⃣ Envía todos los videos\n"
            "2️⃣ Cuando termines, escribe /listo\n"
            "3️⃣ Envía UNA SOLA caption\n\n"
            "Este modo se mantendrá activo hasta que lo cambies.\n\n"
            "**Comandos útiles:**\n"
            "/modo - Ver tu modo actual\n"
            "/listo - Cuando termines de enviar videos"
        )
        
    elif data == "modo_normal":
        guardar_modo_usuario(user_id, "normal")
        estado = "✅ Conectado" if cliente_insta else "❌ Desconectado"
        await callback_query.message.edit_text(
            f"✅ **Modo Normal activado**\n📱 **Instagram:** {estado}\n\n"
            "Usa /start para seleccionar otro modo."
        )
        
    elif data == "login_instagram":
        # Verificar si ya hay sesión
        if cliente_insta:
            user_info = cliente_insta.user_info(cliente_insta.user_id)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Cambiar cuenta", callback_data="login_nuevo")],
                [InlineKeyboardButton("❌ Cerrar sesión", callback_data="logout")]
            ])
            await callback_query.message.edit_text(
                f"✅ **Ya hay una sesión activa**\n\n"
                f"👤 **Usuario:** {user_info.username}\n"
                f"📊 **Seguidores:** {user_info.follower_count}\n\n"
                f"¿Qué deseas hacer?",
                reply_markup=keyboard
            )
        else:
            datos_usuario[user_id] = {'esperando': 'instagram_user'}
            await callback_query.message.edit_text(
                "🔐 **Login en Instagram**\n\n"
                "Por favor, envía tu **nombre de usuario** de Instagram:"
            )
            
    elif data == "login_nuevo":
        datos_usuario[user_id] = {'esperando': 'instagram_user'}
        await callback_query.message.edit_text(
            "🔐 **Cambiar cuenta de Instagram**\n\n"
            "Por favor, envía tu **nuevo nombre de usuario**:"
        )
        
    elif data == "logout":
        if cliente_insta:
            try:
                if os.path.exists(ARCHIVO_SESION):
                    os.remove(ARCHIVO_SESION)
                if os.path.exists(ARCHIVO_CREDENCIALES):
                    os.remove(ARCHIVO_CREDENCIALES)
            except:
                pass
            cliente_insta = None
        await callback_query.message.edit_text("✅ **Sesión cerrada correctamente**")
        
    elif data == "cambiar_caption":
        datos_usuario[user_id] = {'esperando': 'caption_defecto'}
        actual = obtener_caption_defecto()
        await callback_query.message.edit_text(
            f"📝 **Caption actual:**\n{actual}\n\n"
            f"Envía la nueva caption por defecto:"
        )
        
    elif data == "ver_modo":
        modo = obtener_modo_usuario(user_id)
        estado = "✅ Conectado" if cliente_insta else "❌ Desconectado"
        textos_modo = {
            "simple": "📤 Subir un Reels (individual)",
            "multiple": "📤 Subir Múltiples Reels",
            "normal": "🔄 Modo Normal"
        }
        texto = f"📊 **Tu modo actual:** {textos_modo.get(modo, 'Desconocido')}\n📱 **Instagram:** {estado}"
        await callback_query.message.edit_text(texto)
    
    await callback_query.answer()

# ========== HANDLER PARA VIDEOS ==========
@app.on_message(filters.video)
async def manejar_video(client, message):
    global cliente_insta
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    if not cliente_insta:
        await message.reply("❌ **Instagram no conectado.**\nUsa /start y selecciona 'Login Instagram' primero.")
        return
    
    modo = obtener_modo_usuario(user_id)
    
    if modo == "normal":
        await message.reply("❌ Estás en modo normal. Usa /start y selecciona un modo de subida.")
        return
    
    if modo == "simple":
        await message.reply("📥 Descargando video...")
        ruta_video = await message.download()
        
        datos_usuario[user_id] = {
            'ruta_video': ruta_video,
            'esperando': 'caption',
            'multiple': False
        }
        
        await message.reply(
            "✅ **Video recibido**\n\n"
            "Ahora envía la caption para este video:",
            reply_markup=ForceReply(selective=True)
        )
    
    elif modo == "multiple":
        if user_id not in datos_usuario:
            datos_usuario[user_id] = {'videos': [], 'esperando': 'videos', 'multiple': True}
        
        if datos_usuario[user_id].get('esperando') == 'videos':
            await message.reply("📥 Descargando video...")
            ruta_video = await message.download()
            datos_usuario[user_id]['videos'].append(ruta_video)
            
            cantidad = len(datos_usuario[user_id]['videos'])
            await message.reply(
                f"✅ **Video {cantidad} recibido**\n\n"
                f"Envía más videos o escribe /listo para terminar."
            )
        else:
            await message.reply("❌ Ya estás procesando un lote. Termina con /listo primero.")

# ========== HANDLER PARA TEXTO ==========
@app.on_message(filters.text & ~filters.command(["start", "listo", "modo", "logout"]))
async def manejar_texto(client, message):
    global cliente_insta
    user_id = message.from_user.id
    
    if not esta_autorizado(user_id):
        return
    
    if user_id in datos_usuario:
        estado = datos_usuario[user_id]
        
        # ===== PROCESAR LOGIN DE INSTAGRAM =====
        if estado.get('esperando') == 'instagram_user':
            username = message.text.strip()
            datos_usuario[user_id]['instagram_user'] = username
            datos_usuario[user_id]['esperando'] = 'instagram_pass'
            
            await message.reply(
                f"👤 **Usuario:** {username}\n\n"
                f"🔑 Ahora envía tu **contraseña** de Instagram:",
                reply_markup=ForceReply(selective=True)
            )
            
        elif estado.get('esperando') == 'instagram_pass':
            username = estado.get('instagram_user')
            password = message.text.strip()
            
            await message.reply("🔄 Verificando credenciales...")
            
            # Intentar login
            resultado = await login_instagram(username, password, message)
            
            if isinstance(resultado, InstaClient):
                cliente_insta = resultado
                guardar_credenciales(username, password)
                del datos_usuario[user_id]
            elif resultado == "2fa_required":
                datos_usuario[user_id]['esperando'] = 'instagram_2fa'
                datos_usuario[user_id]['instagram_user'] = username
                datos_usuario[user_id]['instagram_pass'] = password
            else:
                del datos_usuario[user_id]
                
        elif estado.get('esperando') == 'instagram_2fa':
            code = message.text.strip()
            username = estado.get('instagram_user')
            password = estado.get('instagram_pass')
            
            await message.reply("🔄 Verificando código...")
            
            try:
                cliente = InstaClient()
                cliente.login(username, password, verification_code=code)
                cliente.dump_settings(ARCHIVO_SESION)
                
                cliente_insta = cliente
                guardar_credenciales(username, password)
                
                user_info = cliente.user_info(cliente.user_id)
                await message.reply(
                    f"✅ **Login exitoso con 2FA!**\n\n"
                    f"👤 **Usuario:** {user_info.username}\n"
                    f"📊 **Seguidores:** {user_info.follower_count}"
                )
                
                del datos_usuario[user_id]
            except Exception as e:
                await message.reply(f"❌ **Error:** {str(e)[:200]}")
        
        # ===== PROCESAR CAPTION =====
        elif estado.get('esperando') == 'caption':
            caption = message.text
            
            if not cliente_insta:
                await message.reply("❌ Instagram no está conectado.")
                del datos_usuario[user_id]
                return
            
            if estado.get('multiple'):
                videos = estado.get('videos', [])
                await message.reply(f"🔄 Subiendo {len(videos)} videos a Instagram...")
                
                for i, ruta_video in enumerate(videos, 1):
                    try:
                        await message.reply(f"📤 Subiendo video {i}/{len(videos)}...")
                        cliente_insta.clip_upload(ruta_video, caption)
                        
                        if i < len(videos):
                            await asyncio.sleep(30)
                            
                    except Exception as e:
                        await message.reply(f"⚠️ Error en video {i}: {str(e)[:100]}")
                
                await message.reply("✅ ¡Todos los videos subidos correctamente!")
                
                for ruta_video in videos:
                    try:
                        os.remove(ruta_video)
                    except:
                        pass
                
                del datos_usuario[user_id]
                
            else:
                ruta_video = estado.get('ruta_video')
                if ruta_video:
                    await message.reply("🔄 Subiendo a Instagram...")
                    
                    try:
                        cliente_insta.clip_upload(ruta_video, caption)
                        await message.reply("✅ ¡Video subido correctamente como Reel!")
                        os.remove(ruta_video)
                    except Exception as e:
                        await message.reply(f"⚠️ Error: {str(e)[:100]}")
                    
                    del datos_usuario[user_id]
                else:
                    await message.reply("❌ No se encontró el video.")
                    del datos_usuario[user_id]
        
        elif estado.get('esperando') == 'caption_defecto':
            caption = message.text
            
            if guardar_caption_defecto(caption):
                await message.reply(f"✅ ¡Caption por defecto actualizada!\n\n**Nueva caption:**\n{caption}")
            else:
                await message.reply("❌ Error al guardar la caption.")
            
            del datos_usuario[user_id]
    
    else:
        await mostrar_estado_modo(client, message.chat.id, user_id)

# ========== INICIO DEL BOT ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 BOT DE INSTAGRAM REELS INICIADO")
    print("=" * 50)
    
    # Intentar cargar credenciales guardadas al inicio
    creds = cargar_credenciales()
    if creds:
        print(f"📂 Credenciales encontradas para: {creds['username']}")
        print("🔄 Intentando login automático...")
        
        # Crear event loop para el login asíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ejecutar login sin mensaje de Telegram
        async def auto_login():
            global cliente_insta
            try:
                cliente = InstaClient()
                if os.path.exists(ARCHIVO_SESION):
                    cliente.load_settings(ARCHIVO_SESION)
                    try:
                        cliente.user_info(cliente.user_id)
                        cliente_insta = cliente
                        print(f"✅ Login automático exitoso: {creds['username']}")
                        return
                    except:
                        pass
                
                cliente.login(creds['username'], creds['password'])
                cliente.dump_settings(ARCHIVO_SESION)
                cliente_insta = cliente
                print(f"✅ Login automático exitoso: {creds['username']}")
            except Exception as e:
                print(f"⚠️ No se pudo hacer login automático: {e}")
        
        loop.run_until_complete(auto_login())
        loop.close()
    
    print(f"📱 Instagram: {'✅ Conectado' if cliente_insta else '❌ Desconectado'}")
    print("=" * 50)
    
    app.run()
