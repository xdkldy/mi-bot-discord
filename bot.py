import discord
from discord.ext import commands
from discord.ui import Modal, TextInput
from discord import app_commands
import json
import os
import datetime
import aiohttp
import time
import sqlite3
import re
import asyncio
import random
import io
import string

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Tokens ──────────────────────────────────────────────────────────────────
_TOKEN_HARDCODED      = "MTQ5MzEwMzUzMTMyMDY3NjM3Mw.GUs441.8wyY2ONEVnj1QiaCYu0pY_BjhcKuLhA9VuHhyU"
_GEMINI_KEY_HARDCODED = "AQ.Ab8RN6JK2jndctOgfpFrQ3tny2jbGse4O2sJMlQN1aY3i6zAaQ"

TOKEN      = _TOKEN_HARDCODED      or os.environ.get("DISCORD_TOKEN", "")
GEMINI_KEY = _GEMINI_KEY_HARDCODED or os.environ.get("GEMINI_API_KEY", "")

if not TOKEN:
    raise RuntimeError(
        "❌ Falta el token de Discord.\n"
        "   Pégalo en la variable _TOKEN_HARDCODED al inicio del script."
    )

# ── Google Generative AI ──────────────────────────────────────────────────
try:
    from google import genai as google_genai
    ai_client = google_genai.Client(api_key=GEMINI_KEY)
    _AI_BACKEND = "genai"
except (ImportError, AttributeError):
    try:
        import google.generativeai as _legacy_genai
        _legacy_genai.configure(api_key=GEMINI_KEY)
        ai_client = None
        _AI_BACKEND = "legacy"
    except ImportError:
        ai_client = None
        _AI_BACKEND = "none"
        print("⚠️  Sin librería de IA instalada.")

# ─────────────────────────────────────────────
#  AUTO-RESPUESTAS POR PALABRAS CLAVE
# ─────────────────────────────────────────────

AUTO_RESPONSES: list[tuple[set[str], dict[str, list[str]]]] = [
    (
        {"verificar", "verificacion", "verificación", "verify", "verificarme", "verificado"},
        {
            "ES": [
                f"Claro! Para verificarte ve a <#1503459513175380029>, presiona el botón **Verify** y sigue el enlace de Double Counter.",
                f"La verificación es sencilla: entra a <#1503459513175380029>, haz clic en **Verify** y completa el proceso en Double Counter.",
                f"Para verificarte: dirígete a <#1503459513175380029> → botón **Verify** → enlace de Double Counter.",
                f"Sin problema! Paso a paso: primero ve a <#1503459513175380029>, después presiona **Verify** y sigue el enlace de Double Counter.",
                f"El proceso de verificación está en <#1503459513175380029>. Solo presiona **Verify** y completa el formulario de Double Counter.",
            ],
            "EN": [
                f"Sure! Head to <#1503459513175380029>, press the **Verify** button and follow the Double Counter link.",
                f"Verification is easy: go to <#1503459513175380029>, click **Verify** and complete the steps on Double Counter.",
                f"To get verified: visit <#1503459513175380029> → hit **Verify** → follow the Double Counter link.",
                f"No problem! Step by step: go to <#1503459513175380029>, press **Verify**, then follow the Double Counter link.",
                f"Verification is at <#1503459513175380029>. Just press **Verify** and fill out the Double Counter form.",
            ],
            "PT": [
                f"Claro! Para se verificar vá a <#1503459513175380029>, pressione o botão **Verify** e siga o link do Double Counter.",
                f"A verificação é simples: entre em <#1503459513175380029>, clique em **Verify** e complete o processo no Double Counter.",
                f"Para se verificar: vá para <#1503459513175380029> → botão **Verify** → link do Double Counter.",
                f"Sem problema! Passo a passo: primeiro vá a <#1503459513175380029>, depois pressione **Verify** e siga o link do Double Counter.",
                f"O processo de verificação está em <#1503459513175380029>. Só pressione **Verify** e preencha o formulário do Double Counter.",
            ],
        },
    ),
    (
        {"juego", "juegos", "condo", "condos", "game", "games", "key", "llave", "acceso", "access"},
        {
            "ES": [
                f"Para acceder a los juegos/condos:\n1️⃣ Únete al grupo: <#1503597582688194690>\n2️⃣ Consigue tu key en: <#1503597637067079721>\n3️⃣ Agrega al usuario de: <#1509671797983940658>",
                f"El proceso para juegos es este: primero entra en <#1503597582688194690>, luego obtén tu key en <#1503597637067079721> y por último agrega al user de <#1509671797983940658>.",
                f"Claro, te explico los pasos para los condos: únete al grupo en <#1503597582688194690>, obtén la key en <#1503597637067079721> y añade al usuario desde <#1509671797983940658>.",
            ],
            "EN": [
                f"To access games/condos:\n1️⃣ Join the group: <#1503597582688194690>\n2️⃣ Get your key at: <#1503597637067079721>\n3️⃣ Add the user from: <#1509671797983940658>",
                f"Here's how to get into games: first join <#1503597582688194690>, then grab your key at <#1503597637067079721> and finally add the user from <#1509671797983940658>.",
                f"Sure! For condos: join the group at <#1503597582688194690>, get your key from <#1503597637067079721>, and add the user listed in <#1509671797983940658>.",
            ],
            "PT": [
                f"Para acessar os jogos/condos:\n1️⃣ Entre no grupo: <#1503597582688194690>\n2️⃣ Pegue sua key em: <#1503597637067079721>\n3️⃣ Adicione o usuário de: <#1509671797983940658>",
                f"O processo para jogos é: primeiro entre em <#1503597582688194690>, depois pegue sua key em <#1503597637067079721> e por último adicione o usuário de <#1509671797983940658>.",
                f"Claro! Para condos: entre no grupo em <#1503597582688194690>, pegue a key em <#1503597637067079721> e adicione o usuário de <#1509671797983940658>.",
            ],
        },
    ),
    (
        {"reglas", "rules", "regla", "normas", "norma"},
        {
            "ES": [
                f"Las reglas del servidor las puedes leer en <#1503459081619243058>. Es importante conocerlas para evitar sanciones!",
                f"Puedes ver todas las normas en <#1503459081619243058>. Si tienes alguna duda sobre alguna regla, con gusto te ayudo.",
                f"El canal de reglas es <#1503459081619243058>. Te recomiendo leerlas antes de continuar.",
            ],
            "EN": [
                f"You can read the server rules at <#1503459081619243058>. It's important to know them to avoid sanctions!",
                f"All the rules are in <#1503459081619243058>. If you have questions about any rule, I'm happy to help.",
                f"The rules channel is <#1503459081619243058>. I recommend reading them before continuing.",
            ],
            "PT": [
                f"Você pode ler as regras do servidor em <#1503459081619243058>. É importante conhecê-las para evitar sanções!",
                f"Todas as normas estão em <#1503459081619243058>. Se tiver dúvidas sobre alguma regra, fico feliz em ajudar.",
                f"O canal de regras é <#1503459081619243058>. Recomendo lê-las antes de continuar.",
            ],
        },
    ),
    (
        {"noticias", "news", "novedades", "anuncios", "announcements", "updates"},
        {
            "ES": [
                f"Las últimas novedades del servidor están en <#1503591370953064488>. Échale un vistazo!",
                f"Para estar al día con todo lo que pasa, revisa <#1503591370953064488>.",
                f"El canal de noticias es <#1503591370953064488>. Ahí publicamos todas las actualizaciones importantes.",
            ],
            "EN": [
                f"The latest server news is at <#1503591370953064488>. Take a look!",
                f"To stay up to date with everything, check <#1503591370953064488>.",
                f"The news channel is <#1503591370953064488>. We post all important updates there.",
            ],
            "PT": [
                f"As últimas novidades do servidor estão em <#1503591370953064488>. Dê uma olhada!",
                f"Para ficar por dentro de tudo, veja <#1503591370953064488>.",
                f"O canal de notícias é <#1503591370953064488>. Publicamos todas as atualizações importantes lá.",
            ],
        },
    ),
    (
        {"ban", "baneado", "banned", "desban", "unban", "apelar", "apelacion", "apelación", "appeal"},
        {
            "ES": [
                f"Para apelar un ban necesito que me cuentes qué pasó. Describe tu situación aquí y un miembro del staff lo revisará.",
                f"Entendido. Si quieres apelar, por favor explica brevemente por qué crees que el ban fue incorrecto y el staff te atenderá.",
                f"Claro, puedo ayudarte con eso. Cuéntame qué sucedió para que el staff pueda revisarlo.",
            ],
            "EN": [
                f"To appeal a ban I need you to tell me what happened. Describe your situation here and a staff member will review it.",
                f"Got it. If you want to appeal, please briefly explain why you think the ban was incorrect and the staff will assist you.",
                f"Sure, I can help with that. Tell me what happened so the staff can review it.",
            ],
            "PT": [
                f"Para apelar um ban preciso que me conte o que aconteceu. Descreva sua situação aqui e um membro da equipe irá revisá-la.",
                f"Entendido. Se quiser apelar, explique brevemente por que acha que o ban foi incorreto e a equipe irá atendê-lo.",
                f"Claro, posso ajudar com isso. Conte-me o que aconteceu para que a equipe possa revisar.",
            ],
        },
    ),
]

OWNER_IDS = [1450410095228747790, 1488259581636513954]

GUILD_ID             = 1503453816060645396
STAFF_CHANNEL_ID     = 1503590366824104078
ROLES_LOG_CHANNEL_ID = 1503590756961488947
STAFF_ROLE_ID        = 1510056086013612173

# ─────────────────────────────────────────────
#  CAPTCHA CONFIG
# ─────────────────────────────────────────────
VERIFIED_ROLE_ID = 1503459513175380029

pending_captchas:   dict[int, dict] = {}
captcha_cooldowns:  dict[int, float] = {}
CAPTCHA_TIMEOUT   = 180
CAPTCHA_COOLDOWN  = 120   # ← 2 minutos

WHITELIST_ROLES = [
    1504140787934433350, 1503458291395592342, 1503734300330295306,
    1503738085425545316, 1503735986276925450, 1503850340317925612,
    1503735240571486218, 1503734870747381893, 1503734458753487010,
    1503735021381488790,
]

BLOCKED_LINKS = [
    "discord.gg/", "discord.com/invite/", "discordapp.com/invite/",
    "discord.me/", "discord.li/", "discord.io/",
]

DATA_FILE    = "tickets.json"
HISTORY_FILE = "ticket_history.json"

xp_sleep = False

LINK_MUTE_LADDER = [
    datetime.timedelta(minutes=1),
    datetime.timedelta(minutes=5),
    datetime.timedelta(minutes=10),
    datetime.timedelta(hours=1),
    datetime.timedelta(days=1),
    datetime.timedelta(days=3),
    datetime.timedelta(days=7),
]
MAX_WARNINGS = 7

# ─────────────────────────────────────────────
#  PALABRAS PROHIBIDAS — línea ~195
# ─────────────────────────────────────────────
# Frases/palabras cuya presencia en el mensaje activa el sistema de infracciones.
# Al 2.º uso en el mismo día → warn + mute en ESCALADA (se reinicia cada día).
FORBIDDEN_PHRASES: list[str] = [
    "read my bio",
    "check my bio",
    "read my b!o",
    "ch3ck my b1o",
    "she is waiting for you",
    "she's waiting for you",
    "check my b!o",
    "r3ad my bio",
    "r3ad my b!o",
    "check my prof",
    "read my prof",
]

# Escalada de mutes para INFRACCIONES NUEVAS (@everyone y palabras prohibidas)
# Reinicia diariamente por usuario
NEW_INFRACTION_MUTE_LADDER = [
    datetime.timedelta(minutes=5),
    datetime.timedelta(minutes=10),
    datetime.timedelta(hours=1),
    datetime.timedelta(hours=5),
    datetime.timedelta(days=4),
    datetime.timedelta(days=9),
    datetime.timedelta(days=17),
    datetime.timedelta(days=28),
]

# Seguimiento en memoria: {user_id: {"count": int, "date": "YYYY-MM-DD", "mute_level": int}}
forbidden_infractions: dict[int, dict] = {}
everyone_infractions:  dict[int, dict] = {}

def _today_str() -> str:
    return datetime.date.today().isoformat()

def _get_infraction(store: dict, user_id: int) -> dict:
    today = _today_str()
    entry = store.get(user_id)
    if not entry or entry.get("date") != today:
        store[user_id] = {"count": 0, "date": today, "mute_level": 0}
    return store[user_id]

def _increment_infraction(store: dict, user_id: int) -> dict:
    entry = _get_infraction(store, user_id)
    entry["count"] += 1
    return entry

# ─────────────────────────────────────────────
#  BASE DE DATOS
# ─────────────────────────────────────────────

conn   = sqlite3.connect("levels.db")
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    userId TEXT PRIMARY KEY,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    lastMsg INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS user_languages (
    userId TEXT PRIMARY KEY,
    lang TEXT DEFAULT 'AUTO'
);
CREATE TABLE IF NOT EXISTS reaction_roles (
    message_id INTEGER,
    emoji TEXT,
    role_id INTEGER,
    requires_captcha INTEGER DEFAULT 0,
    PRIMARY KEY (message_id, emoji)
);
CREATE TABLE IF NOT EXISTS warnings (
    userId TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS verified_users (
    userId TEXT PRIMARY KEY,
    verified_at TEXT
);
CREATE TABLE IF NOT EXISTS verification_panels (
    message_id INTEGER PRIMARY KEY,
    role_id INTEGER,
    unrole_id INTEGER
);
""")

# Migración: columna requires_captcha
try:
    cursor.execute("ALTER TABLE reaction_roles ADD COLUMN requires_captcha INTEGER DEFAULT 0")
    conn.commit()
except Exception:
    pass

cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('levelup_msg',     '🎉 {user} has reached level {level}!')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('levelup_channel', '0')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ticket_count',    '35')")
conn.commit()


def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None

def set_setting(key, value):
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()

def get_user_lang(user_id):
    cursor.execute("SELECT lang FROM user_languages WHERE userId=?", (str(user_id),))
    row = cursor.fetchone()
    return row[0] if row else "AUTO"

def set_user_lang(user_id, lang):
    cursor.execute("REPLACE INTO user_languages (userId, lang) VALUES (?, ?)", (str(user_id), lang.upper()))
    conn.commit()

def get_warnings(user_id: int) -> int:
    cursor.execute("SELECT count FROM warnings WHERE userId=?", (str(user_id),))
    row = cursor.fetchone()
    return row[0] if row else 0

def add_warning(user_id: int) -> int:
    current = get_warnings(user_id)
    new_count = min(current + 1, MAX_WARNINGS)
    cursor.execute("REPLACE INTO warnings (userId, count) VALUES (?, ?)", (str(user_id), new_count))
    conn.commit()
    return new_count

def reset_warnings(user_id: int):
    cursor.execute("REPLACE INTO warnings (userId, count) VALUES (?, 0)", (str(user_id),))
    conn.commit()

def is_verified(user_id: int) -> bool:
    cursor.execute("SELECT userId FROM verified_users WHERE userId=?", (str(user_id),))
    return cursor.fetchone() is not None

def mark_verified(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO verified_users (userId, verified_at) VALUES (?, ?)",
        (str(user_id), datetime.datetime.utcnow().isoformat())
    )
    conn.commit()

def get_verification_panel(message_id: int) -> tuple[int | None, int | None]:
    """Returns (role_id, unrole_id) for a panel message, or (None, None)."""
    cursor.execute("SELECT role_id, unrole_id FROM verification_panels WHERE message_id=?", (message_id,))
    row = cursor.fetchone()
    return (row[0], row[1]) if row else (None, None)

def xp_needed(level):
    return 5 * level * level + 50 * level + 100

def get_progress_bar(current, total, blocks=10):
    pct    = min(current / max(1, total), 1.0)
    filled = int(pct * blocks)
    return "🟩" * filled + "⬛" * (blocks - filled)

# ─────────────────────────────────────────────
#  CAPTCHA IMAGE GENERATOR
# ─────────────────────────────────────────────

def generate_captcha_image(code: str) -> io.BytesIO:
    width, height = 280, 90
    bg_color = (30, 30, 40)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    for _ in range(600):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(1, 3)
        c = (random.randint(60, 100), random.randint(60, 100), random.randint(80, 120))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)

    for _ in range(8):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(80, 140), random.randint(80, 140), random.randint(100, 160)), width=1)

    _FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/data/data/com.termux/files/usr/share/fonts/truetype/DejaVuSans-Bold.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/system/fonts/Roboto-Bold.ttf",
        "/system/fonts/DroidSans-Bold.ttf",
    ]
    font = None
    for _fp in _FONT_PATHS:
        try:
            font = ImageFont.truetype(_fp, 44)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default(size=40)

    colors = [
        (220, 80, 80), (80, 200, 120), (80, 150, 230),
        (230, 200, 60), (200, 80, 200), (80, 220, 220),
    ]

    char_width = width // (len(code) + 1)
    for i, ch in enumerate(code):
        x = char_width * i + char_width // 2 - 10 + random.randint(-4, 4)
        y = (height - 50) // 2 + random.randint(-8, 8)
        color = colors[i % len(colors)]
        tmp = Image.new("RGBA", (50, 60), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp)
        tmp_draw.text((5, 5), ch, font=font, fill=color)
        angle = random.randint(-18, 18)
        tmp = tmp.rotate(angle, expand=True)
        img.paste(tmp, (x, y), tmp)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_captcha_code(length: int = 6) -> str:
    chars = [c for c in string.ascii_uppercase + string.digits if c not in "0O1IL"]
    return "".join(random.choices(chars, k=length))


# ─────────────────────────────────────────────
#  CAPTCHA — MODAL + BOTÓN
# ─────────────────────────────────────────────

_CAPTCHA_TITLES = {
    "EN": "Verification — Enter the code",
    "ES": "Verificacion — Escribe el codigo",
    "PT": "Verificacao — Escreva o codigo",
}
_CAPTCHA_LABELS = {
    "EN": "Write the text shown in the image",
    "ES": "Escribe el texto que aparece en la imagen",
    "PT": "Escreva o texto que aparece na imagem",
}
_CAPTCHA_PLACEHOLDERS = {
    "EN": "Ex: A3KX7P",
    "ES": "Ej: A3KX7P",
    "PT": "Ex: A3KX7P",
}


class CaptchaVerifyModal(Modal):
    def __init__(self, user_id: int, guild: discord.Guild, lang: str = "ES"):
        super().__init__(title=_CAPTCHA_TITLES.get(lang, _CAPTCHA_TITLES["ES"]))
        self.user_id = user_id
        self.guild   = guild
        self.lang    = lang
        self.answer  = TextInput(
            label=_CAPTCHA_LABELS.get(lang, _CAPTCHA_LABELS["ES"]),
            placeholder=_CAPTCHA_PLACEHOLDERS.get(lang, _CAPTCHA_PLACEHOLDERS["ES"]),
            min_length=1,
            max_length=20,
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            entry = pending_captchas.get(self.user_id)
            if not entry:
                msgs = {
                    "EN": "Your captcha has expired. Go back to the server and press Verify again.",
                    "ES": "Tu captcha ha expirado. Vuelve al servidor y presiona Verify de nuevo.",
                    "PT": "Seu captcha expirou. Volte ao servidor e pressione Verify novamente.",
                }
                return await interaction.response.send_message(msgs.get(self.lang, msgs["ES"]), ephemeral=True)

            # Ignorar espacios al comparar
            user_answer = self.answer.value.strip().replace(" ", "").upper()
            correct     = entry["code"].upper()

            if user_answer == correct:
                role_id   = entry.get("role_id")
                unrole_id = entry.get("unrole_id")
                # Siempre usar el Member del servidor, no el User del DM
                member = self.guild.get_member(self.user_id)
                if member is None:
                    try:
                        member = await self.guild.fetch_member(self.user_id)
                    except discord.NotFound:
                        msgs = {
                            "EN": "Could not find you in the server. Make sure you are still a member.",
                            "ES": "No pude encontrarte en el servidor. Asegurate de seguir siendo miembro.",
                            "PT": "Nao consegui te encontrar no servidor. Verifique se ainda e membro.",
                        }
                        return await interaction.response.send_message(msgs.get(self.lang, msgs["ES"]), ephemeral=True)
                await _grant_verified(member, self.guild, interaction, role_id=role_id, unrole_id=unrole_id)
            else:
                # Owners no reciben cooldown
                if self.user_id not in OWNER_IDS:
                    pending_captchas.pop(self.user_id, None)
                    captcha_cooldowns[self.user_id] = time.time() + CAPTCHA_COOLDOWN
                mins = CAPTCHA_COOLDOWN // 60
                msgs = {
                    "EN": f"Incorrect code. You must wait **{mins} minutes** before trying again." if self.user_id not in OWNER_IDS else "Incorrect code. Try again.",
                    "ES": f"Codigo incorrecto. Debes esperar **{mins} minutos** antes de intentarlo de nuevo." if self.user_id not in OWNER_IDS else "Codigo incorrecto. Intentalo de nuevo.",
                    "PT": f"Codigo incorreto. Voce deve aguardar **{mins} minutos** antes de tentar novamente." if self.user_id not in OWNER_IDS else "Codigo incorreto. Tente novamente.",
                }
                await interaction.response.send_message(msgs.get(self.lang, msgs["ES"]), ephemeral=True)

        except discord.InteractionResponded:
            pass
        except Exception as e:
            print(f"[CaptchaModal error] {e}")
            try:
                msgs = {
                    "EN": "An internal error occurred. Please try again or contact staff.",
                    "ES": "Ocurrio un error interno. Intentalo de nuevo o contacta al staff.",
                    "PT": "Ocorreu um erro interno. Tente novamente ou contate a equipe.",
                }
                if not interaction.response.is_done():
                    await interaction.response.send_message(msgs.get(self.lang, msgs["ES"]), ephemeral=True)
                else:
                    await interaction.followup.send(msgs.get(self.lang, msgs["ES"]), ephemeral=True)
            except Exception:
                pass


class CaptchaVerifyView(discord.ui.View):
    def __init__(self, user_id: int, guild: discord.Guild, lang: str = "ES"):
        super().__init__(timeout=CAPTCHA_TIMEOUT)
        self.user_id = user_id
        self.guild   = guild
        self.lang    = lang
        _btn_labels  = {"EN": "Enter the code", "ES": "Ingresar el codigo", "PT": "Inserir o codigo"}
        btn = discord.ui.Button(
            label=_btn_labels.get(lang, _btn_labels["ES"]),
            style=discord.ButtonStyle.primary,
        )
        btn.callback = self._open_modal
        self.add_item(btn)

    async def _open_modal(self, interaction: discord.Interaction):
        # Solo el usuario del captcha puede usar el botón
        if interaction.user.id != self.user_id:
            msgs = {
                "EN": "This captcha is not for you.",
                "ES": "Este captcha no es para ti.",
                "PT": "Este captcha nao e para voce.",
            }
            return await interaction.response.send_message(msgs.get(self.lang, msgs["ES"]), ephemeral=True)

        # Si ya no hay captcha pendiente (expiró o falló), avisar en vez de abrir modal vacío
        if self.user_id not in pending_captchas:
            msgs = {
                "EN": "This captcha has expired or is no longer valid. Go back to the server and press **Verify** again.",
                "ES": "Este captcha ya expiro o no es valido. Vuelve al servidor y presiona **Verify** de nuevo.",
                "PT": "Este captcha expirou ou nao e mais valido. Volte ao servidor e pressione **Verify** novamente.",
            }
            return await interaction.response.send_message(msgs.get(self.lang, msgs["ES"]), ephemeral=True)

        await interaction.response.send_modal(
            CaptchaVerifyModal(self.user_id, self.guild, self.lang)
        )

    async def on_timeout(self):
        pass


CaptchaModal        = CaptchaVerifyModal
CaptchaFallbackView = CaptchaVerifyView


# ─────────────────────────────────────────────
#  GRANT VERIFIED ROLE
# ─────────────────────────────────────────────

async def _grant_verified(
    member: discord.Member,
    guild: discord.Guild,
    interaction: discord.Interaction | None = None,
    *,
    role_id: int | None = None,
    unrole_id: int | None = None,
):
    """Asigna el rol verificado y quita el unrole si corresponde."""
    # Asignar rol
    if role_id:
        role = guild.get_role(role_id)
        if role is None:
            msg = "❌ No se encontró el rol configurado. Contacta al staff."
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                try:
                    await member.send(msg)
                except discord.Forbidden:
                    pass
            return
        try:
            await member.add_roles(role, reason="Verificado mediante captcha")
        except discord.Forbidden:
            msg = "❌ No tengo permisos para asignarte el rol. Contacta al staff."
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                try:
                    await member.send(msg)
                except discord.Forbidden:
                    pass
            return

    # Quitar unrole (si es distinto al role que se acaba de agregar)
    if unrole_id and unrole_id != role_id:
        unrole = guild.get_role(unrole_id)
        if unrole and unrole in member.roles:
            try:
                await member.remove_roles(unrole, reason="Verificacion completada — unrole")
            except discord.Forbidden:
                pass
    elif unrole_id and unrole_id == role_id:
        # Mismo rol: no tiene sentido agregar y quitar; se ignora el unrole
        pass

    mark_verified(member.id)
    pending_captchas.pop(member.id, None)
    captcha_cooldowns.pop(member.id, None)

    lang = get_user_lang(member.id)
    if lang == "AUTO":
        lang = "ES"

    success_msgs = {
        "EN": [
            "Verification complete. You now have access to the server.",
            "Done. Your verification was successful. Welcome.",
            "Correct code — you are now verified.",
        ],
        "ES": [
            "Verificacion completada. Ya tienes acceso al servidor.",
            "Listo. Tu verificacion fue exitosa. Bienvenido/a.",
            "Codigo correcto — ya estas verificado/a.",
        ],
        "PT": [
            "Verificacao concluida. Voce ja tem acesso ao servidor.",
            "Pronto. Sua verificacao foi bem-sucedida. Bem-vindo/a.",
            "Codigo correto — voce ja esta verificado/a.",
        ],
    }
    success = random.choice(success_msgs.get(lang, success_msgs["ES"]))

    if interaction:
        await interaction.response.send_message(success, ephemeral=True)
    else:
        try:
            await member.send(success)
        except discord.Forbidden:
            pass

    log_ch = bot.get_channel(ROLES_LOG_CHANNEL_ID)
    if log_ch:
        e = discord.Embed(
            title="✅ Usuario Verificado",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow(),
        )
        e.add_field(name="Usuario", value=f"{member.mention} (`{member}`)", inline=False)
        e.add_field(name="Método",  value="Captcha",                         inline=True)
        if unrole_id and unrole_id != role_id:
            ur = guild.get_role(unrole_id)
            e.add_field(name="Rol eliminado", value=ur.mention if ur else str(unrole_id), inline=True)
        await log_ch.send(embed=e)


# ─────────────────────────────────────────────
#  START CAPTCHA FLOW
# ─────────────────────────────────────────────

async def start_captcha(
    member: discord.Member,
    guild: discord.Guild,
    *,
    role_id: int | None = None,
    unrole_id: int | None = None,
    interaction: discord.Interaction | None = None,
):
    lang = get_user_lang(member.id)
    if lang == "AUTO":
        lang = "ES"

    code    = generate_captcha_code()
    img_buf = generate_captcha_image(code)

    pending_captchas[member.id] = {
        "code":      code,
        "guild_id":  guild.id,
        "role_id":   role_id,
        "unrole_id": unrole_id,
    }

    _titles = {
        "EN": "Server Verification",
        "ES": "Verificacion del servidor",
        "PT": "Verificacao do servidor",
    }
    _descs = {
        "EN": (
            "**Press the button below and write what you see in the image.**\n"
            f"You have **{CAPTCHA_TIMEOUT // 60} minutes** to complete it."
        ),
        "ES": (
            "**Presiona el boton de abajo y escribe lo que ves en la imagen.**\n"
            f"Tienes **{CAPTCHA_TIMEOUT // 60} minutos** para completarlo."
        ),
        "PT": (
            "**Pressione o botao abaixo e escreva o que ve na imagem.**\n"
            f"Voce tem **{CAPTCHA_TIMEOUT // 60} minutos** para concluir."
        ),
    }
    _footers = {
        "EN": "Do not share this code with anyone.",
        "ES": "No compartas este codigo con nadie.",
        "PT": "Nao compartilhe este codigo com ninguem.",
    }

    view    = CaptchaVerifyView(member.id, guild, lang)
    dm_sent = False

    try:
        dm   = await member.create_dm()
        file = discord.File(img_buf, filename="captcha.png")
        embed = discord.Embed(
            title=_titles.get(lang, _titles["ES"]),
            description=_descs.get(lang, _descs["ES"]),
            color=discord.Color.blurple(),
        )
        embed.set_image(url="attachment://captcha.png")
        embed.set_footer(text=_footers.get(lang, _footers["ES"]))
        await dm.send(embed=embed, file=file, view=view)
        dm_sent = True
    except discord.Forbidden:
        dm_sent = False

    if not dm_sent:
        # DMs cerrados — fallback EFÍMERO si tenemos interaction (solo el usuario lo ve)
        _fb_descs = {
            "EN": (
                "I couldn't send you a private message. Here is your captcha.\n"
                "Press the button below to enter the code. **Only you can see this message.**"
            ),
            "ES": (
                "No pude enviarte un mensaje privado. Aqui esta tu captcha.\n"
                "Presiona el boton de abajo para ingresar el codigo. **Solo tu puedes ver este mensaje.**"
            ),
            "PT": (
                "Nao consegui te enviar uma mensagem privada. Aqui esta o seu captcha.\n"
                "Pressione o botao abaixo para inserir o codigo. **So voce pode ver esta mensagem.**"
            ),
        }

        img_buf.seek(0)
        file = discord.File(img_buf, filename="captcha.png")
        embed = discord.Embed(
            title=_titles.get(lang, _titles["ES"]),
            description=_fb_descs.get(lang, _fb_descs["ES"]),
            color=discord.Color.blurple(),
        )
        embed.set_image(url="attachment://captcha.png")

        if interaction:
            # Ephemeral followup — solo el usuario lo ve
            try:
                await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)
            except Exception:
                pass
        else:
            # Fallback desde reaction (sin interaction): enviar en canal de verificación
            channel = guild.get_channel(1503459513175380029)
            if channel is None:
                for ch in guild.text_channels:
                    perms = ch.permissions_for(guild.me)
                    if perms.send_messages and perms.embed_links and perms.attach_files:
                        channel = ch
                        break
            if channel:
                msg = await channel.send(
                    content=member.mention,
                    embed=embed,
                    file=file,
                    view=CaptchaVerifyView(member.id, guild, lang),
                )
                await asyncio.sleep(CAPTCHA_TIMEOUT)
                try:
                    await msg.delete()
                except discord.NotFound:
                    pass

    asyncio.create_task(_captcha_timeout_watcher(member.id, code, lang))


async def _captcha_timeout_watcher(user_id: int, code: str, lang: str = "ES"):
    await asyncio.sleep(CAPTCHA_TIMEOUT)
    entry = pending_captchas.get(user_id)
    if entry and entry["code"] == code:
        pending_captchas.pop(user_id, None)
        _msgs = {
            "EN": "Time to complete the captcha expired. Press the Verify button again to try again.",
            "ES": "El tiempo para completar el captcha expiro. Presiona el boton Verify de nuevo para intentarlo.",
            "PT": "O tempo para completar o captcha expirou. Pressione o botao Verify novamente para tentar de novo.",
        }
        try:
            user = bot.get_user(user_id)
            if user:
                await user.send(_msgs.get(lang, _msgs["ES"]))
        except discord.Forbidden:
            pass


# ─────────────────────────────────────────────
#  HELPERS DE INFRACCIONES NUEVAS
# ─────────────────────────────────────────────

def _fmt_duration(td: datetime.timedelta) -> str:
    s = int(td.total_seconds())
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


async def apply_new_infraction_mute(member: discord.Member, store: dict, channel, reason_text: str):
    """Aplica mute escalonado para infracciones nuevas (palabras prohibidas / @everyone)."""
    entry = _get_infraction(store, member.id)
    level = entry.get("mute_level", 0)

    if level >= len(NEW_INFRACTION_MUTE_LADDER):
        # Ban
        try:
            await member.ban(reason=reason_text + " — límite de infracciones alcanzado")
        except discord.Forbidden:
            pass
        e = discord.Embed(
            title="⛔ Miembro Baneado",
            description=f"{member.mention} fue baneado por exceso de infracciones.\n**Motivo:** {reason_text}",
            color=discord.Color.dark_red(),
        )
        try:
            await channel.send(embed=e, delete_after=20)
        except Exception:
            pass
        return

    mute_time = NEW_INFRACTION_MUTE_LADDER[level]
    entry["mute_level"] = level + 1

    try:
        await member.timeout(mute_time, reason=reason_text)
    except discord.Forbidden:
        pass

    duration_str = _fmt_duration(mute_time)
    add_warning(member.id)

    e = discord.Embed(
        title="⚠️ Advertencia + Mute",
        description=(
            f"{member.mention} — **{reason_text}**\n"
            f"Mute aplicado: **{duration_str}**"
        ),
        color=discord.Color.orange(),
    )
    try:
        await channel.send(embed=e, delete_after=15)
    except Exception:
        pass


# ─────────────────────────────────────────────
#  LOCALIZACIÓN
# ─────────────────────────────────────────────

LANG_MAP = {"ES": "es", "EN": "en", "PT": "pt"}

COMMAND_LOCALIZATION: dict[str, dict] = {
    "ban": {
        "name":        {"es-ES": "banear",            "pt-BR": "banir"},
        "description": {"es-ES": "Banea a un usuario","pt-BR": "Bane um usuário"},
    },
    "clear": {
        "name":        {"es-ES": "limpiar",                  "pt-BR": "limpar"},
        "description": {"es-ES": "Borra mensajes del canal", "pt-BR": "Apaga mensagens do canal"},
    },
    "kick": {
        "name":        {"es-ES": "expulsar",             "pt-BR": "expulsar"},
        "description": {"es-ES": "Expulsa a un miembro", "pt-BR": "Expulsa um membro"},
    },
    "leaderboard": {
        "name":        {"es-ES": "tabla_clasificacion",          "pt-BR": "placar"},
        "description": {"es-ES": "Top 10 de usuarios por nivel", "pt-BR": "Top 10 usuários por nível"},
    },
    "mute": {
        "name":        {"es-ES": "silenciar",                         "pt-BR": "silenciar"},
        "description": {"es-ES": "Silencia a un miembro del servidor", "pt-BR": "Silencia um membro do servidor"},
    },
    "rank": {
        "name":        {"es-ES": "rango",                       "pt-BR": "ranque"},
        "description": {"es-ES": "Muestra tu tarjeta de nivel", "pt-BR": "Mostra seu cartão de nível"},
    },
    "reaction_role_create": {
        "name":        {"es-ES": "crear_rol_reaccion",             "pt-BR": "criar_cargo_reacao"},
        "description": {"es-ES": "Crea un rol obtenible por reacción", "pt-BR": "Cria um cargo por reação"},
    },
    "role_all": {
        "name":        {"es-ES": "rol_a_todos",                        "pt-BR": "cargo_para_todos"},
        "description": {"es-ES": "Asigna un rol a todos los miembros", "pt-BR": "Atribui cargo a todos os membros"},
    },
    "set_language": {
        "name":        {"es-ES": "cambiar_idioma",                        "pt-BR": "mudar_idioma"},
        "description": {"es-ES": "Cambia tu idioma de interfaz personal", "pt-BR": "Altera seu idioma de interface pessoal"},
    },
    "ticket_history": {
        "name":        {"es-ES": "historial_tickets",               "pt-BR": "historico_tickets"},
        "description": {"es-ES": "Ver historial de tickets cerrados", "pt-BR": "Ver histórico de tickets fechados"},
    },
    "ticket_panel": {
        "name":        {"es-ES": "panel_tickets",                "pt-BR": "painel_tickets"},
        "description": {"es-ES": "Reenviar el panel de soporte", "pt-BR": "Reenviar o painel de suporte"},
    },
    "translate_msg": {
        "name":        {"es-ES": "traducir_msg",                 "pt-BR": "traduzir_msg"},
        "description": {"es-ES": "Traduce un mensaje por su ID", "pt-BR": "Traduz uma mensagem pelo ID"},
    },
    "upload": {
        "name":        {"es-ES": "publicar",                      "pt-BR": "publicar"},
        "description": {"es-ES": "Envía un formato de publicación", "pt-BR": "Envia um formato de publicação"},
    },
    "xp_add": {
        "name":        {"es-ES": "añadir_xp",            "pt-BR": "adicionar_xp"},
        "description": {"es-ES": "Añade XP a un usuario", "pt-BR": "Adiciona XP a um usuário"},
    },
    "xp_pause": {
        "name":        {"es-ES": "pausar_alertas",                  "pt-BR": "pausar_alertas"},
        "description": {"es-ES": "Pausa anuncios de subida de nivel", "pt-BR": "Pausa anúncios de aumento de nível"},
    },
    "xp_resume": {
        "name":        {"es-ES": "reanudar_alertas",                    "pt-BR": "retomar_alertas"},
        "description": {"es-ES": "Reactiva anuncios de subida de nivel", "pt-BR": "Reativa anúncios de aumento de nível"},
    },
    "xp_set": {
        "name":        {"es-ES": "establecer_nivel",           "pt-BR": "definir_nivel"},
        "description": {"es-ES": "Cambia el nivel de un usuario", "pt-BR": "Altera o nível de um usuário"},
    },
    "warn_reset": {
        "name":        {"es-ES": "resetear_advertencias",              "pt-BR": "resetar_advertencias"},
        "description": {"es-ES": "Resetea las advertencias de un usuario", "pt-BR": "Reseta as advertências de um usuário"},
    },
}


class CustomCommandTree(app_commands.CommandTree):
    async def translate(self, string, locale, context):
        cmd_name = str(string)
        loc_data = COMMAND_LOCALIZATION.get(cmd_name)
        if not loc_data:
            return None
        str_locale = str(locale)
        if context.location == app_commands.TranslationContextLocation.command_name:
            return loc_data["name"].get(str_locale)
        if context.location == app_commands.TranslationContextLocation.command_description:
            return loc_data["description"].get(str_locale)
        return None


class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(tree_cls=CustomCommandTree, **kwargs)


intents = discord.Intents.all()
bot     = MyBot(command_prefix=["F!", "f!"], intents=intents)

# ─────────────────────────────────────────────
#  HELPERS DE TRADUCCIÓN
# ─────────────────────────────────────────────

async def translate_text(text: str, lang: str) -> str:
    tl  = LANG_MAP.get(lang, "en")
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "auto", "tl": tl, "dt": "t", "q": text}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params) as r:
                data = await r.json(content_type=None)
                return "".join(x[0] for x in data[0])
    except Exception:
        return text


async def resolve_lang(user_id: int, discord_locale=None) -> str:
    saved = get_user_lang(user_id)
    if saved != "AUTO":
        return saved
    if discord_locale:
        loc = str(discord_locale)
        if loc.startswith("es"):
            return "ES"
        if loc.startswith("pt"):
            return "PT"
    return "EN"


async def tr_i(interaction: discord.Interaction, text: str) -> str:
    lang = await resolve_lang(interaction.user.id, interaction.locale)
    return await translate_text(text, lang)


async def tr_ctx(ctx: commands.Context, text: str) -> str:
    lang = await resolve_lang(ctx.author.id)
    return await translate_text(text, lang)


def parse_timespan(time_str: str) -> datetime.timedelta | None:
    m = re.match(r"(\d+)([smhd])", (time_str or "").lower())
    if not m:
        return None
    amount, unit = int(m.group(1)), m.group(2)
    return {"s": datetime.timedelta(seconds=amount),
            "m": datetime.timedelta(minutes=amount),
            "h": datetime.timedelta(hours=amount),
            "d": datetime.timedelta(days=amount)}[unit]

# ─────────────────────────────────────────────
#  TICKET DATA HELPERS
# ─────────────────────────────────────────────

def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"count": 35, "channels": {}}
    with open(DATA_FILE) as f:
        try:
            d = json.load(f)
            d.setdefault("channels", {})
            if d.get("count", 0) < 35:
                d["count"] = 35
            return d
        except Exception:
            return {"count": 35, "channels": {}}

def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_history(data: list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ─────────────────────────────────────────────
#  LEVEL-UP EMBED
# ─────────────────────────────────────────────

async def send_level_up_embed(user: discord.Member, level: int, channel, *, via_command=False):
    tmpl = get_setting("levelup_msg") or "🎉 {user} has reached level {level}!"
    text = tmpl.replace("{user}", user.mention).replace("{level}", str(level))
    if via_command:
        text += "\n`[Leveled up via command]`"
    embed = discord.Embed(title="📈 Level Up!", description=text, color=0x00FFCC)
    av    = user.avatar.url if user.avatar else user.default_avatar.url
    embed.set_thumbnail(url=av)
    embed.add_field(name="Usuario",       value=user.name, inline=True)
    embed.add_field(name="Nivel actual",  value=str(level), inline=True)
    embed.set_footer(text="Level System")
    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass

# ─────────────────────────────────────────────
#  MODALES DE TICKET
# ─────────────────────────────────────────────

class AllianceModal(Modal):
    def __init__(self, lang: str):
        titles = {"EN": "Alliance Application", "ES": "Solicitud de Alianza", "PT": "Solicitação de Aliança"}
        super().__init__(title=titles.get(lang, titles["EN"]))
        self.lang = lang
        self.members = TextInput(label={"EN": "How many members?",         "ES": "¿Cuántos miembros?",           "PT": "Quantos membros?"}.get(lang, "How many members?"), max_length=50)
        self.active  = TextInput(label={"EN": "Community active? [Y/N]",   "ES": "¿Activa? [Sí/No]",             "PT": "Ativa? [Sim/Não]"}.get(lang, "Active?"), max_length=10)
        self.healthy = TextInput(label={"EN": "Community healthy? [Y/N]",  "ES": "¿Sana? [Sí/No]",               "PT": "Saudável? [Sim/Não]"}.get(lang, "Healthy?"), max_length=10)
        self.topic   = TextInput(label={"EN": "What is your server about?","ES": "¿De qué trata tu servidor?",   "PT": "Sobre o que é o servidor?"}.get(lang, "Topic?"), max_length=200)
        for item in (self.members, self.active, self.healthy, self.topic):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        res = {"EN": f"Form submitted — staff will reply shortly. <@&{STAFF_ROLE_ID}>",
               "ES": f"Formulario enviado. El staff te responderá pronto. <@&{STAFF_ROLE_ID}>",
               "PT": f"Formulário enviado. A staff responderá em breve. <@&{STAFF_ROLE_ID}>"}
        await interaction.response.send_message(res.get(self.lang, res["EN"]))
        staff_ch = bot.get_channel(STAFF_CHANNEL_ID)
        if staff_ch:
            e = discord.Embed(title="Alliance Request", color=discord.Color.blue())
            e.add_field(name="User",    value=interaction.user.mention, inline=False)
            e.add_field(name="Members", value=self.members.value,       inline=True)
            e.add_field(name="Active",  value=self.active.value,        inline=True)
            e.add_field(name="Healthy", value=self.healthy.value,       inline=True)
            e.add_field(name="Topic",   value=self.topic.value,         inline=False)
            await staff_ch.send(content=f"<@&{STAFF_ROLE_ID}>", embed=e)


class ReportUserModal(Modal):
    def __init__(self, lang: str):
        titles = {"EN": "Report User", "ES": "Reportar Usuario", "PT": "Denunciar Usuário"}
        super().__init__(title=titles.get(lang, titles["EN"]))
        self.lang = lang
        self.user_report = TextInput(label={"EN": "Who do you want to report?", "ES": "¿A quién reportas?", "PT": "Quem você denuncia?"}.get(lang, "Who?"))
        self.reason      = TextInput(label={"EN": "Reason?", "ES": "¿Motivo?", "PT": "Motivo?"}.get(lang, "Reason?"), style=discord.TextStyle.paragraph)
        self.add_item(self.user_report)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        e = discord.Embed(title="User Report", color=discord.Color.red())
        e.add_field(name="Reported", value=self.user_report.value,    inline=False)
        e.add_field(name="Reason",   value=self.reason.value,         inline=False)
        e.add_field(name="Reporter", value=interaction.user.mention,  inline=False)
        await interaction.response.send_message(content=f"<@&{STAFF_ROLE_ID}> New user report.", embed=e)


class ReportStaffModal(Modal):
    def __init__(self, lang: str):
        titles = {"EN": "Report Staff", "ES": "Reportar Staff", "PT": "Denunciar Staff"}
        super().__init__(title=titles.get(lang, titles["EN"]))
        self.lang = lang
        self.staff_report = TextInput(label={"EN": "Which staff member?",               "ES": "¿Qué staff reportas?",        "PT": "Qual staff denuncia?"}.get(lang, "Who?"))
        self.reason       = TextInput(label={"EN": "Reason?",                           "ES": "¿Motivo?",                     "PT": "Motivo?"}.get(lang, "Reason?"), style=discord.TextStyle.paragraph)
        self.gravity      = TextInput(label={"EN": "Severity? [Low/Medium/High]",       "ES": "¿Gravedad? [Poco/Medio/Muy]",  "PT": "Gravidade? [Baixa/Média/Alta]"}.get(lang, "Severity?"), max_length=30)
        self.sanction     = TextInput(label={"EN": "Suggested sanction? [Mute/Ban/Warn]","ES": "¿Sanción sugerida?",           "PT": "Punição? [Mute/Ban/Warn]"}.get(lang, "Sanction?"), max_length=20)
        for item in (self.staff_report, self.reason, self.gravity, self.sanction):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        e = discord.Embed(title="Staff Report", color=discord.Color.dark_red())
        e.add_field(name="Staff Reported",     value=self.staff_report.value, inline=False)
        e.add_field(name="Reason",             value=self.reason.value,       inline=False)
        e.add_field(name="Severity",           value=self.gravity.value,      inline=True)
        e.add_field(name="Suggested Sanction", value=self.sanction.value,     inline=True)
        e.add_field(name="Reporter",           value=interaction.user.mention, inline=False)
        await interaction.response.send_message(content=f"<@&{STAFF_ROLE_ID}> Staff report received.", embed=e)

# ─────────────────────────────────────────────
#  VISTAS DE TICKET
# ─────────────────────────────────────────────

class HelpSurveyModal(Modal):
    def __init__(self, lang: str):
        titles = {"EN": "Help Survey", "ES": "Encuesta de ayuda", "PT": "Pesquisa de ajuda"}
        super().__init__(title=titles.get(lang, titles["ES"]))
        self.lang = lang
        labels = {
            "problem": {"EN": "Describe your problem in detail", "ES": "Describe tu problema en detalle", "PT": "Descreva seu problema em detalhe"},
            "tried":   {"EN": "What have you already tried?",   "ES": "¿Qué ya intentaste?",             "PT": "O que voce ja tentou?"},
            "urgency": {"EN": "Urgency level [Low / Medium / High]", "ES": "Nivel de urgencia [Baja / Media / Alta]", "PT": "Nível de urgência [Baixa / Média / Alta]"},
        }
        self.problem = TextInput(label=labels["problem"].get(lang, labels["problem"]["ES"]), style=discord.TextStyle.paragraph, max_length=500)
        self.tried   = TextInput(label=labels["tried"].get(lang, labels["tried"]["ES"]),   style=discord.TextStyle.paragraph, max_length=300, required=False)
        self.urgency = TextInput(label=labels["urgency"].get(lang, labels["urgency"]["ES"]), max_length=20)
        self.add_item(self.problem)
        self.add_item(self.tried)
        self.add_item(self.urgency)

    async def on_submit(self, interaction: discord.Interaction):
        confirms = {"EN": "Thank you. I have your details and will help you shortly.", "ES": "Gracias. Ya tengo tu informacion y te ayudo en un momento.", "PT": "Obrigado. Ja tenho suas informacoes e te ajudo em breve."}
        await interaction.response.send_message(confirms.get(self.lang, confirms["ES"]), ephemeral=True)
        summary_labels = {"EN": "**Survey response:**", "ES": "**Respuesta de encuesta:**", "PT": "**Resposta da pesquisa:**"}
        msg = (
            f"{summary_labels.get(self.lang, summary_labels['ES'])}\n"
            f"- Problema: {self.problem.value}\n"
            f"- Ya intenté: {self.tried.value or '—'}\n"
            f"- Urgencia: {self.urgency.value}"
        )
        await interaction.channel.send(msg)


class SurveyRequestView(discord.ui.View):
    def __init__(self, lang: str):
        super().__init__(timeout=300)
        self.lang = lang
        labels = {"EN": "Fill out survey", "ES": "Rellenar encuesta", "PT": "Preencher pesquisa"}
        self.btn = discord.ui.Button(label=labels.get(lang, labels["ES"]), style=discord.ButtonStyle.primary)
        self.btn.callback = self._open_survey
        self.add_item(self.btn)

    async def _open_survey(self, interaction: discord.Interaction):
        await interaction.response.send_modal(HelpSurveyModal(self.lang))


class ContactStaffView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Contact Staff", style=discord.ButtonStyle.danger, custom_id="persistent:contact_staff")
    async def contact_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        data   = load_data()
        ch_key = str(interaction.channel.id)
        if ch_key in data["channels"]:
            data["channels"][ch_key]["ai_active"] = False
            save_data(data)
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"<@&{STAFF_ROLE_ID}> {interaction.user.mention} ha solicitado asistencia humana.")


class TicketLangView(discord.ui.View):
    def __init__(self, category: str):
        super().__init__(timeout=300)
        self.category = category

    async def _proceed(self, interaction: discord.Interaction, lang: str):
        data   = load_data()
        ch_key = str(interaction.channel.id)
        if ch_key in data["channels"]:
            data["channels"][ch_key]["language"] = lang
            save_data(data)

        if self.category == "Alliance":
            await interaction.response.send_modal(AllianceModal(lang))
        elif self.category == "Report User":
            await interaction.response.send_modal(ReportUserModal(lang))
        elif self.category == "Report Staff":
            await interaction.response.send_modal(ReportStaffModal(lang))
        elif self.category == "Help":
            lang_confirm = {
                "EN": "✅ Language set to **English**.",
                "ES": "✅ Idioma establecido en **Español**.",
                "PT": "✅ Idioma definido como **Português**.",
            }
            await interaction.response.edit_message(content=lang_confirm[lang], view=None)

            u = interaction.user.mention
            greetings = {
                "EN": [
                    f"Hello {u}. I'm the support staff for this server. Tell me what's going on and I'll do my best to help. If you'd rather talk to a real person, use **Contact Staff**.",
                    f"Welcome {u}. I'm here to help. Describe your issue and I'll take care of it. If you need a staff member, the **Contact Staff** button is right above.",
                    f"Hi {u}. What can I help you with today? Describe your situation and I'll get right on it.",
                    f"Hello {u}. Glad you opened a ticket. Tell me what happened and I'll try to sort it out. Need a real person? Use **Contact Staff** anytime.",
                ],
                "ES": [
                    f"Hola {u}. Soy el soporte del servidor. Cuéntame qué está pasando y haré lo posible por ayudarte. Si prefieres hablar con alguien del staff, presiona **Contact Staff**.",
                    f"Hola {u}. Estoy aquí para ayudarte. Describe tu problema y me encargo. Si necesitas un miembro del staff, el botón **Contact Staff** está arriba.",
                    f"Hola {u}. En qué te puedo ayudar hoy? Cuéntame tu situación y me pongo en ello.",
                    f"Hola {u}. Dime qué pasó y veo cómo ayudarte. Necesitas a alguien real? Usa **Contact Staff** cuando quieras.",
                ],
                "PT": [
                    f"Ola {u}. Sou o suporte do servidor. Me conte o que esta acontecendo e farei o possivel para ajuda-lo. Se preferir falar com alguem da equipe, pressione **Contact Staff**.",
                    f"Bem-vindo {u}. Estou aqui para ajudar. Descreva seu problema e eu cuido disso. Se precisar de um membro da equipe, o botao **Contact Staff** esta acima.",
                    f"Oi {u}. Em que posso ajudar hoje? Me conte sua situacao e vou me encarregar.",
                ],
            }
            await interaction.channel.send(content=random.choice(greetings[lang]), view=ContactStaffView())

    @discord.ui.button(label="English",   style=discord.ButtonStyle.secondary, emoji="🇺🇸")
    async def lang_en(self, i, b): await self._proceed(i, "EN")

    @discord.ui.button(label="Español",   style=discord.ButtonStyle.secondary, emoji="🇪🇸")
    async def lang_es(self, i, b): await self._proceed(i, "ES")

    @discord.ui.button(label="Português", style=discord.ButtonStyle.secondary, emoji="🇧🇷")
    async def lang_pt(self, i, b): await self._proceed(i, "PT")


class TranslateView(discord.ui.View):
    def __init__(self, text: str):
        super().__init__(timeout=None)
        self.text = text

    @discord.ui.button(label="English",   style=discord.ButtonStyle.primary)
    async def en(self, i, b): await i.response.send_message(await translate_text(self.text, "EN"), ephemeral=True)

    @discord.ui.button(label="Español",   style=discord.ButtonStyle.primary)
    async def es(self, i, b): await i.response.send_message(await translate_text(self.text, "ES"), ephemeral=True)

    @discord.ui.button(label="Português", style=discord.ButtonStyle.primary)
    async def pt(self, i, b): await i.response.send_message(await translate_text(self.text, "PT"), ephemeral=True)


class HistoryView(discord.ui.View):
    PER_PAGE = 5

    def __init__(self, history: list):
        super().__init__(timeout=120)
        self.history = history
        self.page    = 0

    def _max_page(self):
        return max(1, (len(self.history) - 1) // self.PER_PAGE + 1)

    def _embed(self):
        e     = discord.Embed(title="📜 Historial de Tickets Cerrados", color=0xFFFFFF)
        start = self.page * self.PER_PAGE
        rows  = self.history[start:start + self.PER_PAGE]
        if not rows:
            e.description = "No hay tickets cerrados."
            return e
        lines = []
        for r in rows:
            lines.append(
                f"**Creado por:** {r.get('created_by','?')} · "
                f"**Cerrado por:** {r.get('closed_by','?')} · "
                f"**Reclamado por:** {r.get('claimed_by','None')}"
            )
            if r.get("reason"):
                lines.append(f"> Motivo: {r['reason']}")
            lines.append("")
        e.description = "\n".join(lines)
        e.set_footer(text=f"Página {self.page + 1} / {self._max_page()}")
        return e

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, i, b):
        if self.page > 0:
            self.page -= 1
        await i.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(emoji="❎", style=discord.ButtonStyle.danger)
    async def close(self, i, b):
        await i.message.delete()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def nxt(self, i, b):
        if self.page < self._max_page() - 1:
            self.page += 1
        await i.response.edit_message(embed=self._embed(), view=self)


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Alliance",     style=discord.ButtonStyle.primary)
    async def alliance(self,    i, b): await create_ticket(i, "Alliance")

    @discord.ui.button(label="Help",         style=discord.ButtonStyle.primary)
    async def help(self,        i, b): await create_ticket(i, "Help")

    @discord.ui.button(label="Report User",  style=discord.ButtonStyle.danger)
    async def report_user(self, i, b): await create_ticket(i, "Report User")

    @discord.ui.button(label="Report Staff", style=discord.ButtonStyle.danger)
    async def report_staff(self,i, b): await create_ticket(i, "Report Staff")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green, custom_id="persistent:create_ticket")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        titles = {"EN": "Support System", "ES": "Sistema de Soporte", "PT": "Sistema de Suporte"}
        descs  = {"EN": "What type of ticket do you need?", "ES": "¿Qué tipo de ticket necesitas?", "PT": "Que tipo de ticket você precisa?"}
        lang   = await resolve_lang(interaction.user.id, interaction.locale)
        await interaction.response.send_message(
            embed=discord.Embed(title=titles.get(lang, titles["EN"]), description=descs.get(lang, descs["EN"]), color=discord.Color.blue()),
            view=CategoryView(),
            ephemeral=True,
        )


class CloseReasonModal(Modal):
    def __init__(self, lang: str = "EN"):
        titles = {"EN": "Close Ticket with Reason", "ES": "Cerrar Ticket con Motivo", "PT": "Fechar Ticket com Motivo"}
        super().__init__(title=titles.get(lang, titles["EN"]))
        self.lang = lang
        labels = {"EN": "Reason", "ES": "Motivo", "PT": "Motivo"}
        placeholders = {"EN": "Write the reason…", "ES": "Escribe el motivo…", "PT": "Escreva o motivo…"}
        self.reason_input = TextInput(
            label=labels.get(lang, labels["EN"]),
            placeholder=placeholders.get(lang, placeholders["EN"]),
            required=True,
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await _execute_close(interaction, reason=self.reason_input.value)


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim",              style=discord.ButtonStyle.green,     custom_id="persistent:ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id in WHITELIST_ROLES for r in interaction.user.roles):
            msgs = {"EN": "Only authorized staff can claim this ticket.", "ES": "Solo el staff autorizado puede reclamar este ticket.", "PT": "Somente staff autorizado pode reivindicar este ticket."}
            lang = await resolve_lang(interaction.user.id, interaction.locale)
            return await interaction.response.send_message(f"❌ {msgs.get(lang, msgs['EN'])}", ephemeral=True)
        data   = load_data()
        ch_key = str(interaction.channel.id)
        if ch_key in data["channels"]:
            data["channels"][ch_key]["claimed_by"] = interaction.user.name
            data["channels"][ch_key]["ai_active"]  = False
            save_data(data)
        button.disabled = True
        await interaction.response.edit_message(view=self)
        lang = await resolve_lang(interaction.user.id, interaction.locale)
        msgs = {"EN": f"Ticket claimed by {interaction.user.mention}", "ES": f"Ticket reclamado por {interaction.user.mention}", "PT": f"Ticket reivindicado por {interaction.user.mention}"}
        await interaction.channel.send(msgs.get(lang, msgs["EN"]))

    @discord.ui.button(label="Close",              style=discord.ButtonStyle.danger,    custom_id="persistent:ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await _execute_close(interaction)

    @discord.ui.button(label="Close with Reason",  style=discord.ButtonStyle.secondary,  custom_id="persistent:ticket_close_reason")
    async def close_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
        lang = await resolve_lang(interaction.user.id, interaction.locale)
        await interaction.response.send_modal(CloseReasonModal(lang))


class DeleteChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="persistent:ticket_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        msgs = {"EN": "Deleting…", "ES": "Eliminando…", "PT": "Excluindo…"}
        lang = await resolve_lang(interaction.user.id, interaction.locale)
        await interaction.response.send_message(msgs.get(lang, msgs["EN"]), ephemeral=True)
        await asyncio.sleep(1)
        await interaction.channel.delete()

# ─────────────────────────────────────────────
#  CIERRE DE TICKET
# ─────────────────────────────────────────────

async def _execute_close(interaction: discord.Interaction, reason: str | None = None):
    channel = interaction.channel
    data    = load_data()
    ch_key  = str(channel.id)

    creator_id, creator_name, claimed_by = None, "Unknown", "None"
    if ch_key in data["channels"]:
        creator_id   = data["channels"][ch_key].get("creator_id")
        creator_name = data["channels"][ch_key].get("creator_name", "Unknown")
        claimed_by   = data["channels"][ch_key].get("claimed_by", "None")

    if creator_id:
        member = channel.guild.get_member(creator_id)
        if member:
            try:
                await channel.set_permissions(member, view_channel=False, send_messages=False)
            except discord.Forbidden:
                pass

    lang = await resolve_lang(interaction.user.id, interaction.locale)
    _closed_by = {
        "EN": f"Ticket closed by {interaction.user.mention}",
        "ES": f"Ticket cerrado por {interaction.user.mention}",
        "PT": f"Ticket fechado por {interaction.user.mention}",
    }
    _reason_lbl = {"EN": "Reason", "ES": "Motivo", "PT": "Motivo"}
    msg = _closed_by.get(lang, _closed_by["EN"])
    if reason:
        msg += f"\n**{_reason_lbl.get(lang, 'Reason')}:** {reason}"

    await channel.send(embed=discord.Embed(description=msg, color=0xFFFFFF))

    history = load_history()
    history.append({
        "created_by": creator_name,
        "closed_by":  interaction.user.name,
        "claimed_by": claimed_by,
        "reason":     reason,
        "date":       datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save_history(history)

    _del_titles = {"EN": "Delete Channel", "ES": "Eliminar Canal", "PT": "Excluir Canal"}
    _del_descs  = {
        "EN": "Click below to permanently delete this channel.",
        "ES": "Haz clic abajo para eliminar este canal permanentemente.",
        "PT": "Clique abaixo para excluir este canal permanentemente.",
    }
    e = discord.Embed(title=_del_titles.get(lang, _del_titles["EN"]), description=_del_descs.get(lang, _del_descs["EN"]), color=discord.Color.red())
    await channel.send(embed=e, view=DeleteChannelView())

# ─────────────────────────────────────────────
#  CREACIÓN DE TICKET
# ─────────────────────────────────────────────

async def create_ticket(interaction: discord.Interaction, category: str):
    await interaction.response.defer(ephemeral=True)
    data  = load_data()
    data["count"] += 1
    guild = interaction.guild

    staff_role = guild.get_role(STAFF_ROLE_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user:   discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            attach_files=True, embed_links=True, read_message_history=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True,
        ),
    }
    if staff_role:
        if category == "Report Staff":
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                attach_files=True, embed_links=True, read_message_history=True,
                manage_channels=False, manage_messages=False,
            )
        else:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                attach_files=True, embed_links=True, read_message_history=True,
                manage_channels=True, manage_messages=True,
            )

    channel = await guild.create_text_channel(
        name=f"ticket-{data['count']:03d}", overwrites=overwrites
    )

    data["channels"][str(channel.id)] = {
        "creator_id":   interaction.user.id,
        "creator_name": interaction.user.name,
        "claimed_by":   "None",
        "category":     category,
        "ai_active":    category == "Help",
        "language":     "EN",
    }
    save_data(data)

    lang = await resolve_lang(interaction.user.id, interaction.locale)

    _titles  = {"EN": "Support Ticket",        "ES": "Ticket de Soporte",    "PT": "Ticket de Suporte"}
    _descs   = {
        "EN": f"Welcome {interaction.user.mention}\nA staff member will assist you shortly.",
        "ES": f"Bienvenido {interaction.user.mention}\nUn miembro del staff te asistirá en breve.",
        "PT": f"Bem-vindo {interaction.user.mention}\nUm membro da equipe irá te atender em breve.",
    }
    _cat_lbl = {"EN": "Category",  "ES": "Categoría", "PT": "Categoria"}
    _cat_val = {
        "Alliance":     {"EN": "Alliance",     "ES": "Alianza",       "PT": "Aliança"},
        "Help":         {"EN": "Help",          "ES": "Ayuda",         "PT": "Ajuda"},
        "Report User":  {"EN": "Report User",   "ES": "Reportar Usuario", "PT": "Denunciar Usuário"},
        "Report Staff": {"EN": "Report Staff",  "ES": "Reportar Staff",   "PT": "Denunciar Staff"},
    }

    embed = discord.Embed(title=_titles.get(lang, _titles["EN"]), description=_descs.get(lang, _descs["EN"]), color=0xFFFFFF)
    embed.add_field(name=_cat_lbl.get(lang, _cat_lbl["EN"]), value=_cat_val.get(category, {}).get(lang, category), inline=False)

    await channel.send(embed=embed, view=TicketControlView())
    await channel.send("Select your language / Selecciona tu idioma / Selecione seu idioma:", view=TicketLangView(category))

    _created = {
        "EN": f"Channel created: {channel.mention}",
        "ES": f"Canal creado: {channel.mention}",
        "PT": f"Canal criado: {channel.mention}",
    }
    try:
        await interaction.edit_original_response(
            embed=discord.Embed(description=_created.get(lang, _created["EN"]), color=discord.Color.green()),
            view=None,
        )
    except Exception:
        await interaction.followup.send(_created.get(lang, _created["EN"]), ephemeral=True)

# ─────────────────────────────────────────────
#  SISTEMA DE ADVERTENCIAS POR LINKS
# ─────────────────────────────────────────────

async def handle_link_infraction(message: discord.Message):
    member = message.author
    try:
        await message.delete()
    except discord.Forbidden:
        pass

    warn_count = add_warning(member.id)
    mute_idx   = min(warn_count - 1, len(LINK_MUTE_LADDER) - 1)
    mute_time  = LINK_MUTE_LADDER[mute_idx]

    total_s = int(mute_time.total_seconds())
    if total_s < 60:
        duration_str = f"{total_s}s"
    elif total_s < 3600:
        duration_str = f"{total_s // 60}m"
    elif total_s < 86400:
        duration_str = f"{total_s // 3600}h"
    else:
        duration_str = f"{total_s // 86400}d"

    muted = False
    if warn_count <= MAX_WARNINGS:
        try:
            await member.timeout(mute_time, reason=f"Enlace externo — advertencia {warn_count}/{MAX_WARNINGS}")
            muted = True
        except discord.Forbidden:
            pass

    warn_bar = "🟥" * warn_count + "⬛" * (MAX_WARNINGS - warn_count)

    if warn_count >= MAX_WARNINGS:
        color   = discord.Color.dark_red()
        title   = "⛔ Advertencia máxima alcanzada"
        note    = "Has alcanzado el límite de advertencias. El staff revisará tu caso."
    else:
        color   = discord.Color.orange()
        title   = "⚠️ Advertencia — Enlace externo"
        note    = f"Silenciado por **{duration_str}**." if muted else "No se pudo silenciar (sin permisos)."

    e = discord.Embed(title=title, color=color)
    e.description = (
        f"{member.mention} ha enviado un enlace a otro servidor de Discord.\n\n"
        f"**Advertencias:** {warn_bar} `{warn_count}/{MAX_WARNINGS}`\n"
        f"{note}"
    )
    e.set_footer(text="Los links externos no están permitidos.")
    await message.channel.send(embed=e, delete_after=15)

    staff_ch = bot.get_channel(STAFF_CHANNEL_ID)
    if staff_ch:
        log_e = discord.Embed(title="🔗 Link externo detectado", color=discord.Color.orange())
        log_e.add_field(name="Usuario",      value=f"{member.mention} ({member})", inline=False)
        log_e.add_field(name="Canal",        value=message.channel.mention,         inline=True)
        log_e.add_field(name="Advertencias", value=f"`{warn_count}/{MAX_WARNINGS}`", inline=True)
        log_e.add_field(name="Mute aplicado",value=f"`{duration_str}`" if muted else "No", inline=True)
        await staff_ch.send(embed=log_e)

# ─────────────────────────────────────────────
#  EVENTO ON_MESSAGE
# ─────────────────────────────────────────────

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ── DM: responder captcha por texto ──
    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        entry   = pending_captchas.get(user_id)
        if entry:
            lang = get_user_lang(user_id)
            if lang == "AUTO":
                lang = "ES"
            # Ignorar espacios
            user_answer = message.content.strip().replace(" ", "").upper()
            if user_answer == entry["code"].upper():
                guild = bot.get_guild(entry["guild_id"])
                if guild:
                    member = guild.get_member(user_id)
                    if member:
                        await _grant_verified(
                            member, guild,
                            role_id=entry.get("role_id"),
                            unrole_id=entry.get("unrole_id"),
                        )
                        return
            else:
                if user_id not in OWNER_IDS:
                    pending_captchas.pop(user_id, None)
                    captcha_cooldowns[user_id] = time.time() + CAPTCHA_COOLDOWN
                mins = CAPTCHA_COOLDOWN // 60
                _msgs = {
                    "EN": f"Incorrect code. You must wait **{mins} minutes** before trying again." if user_id not in OWNER_IDS else "Incorrect code. Try again.",
                    "ES": f"Codigo incorrecto. Debes esperar **{mins} minutos** antes de intentarlo de nuevo." if user_id not in OWNER_IDS else "Codigo incorrecto. Intentalo de nuevo.",
                    "PT": f"Codigo incorreto. Voce deve aguardar **{mins} minutos** antes de tentar novamente." if user_id not in OWNER_IDS else "Codigo incorreto. Tente novamente.",
                }
                await message.channel.send(_msgs.get(lang, _msgs["ES"]))
        return

    # ── Solo procesamos mensajes de servidor ──
    if not message.guild:
        return

    member        = message.author
    content_lower = message.content.lower()
    is_owner      = member.id in OWNER_IDS
    is_staff      = (
        is_owner
        or any(r.id in WHITELIST_ROLES for r in getattr(member, "roles", []))
    )

    # ── Filtro @everyone: NADIE puede usarlo salvo OWNER ──
    if "@everyone" in message.content and not is_owner:
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        entry = _increment_infraction(everyone_infractions, member.id)
        if entry["count"] >= 2:
            await apply_new_infraction_mute(member, everyone_infractions, message.channel, "Uso de @everyone")
        else:
            # Primera vez: solo avisar
            e = discord.Embed(
                title="🚫 @everyone no permitido",
                description=f"{member.mention}, el uso de @everyone no está permitido para miembros.",
                color=discord.Color.red(),
            )
            try:
                await message.channel.send(embed=e, delete_after=10)
            except Exception:
                pass
        return

    # ── Filtro palabras prohibidas: NADIE salvo OWNER ──
    if not is_owner:
        found_phrase = None
        for phrase in FORBIDDEN_PHRASES:
            if phrase in content_lower:
                found_phrase = phrase
                break

        if found_phrase:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            entry = _increment_infraction(forbidden_infractions, member.id)
            if entry["count"] >= 2:
                await apply_new_infraction_mute(member, forbidden_infractions, message.channel, f"Palabra/frase prohibida: {found_phrase}")
            else:
                # Primera vez: advertencia sin mute
                e = discord.Embed(
                    title="⚠️ Mensaje no permitido",
                    description=f"{member.mention}, ese contenido no está permitido en este servidor.",
                    color=discord.Color.orange(),
                )
                try:
                    await message.channel.send(embed=e, delete_after=10)
                except Exception:
                    pass
            return

    # ── Filtro links externos ──
    if not is_staff and any(link in content_lower for link in BLOCKED_LINKS):
        await handle_link_infraction(message)
        return

    # ── XP por chat (fuera de tickets) ──
    if not message.channel.name.startswith("ticket-"):
        user_id = str(member.id)
        now     = int(time.time())
        cursor.execute("SELECT xp, level, lastMsg FROM users WHERE userId=?", (user_id,))
        row = cursor.fetchone()
        xp, level, last_msg = row if row else (0, 0, 0)
        if now - last_msg >= 60:
            xp += random.randint(10, 25)
            leveled_up = False
            while xp >= xp_needed(level):
                xp    -= xp_needed(level)
                level += 1
                leveled_up = True
            if row:
                cursor.execute("UPDATE users SET xp=?,level=?,lastMsg=? WHERE userId=?", (xp, level, now, user_id))
            else:
                cursor.execute("INSERT INTO users(userId,xp,level,lastMsg) VALUES(?,?,?,?)", (user_id, xp, level, now))
            conn.commit()
            if leveled_up and not xp_sleep:
                raw    = get_setting("levelup_channel")
                ch_id  = int(raw) if raw and raw.isdigit() else 0
                target = bot.get_channel(ch_id) if ch_id else message.channel
                if target:
                    await send_level_up_embed(member, level, target)

    # ── IA en tickets Help ──
    if message.channel.name.startswith("ticket-"):
        data   = load_data()
        ch_key = str(message.channel.id)
        ticket = data["channels"].get(ch_key, {})

        if ticket.get("category") == "Help" and ticket.get("ai_active", False):
            ticket_lang = ticket.get("language", "EN")
            creator_id  = ticket.get("creator_id")
            if is_staff and member.id != creator_id:
                await bot.process_commands(message)
                return

            words = set(content_lower.split())

            _OTHER_CATS = {
                "alliance":    {"alliance", "alianza", "aliança"},
                "Report User": {"reportar", "reporte", "report", "denunciar", "denuncia"},
                "Report Staff":{"staff", "moderador", "moderadora", "admin", "administrador", "mod"},
            }
            _detected_cat = None
            for _cat, _kws in _OTHER_CATS.items():
                if words & _kws:
                    _detected_cat = _cat
                    break
            if _detected_cat:
                _tickets_ch = "<#1503589089780170904>"
                _redirect = {
                    "ES": f"Al parecer tu problema consiste en otra categoria. Por favor ve al canal {_tickets_ch}, crea un ticket y selecciona la opcion **{_detected_cat}**.",
                    "EN": f"It seems your issue falls under a different category. Please go to {_tickets_ch}, open a ticket and select **{_detected_cat}**.",
                    "PT": f"Parece que seu problema e de outra categoria. Va ao canal {_tickets_ch}, crie um ticket e selecione **{_detected_cat}**.",
                }
                await message.channel.send(_redirect.get(ticket_lang, _redirect["ES"]))
                return

            msg_count = ticket.get("msg_count", 0) + 1
            data["channels"][ch_key]["msg_count"] = msg_count
            save_data(data)

            ticket_limit = 15
            if "msg_limit" not in ticket:
                data["channels"][ch_key]["msg_limit"] = ticket_limit
                save_data(data)

            if msg_count >= ticket_limit:
                data["channels"][ch_key]["ai_active"] = False
                save_data(data)
                escalate = {
                    "EN": [
                        f"I think at this point it's best to have a staff member take over. <@&{STAFF_ROLE_ID}>",
                        f"Let me pass this over to the team so they can help you directly. <@&{STAFF_ROLE_ID}>",
                        f"I've done what I can from my end. A staff member will take it from here. <@&{STAFF_ROLE_ID}>",
                        f"At this point it would be best to speak with someone from the team directly. <@&{STAFF_ROLE_ID}>",
                    ],
                    "ES": [
                        f"Creo que lo mejor en este punto es que un miembro del staff tome el caso. <@&{STAFF_ROLE_ID}>",
                        f"Voy a pasarle esto al equipo para que te ayuden directamente. <@&{STAFF_ROLE_ID}>",
                        f"He hecho lo que puedo desde mi lado. Un miembro del staff continuara desde aqui. <@&{STAFF_ROLE_ID}>",
                        f"En este punto seria mejor que hablaras con alguien del equipo directamente. <@&{STAFF_ROLE_ID}>",
                    ],
                    "PT": [
                        f"Acho que o melhor agora e que um membro da equipe assuma o caso. <@&{STAFF_ROLE_ID}>",
                        f"Vou passar isso para a equipe para que possam te ajudar diretamente. <@&{STAFF_ROLE_ID}>",
                        f"Fiz o que pude da minha parte. Um membro da equipe continuara a partir daqui. <@&{STAFF_ROLE_ID}>",
                    ],
                }
                await message.channel.send(random.choice(escalate.get(ticket_lang, escalate["ES"])))
                return

            auto_reply = None
            for keywords, replies in AUTO_RESPONSES:
                if words & keywords:
                    variations = replies.get(ticket_lang) or replies.get("ES", [])
                    if variations:
                        auto_reply = random.choice(variations)
                    break

            if auto_reply:
                await message.channel.send(auto_reply)
            else:
                async with message.channel.typing():
                    _lang_word = "español" if ticket_lang == "ES" else "inglés" if ticket_lang == "EN" else "portugués"
                    system_prompt = (
                        f"Eres un miembro del STAFF de soporte de este servidor de Discord llamado '{bot.user.display_name}'.\n"
                        f"REGLAS ABSOLUTAS:\n"
                        f"1. NUNCA uses emojis.\n"
                        f"2. NUNCA inventes canales, roles ni menciones.\n"
                        f"3. NUNCA salgas de tu papel de staff.\n"
                        f"4. NUNCA menciones que eres una IA.\n"
                        f"5. Si no sabes la respuesta, responde EXACTAMENTE: [CONTACT_STAFF]\n"
                        f"6. Responde SIEMPRE en {_lang_word}.\n"
                        f"7. Máximo 3 oraciones por respuesta.\n\n"
                        f"Usuario: {member.display_name} | Mensaje {msg_count}/15.\n\n"
                        f"CANALES REALES:\n"
                        f"- Verificacion: <#1503459513175380029>\n"
                        f"- Grupo de juegos/condos: <#1503597582688194690>\n"
                        f"- Canal de keys: <#1503597637067079721>\n"
                        f"- Canal de usuario condos: <#1509671797983940658>\n"
                        f"- Noticias: <#1503591370953064488>\n"
                        f"- Reglas: <#1503459081619243058>\n"
                        f"- Tickets: <#1503589089780170904>\n\n"
                        f"Si el usuario solicita hablar con un humano, responde EXACTAMENTE: [CONTACT_STAFF]\n"
                        f"Si necesitas más info, responde EXACTAMENTE: [SEND_SURVEY]"
                    )
                    try:
                        full_prompt = f"{system_prompt}\n\nUsuario: {message.content}"
                        if _AI_BACKEND == "genai" and ai_client:
                            resp = await ai_client.aio.models.generate_content(
                                model="gemini-2.5-flash-lite",
                                contents=full_prompt,
                            )
                            text = resp.text.strip()
                        elif _AI_BACKEND == "legacy":
                            loop  = asyncio.get_event_loop()
                            model = _legacy_genai.GenerativeModel("gemini-1.5-flash")
                            resp  = await loop.run_in_executor(None, model.generate_content, full_prompt)
                            text  = resp.text.strip()
                        else:
                            raise RuntimeError("Sin backend de IA disponible")

                        if "[CONTACT_STAFF]" in text:
                            data["channels"][ch_key]["ai_active"] = False
                            save_data(data)
                            transfer_msgs = {
                                "EN": f"Let me get someone from the team. <@&{STAFF_ROLE_ID}>",
                                "ES": f"Dejame llamar a alguien del equipo. <@&{STAFF_ROLE_ID}>",
                                "PT": f"Deixa eu chamar alguem da equipe. <@&{STAFF_ROLE_ID}>",
                            }
                            await message.channel.send(transfer_msgs.get(ticket_lang, transfer_msgs["ES"]))
                        elif "[SEND_SURVEY]" in text:
                            survey_msgs = {
                                "EN": "To help you better, please fill out this short form:",
                                "ES": "Para ayudarte mejor, por favor rellena este formulario corto:",
                                "PT": "Para te ajudar melhor, por favor preencha este formulario curto:",
                            }
                            await message.channel.send(
                                survey_msgs.get(ticket_lang, survey_msgs["ES"]),
                                view=SurveyRequestView(ticket_lang),
                            )
                        else:
                            await message.channel.send(text)

                    except Exception as err:
                        print(f"[AI error] {err}")
                        data["channels"][ch_key]["ai_active"] = False
                        save_data(data)
                        fallback = {
                            "EN": f"Sorry, I'm having some trouble right now. Let me get a staff member. <@&{STAFF_ROLE_ID}>",
                            "ES": f"Disculpa, estoy teniendo problemas. Déjame llamar a alguien del staff. <@&{STAFF_ROLE_ID}>",
                            "PT": f"Desculpe, estou com problemas. Deixa eu chamar alguém da equipe. <@&{STAFF_ROLE_ID}>",
                        }
                        await message.channel.send(fallback.get(ticket_lang, fallback["ES"]))

    await bot.process_commands(message)

# ─────────────────────────────────────────────
#  REACTION ROLES
# ─────────────────────────────────────────────

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    guild  = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    if not member or member.bot:
        return

    cursor.execute(
        "SELECT role_id, requires_captcha FROM reaction_roles WHERE message_id=? AND emoji=?",
        (payload.message_id, str(payload.emoji))
    )
    row = cursor.fetchone()
    if not row:
        return

    role_id, requires_captcha = row

    if requires_captcha:
        lang = get_user_lang(member.id)
        if lang == "AUTO":
            lang = "ES"

        # Buscar unrole_id en verification_panels
        cursor.execute("SELECT unrole_id FROM verification_panels WHERE message_id=?", (payload.message_id,))
        vp_row   = cursor.fetchone()
        unrole_id = vp_row[0] if vp_row else None

        if role_id and is_verified(member.id):
            role = guild.get_role(role_id)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Ya verificado — re-asignacion")
                except discord.Forbidden:
                    pass
            return

        if member.id not in OWNER_IDS:
            cooldown_until = captcha_cooldowns.get(member.id)
            if cooldown_until and time.time() < cooldown_until:
                remaining = int(cooldown_until - time.time())
                mins, secs = divmod(remaining, 60)
                _msgs = {
                    "EN": f"You must wait **{mins}m {secs}s** before requesting a new captcha.",
                    "ES": f"Debes esperar **{mins}m {secs}s** antes de solicitar un nuevo captcha.",
                    "PT": f"Voce deve aguardar **{mins}m {secs}s** antes de solicitar um novo captcha.",
                }
                try:
                    await member.send(_msgs.get(lang, _msgs["ES"]))
                except discord.Forbidden:
                    pass
                return
            captcha_cooldowns.pop(member.id, None)

        if member.id in pending_captchas:
            _msgs = {
                "EN": "You already have a pending captcha. Check your direct messages.",
                "ES": "Ya tienes un captcha pendiente. Revisa tus mensajes directos.",
                "PT": "Voce ja tem um captcha pendente. Verifique suas mensagens diretas.",
            }
            try:
                await member.send(_msgs.get(lang, _msgs["ES"]))
            except discord.Forbidden:
                pass
            return

        asyncio.create_task(start_captcha(member, guild, role_id=role_id, unrole_id=unrole_id))
        return

    if role_id:
        role = guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
                log_ch = bot.get_channel(ROLES_LOG_CHANNEL_ID)
                if log_ch:
                    await log_ch.send(f"✅ {member.mention} recibió {role.mention} por reacción.")
            except discord.Forbidden:
                pass


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    cursor.execute(
        "SELECT role_id, requires_captcha FROM reaction_roles WHERE message_id=? AND emoji=?",
        (payload.message_id, str(payload.emoji))
    )
    row = cursor.fetchone()
    if not row:
        return

    role_id, requires_captcha = row[0], row[1]
    if requires_captcha:
        return
    if not role_id:
        return

    guild  = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    if member and not member.bot:
        role = guild.get_role(role_id)
        if role:
            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                pass

# ─────────────────────────────────────────────
#  GRUPOS DE SLASH COMMANDS
# ─────────────────────────────────────────────

class LanguageGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="language", description="Configuración de idioma de interfaz")

    @app_commands.command(name="set", description=app_commands.locale_str("set_language"))
    @app_commands.describe(language="Selecciona tu idioma preferido")
    @app_commands.choices(language=[
        app_commands.Choice(name="Automático (Discord App)", value="AUTO"),
        app_commands.Choice(name="English",   value="EN"),
        app_commands.Choice(name="Español",   value="ES"),
        app_commands.Choice(name="Português", value="PT"),
    ])
    async def set_language(self, interaction: discord.Interaction, language: str):
        set_user_lang(interaction.user.id, language)
        msgs = {
            "AUTO": "✅ Idioma en **automático** (según tu Discord).",
            "EN":   "✅ Interface language set to **English**.",
            "ES":   "✅ Idioma de interfaz cambiado a **Español**.",
            "PT":   "✅ Idioma da interface alterado para **Português**.",
        }
        await interaction.response.send_message(msgs[language], ephemeral=True)


class LevelGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="level", description="Sistema de niveles y XP")

    @app_commands.command(name="leaderboard", description=app_commands.locale_str("leaderboard"))
    async def leaderboard(self, interaction: discord.Interaction):
        cursor.execute("SELECT userId, level FROM users ORDER BY level DESC LIMIT 10")
        rows  = cursor.fetchall()
        title = await tr_i(interaction, "🏆 Clasificación")
        lvl_t = await tr_i(interaction, "Nivel")
        e     = discord.Embed(title=title, color=0x3498DB)
        desc  = "\n".join(f"{i+1}. <@{uid}> — {lvl_t} {lvl}" for i, (uid, lvl) in enumerate(rows))
        e.description = desc or await tr_i(interaction, "Sin datos aún.")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="rank", description=app_commands.locale_str("rank"))
    async def rank(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        cursor.execute("SELECT xp, level FROM users WHERE userId=?", (str(target.id),))
        row    = cursor.fetchone()
        xp, level = row if row else (0, 0)
        needed = xp_needed(level)
        bar    = get_progress_bar(xp, needed)
        title  = await tr_i(interaction, f"📊 Perfil de {target.name}")
        e      = discord.Embed(title=title, color=0x00FFCC)
        av     = target.avatar.url if target.avatar else target.default_avatar.url
        e.set_thumbnail(url=av)
        e.add_field(name="Nivel",    value=f"**{level}**",       inline=True)
        e.add_field(name="XP",       value=f"`{xp} / {needed}`", inline=True)
        e.add_field(name="Progreso", value=bar,                    inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="xp-add", description=app_commands.locale_str("xp_add"))
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario objetivo", amount="Cantidad de XP a añadir")
    async def xp_add(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        if amount <= 0:
            return await interaction.response.send_message("❌ La cantidad debe ser mayor a 0.", ephemeral=True)
        uid = str(user.id)
        cursor.execute("SELECT xp, level FROM users WHERE userId=?", (uid,))
        row = cursor.fetchone()
        xp, level = row if row else (0, 0)
        if not row:
            cursor.execute("INSERT INTO users(userId,xp,level,lastMsg) VALUES(?,?,?,?)", (uid, 0, 0, 0))
        xp += amount
        leveled_up = False
        while xp >= xp_needed(level):
            xp    -= xp_needed(level)
            level += 1
            leveled_up = True
        cursor.execute("UPDATE users SET xp=?,level=? WHERE userId=?", (xp, level, uid))
        conn.commit()
        await interaction.response.send_message(f"✅ Añadido {amount} XP a {user.name}.", ephemeral=True)
        if leveled_up:
            raw    = get_setting("levelup_channel")
            ch_id  = int(raw) if raw and raw.isdigit() else 0
            target = bot.get_channel(ch_id) if ch_id else interaction.channel
            if target:
                await send_level_up_embed(user, level, target)

    @app_commands.command(name="xp-pause", description=app_commands.locale_str("xp_pause"))
    @app_commands.default_permissions(administrator=True)
    async def xp_pause(self, interaction: discord.Interaction):
        global xp_sleep
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        xp_sleep = True
        await interaction.response.send_message("😴 Alertas de subida de nivel pausadas.")

    @app_commands.command(name="xp-resume", description=app_commands.locale_str("xp_resume"))
    @app_commands.default_permissions(administrator=True)
    async def xp_resume(self, interaction: discord.Interaction):
        global xp_sleep
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        xp_sleep = False
        await interaction.response.send_message("🔄 Alertas de subida de nivel activadas.")

    @app_commands.command(name="xp-set", description=app_commands.locale_str("xp_set"))
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario objetivo", level="Nuevo nivel")
    async def xp_set(self, interaction: discord.Interaction, user: discord.Member, level: int):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        cursor.execute("UPDATE users SET level=?,xp=0 WHERE userId=?", (level, str(user.id)))
        conn.commit()
        await interaction.response.send_message(f"✅ {user.name} ahora está en nivel {level}.", ephemeral=True)
        raw    = get_setting("levelup_channel")
        ch_id  = int(raw) if raw and raw.isdigit() else 0
        target = bot.get_channel(ch_id) if ch_id else interaction.channel
        if target:
            await send_level_up_embed(user, level, target, via_command=True)


class RoleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="role", description="Gestión de roles")

    @app_commands.command(name="all", description=app_commands.locale_str("role_all"))
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol a asignar a todos")
    async def role_all(self, interaction: discord.Interaction, role: discord.Role):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        await interaction.response.defer(thinking=True)

        members    = [m for m in interaction.guild.members if role not in m.roles and not m.bot]
        total      = len(members)
        done       = 0
        failed     = 0
        start_time = time.time()

        if total == 0:
            return await interaction.followup.send("✅ Todos los miembros ya tienen este rol.")

        status_msg = await interaction.followup.send(
            embed=discord.Embed(
                title="Asignando rol…",
                description=f"Progreso: `0 / {total}` ▱▱▱▱▱▱▱▱▱▱  0%",
                color=0x3498DB,
            )
        )

        for i, m in enumerate(members):
            try:
                await m.add_roles(role, reason=f"role-all por {interaction.user}")
                done += 1
            except Exception:
                failed += 1

            if (i + 1) % 10 == 0 or (i + 1) == total:
                pct     = (i + 1) / total
                blocks  = int(pct * 10)
                bar     = "▰" * blocks + "▱" * (10 - blocks)
                elapsed = int(time.time() - start_time)
                eta     = int((total - i - 1) * (elapsed / (i + 1))) if i > 0 else "?"
                done_txt = "✅ ¡Asignación completa!" if (i + 1) == total else "Asignando rol…"
                e = discord.Embed(
                    title=done_txt,
                    description=(
                        f"Progreso: `{i+1} / {total}` {bar}  {int(pct*100)}%\n"
                        f"✅ Asignados: **{done}**  ❌ Fallidos: **{failed}**\n"
                        f"⏱ Tiempo: {elapsed}s" +
                        (f"  |  ETA: ~{eta}s" if (i + 1) < total else "")
                    ),
                    color=0x00CC66 if (i + 1) == total else 0x3498DB,
                )
                await status_msg.edit(embed=e)

    @app_commands.command(name="reaction", description="Agrega un emoji a un mensaje con rol y/o captcha opcionales")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        emoji="Emoji a agregar",
        message="Texto del nuevo mensaje (ignorado si usas message_id)",
        message_id="ID de mensaje existente al que agregar el emoji",
        role="Rol que se dará al reaccionar (opcional)",
        captcha="¿Requerir captcha antes de dar el rol?",
    )
    async def reaction_role(
        self,
        interaction: discord.Interaction,
        emoji: str,
        message: str = None,
        message_id: str = None,
        role: discord.Role = None,
        captcha: bool = False,
    ):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)

        if not message and not message_id:
            return await interaction.response.send_message(
                "❌ Debes indicar el texto de un nuevo mensaje (`message`) "
                "**o** el ID de un mensaje existente (`message_id`).",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        if message_id:
            try:
                target_msg = await interaction.channel.fetch_message(int(message_id))
            except Exception:
                return await interaction.followup.send("❌ No encontré ese mensaje en este canal.", ephemeral=True)
        else:
            target_msg = await interaction.channel.send(message)

        try:
            await target_msg.add_reaction(emoji)
        except discord.HTTPException:
            if not message_id:
                await target_msg.delete()
            return await interaction.followup.send("❌ Emoji inválido.", ephemeral=True)

        role_id = role.id if role else None
        cursor.execute(
            "REPLACE INTO reaction_roles(message_id, emoji, role_id, requires_captcha) VALUES(?,?,?,?)",
            (target_msg.id, emoji, role_id, 1 if captcha else 0),
        )
        conn.commit()

        parts = []
        if role:
            parts.append(f"rol **{role.name}**")
        if captcha:
            parts.append("captcha requerido 🔐")
        if not parts:
            parts.append("solo emoji (sin rol, sin captcha)")

        await interaction.followup.send(
            f"✅ Emoji {emoji} registrado en [{target_msg.id}]({target_msg.jump_url}) → {', '.join(parts)}",
            ephemeral=True,
        )


class SendGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="send", description="Enviar mensajes como el bot")

    @app_commands.command(name="text", description="Envía un mensaje o embed a un canal")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        text="Contenido del mensaje",
        channel="Canal de destino",
        color="Color hex del embed (ej. FF0000). Vacío = texto plano.",
    )
    async def send_text(self, interaction: discord.Interaction, text: str, channel: discord.TextChannel, color: str = None):
        if interaction.user.id not in OWNER_IDS and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        try:
            if color:
                try:
                    color_val = int(color.lstrip("#"), 16)
                except ValueError:
                    return await interaction.response.send_message("❌ Color inválido. Ejemplo: `FF0000`", ephemeral=True)
                await channel.send(embed=discord.Embed(description=text, color=discord.Color(color_val)))
            else:
                await channel.send(text)
            await interaction.response.send_message(f"✅ Mensaje enviado a {channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sin permisos para escribir en ese canal.", ephemeral=True)


class TicketGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="ticket", description="Sistema de tickets de soporte")

    @app_commands.command(name="history", description=app_commands.locale_str("ticket_history"))
    @app_commands.default_permissions(administrator=True)
    async def ticket_history(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        view = HistoryView(load_history())
        await interaction.response.send_message(embed=view._embed(), view=view, ephemeral=True)

    @app_commands.command(name="panel", description=app_commands.locale_str("ticket_panel"))
    @app_commands.default_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        title = await tr_i(interaction, "📩 Sistema de Soporte")
        desc  = await tr_i(interaction, "Haz clic en el botón para abrir un ticket de soporte.")
        await interaction.channel.send(
            embed=discord.Embed(title=title, description=desc, color=discord.Color.blue()),
            view=TicketView(),
        )
        await interaction.response.send_message("✅ Panel enviado.", ephemeral=True)


CAPTCHA_OWNER_ID = 1450410095228747790


class SetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="set", description="Configuración del servidor")

    @app_commands.command(
        name="verification",
        description="Crea y envía un panel de verificación con captcha en el canal indicado",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Canal donde se enviará el panel de verificación",
        role="Rol que se asigna al pasar el captcha",
        mention="(Opcional) Rol a mencionar en el mensaje del panel",
        unrole="(Opcional) Rol que se ELIMINA al verificarse (no elimina el rol que se agrega, salvo que sean iguales)",
    )
    async def set_verification(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
        mention: discord.Role | None = None,
        unrole: discord.Role | None = None,
    ):
        if interaction.user.id != CAPTCHA_OWNER_ID:
            return await interaction.response.send_message(
                "❌ No tienes permiso para usar este comando.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        perms = channel.permissions_for(interaction.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return await interaction.followup.send(
                f"❌ No tengo permisos para enviar mensajes o embeds en {channel.mention}.", ephemeral=True
            )

        unrole_note = ""
        if unrole:
            if unrole.id == role.id:
                unrole_note = "\n*Nota: `unrole` es igual a `role`, por lo que no se eliminará ningún rol al verificarse.*"
            else:
                unrole_note = f"\n*Al verificarte se te eliminará el rol **{unrole.name}**.*"

        embed = discord.Embed(
            title="Server Verification",
            description=(
                "To gain access to the server you must complete a quick verification.\n\n"
                "**Click the button below** to receive a captcha image.\n"
                "Type the text shown in the image to get verified. **Spaces are ignored.**\n\n"
                f"Upon completing verification you will receive the **{role.name}** role."
                + (f"\n\nYou will lose the **{unrole.name}** role upon verification." if unrole and unrole.id != role.id else "")
            ),
            color=0x57F287,
        )
        embed.set_footer(text="If you fail the captcha you must wait 2 minutes before trying again.")

        try:
            panel_msg = await channel.send(
                content=mention.mention if mention else None,
                embed=embed,
                view=VerificationPanelView(),
            )
        except discord.HTTPException as exc:
            return await interaction.followup.send(f"❌ Error al enviar el panel: {exc}", ephemeral=True)

        # Registrar en reaction_roles y verification_panels
        cursor.execute(
            "REPLACE INTO reaction_roles(message_id, emoji, role_id, requires_captcha) VALUES(?,?,?,?)",
            (panel_msg.id, "__button__", role.id, 1),
        )
        cursor.execute(
            "REPLACE INTO verification_panels(message_id, role_id, unrole_id) VALUES(?,?,?)",
            (panel_msg.id, role.id, unrole.id if unrole and unrole.id != role.id else None),
        )
        conn.commit()

        summary = (
            f"✅ Panel de verificación enviado en {channel.mention}.\n"
            f"Rol que se asignará: **{role.name}**\n"
        )
        if unrole and unrole.id != role.id:
            summary += f"Rol que se eliminará: **{unrole.name}**\n"
        if mention:
            summary += f"Mención: {mention.mention}\n"
        summary += f"ID del mensaje: `{panel_msg.id}`"
        summary += unrole_note

        await interaction.followup.send(summary, ephemeral=True)

    # Comando legado para compatibilidad (mantener /set captcha por si acaso)
    @app_commands.command(name="captcha", description="[Obsoleto] Usa /set verification en su lugar")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        emoji="Emoji que el usuario debe reaccionar para verificarse",
        role="Rol que se asigna al pasar el captcha",
    )
    async def set_captcha(self, interaction: discord.Interaction, emoji: str, role: discord.Role):
        if interaction.user.id != CAPTCHA_OWNER_ID:
            return await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Verificacion",
            description=(
                f"Para acceder al servidor debes verificarte.\n\n"
                f"Reacciona con {emoji} para iniciar la verificacion.\n"
                f"Recibirás un captcha por DM. Si tienes los DMs cerrados, "
                f"te aparecerá el captcha aquí mismo (solo tú lo verás)."
            ),
            color=0x2B2D31,
        )
        embed.set_footer(text="Verificacion automatica — Los espacios se ignoran al escribir el codigo")

        try:
            panel_msg = await interaction.channel.send(embed=embed)
            await panel_msg.add_reaction(emoji)
        except discord.HTTPException:
            return await interaction.followup.send("❌ Emoji invalido o sin permisos para reaccionar.", ephemeral=True)

        cursor.execute(
            "REPLACE INTO reaction_roles(message_id, emoji, role_id, requires_captcha) VALUES(?,?,?,?)",
            (panel_msg.id, emoji, role.id, 1),
        )
        conn.commit()

        await interaction.followup.send(
            f"✅ Panel enviado.\nEmoji: {emoji} → Rol: **{role.name}** → Captcha: activado\n"
            f"*Considera usar `/set verification` para más opciones (canal destino, unrole, mención).*",
            ephemeral=True,
        )


class TranslateGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="translate", description="Herramientas de traducción")

    @app_commands.command(name="message", description=app_commands.locale_str("translate_msg"))
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message_id="ID del mensaje a traducir")
    async def translate_msg(self, interaction: discord.Interaction, message_id: str):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        try:
            msg = await interaction.channel.fetch_message(int(message_id))
        except Exception:
            return await interaction.response.send_message("❌ Mensaje no encontrado.", ephemeral=True)
        await interaction.response.send_message("🌐 Elige un idioma:", view=TranslateView(msg.content))


class WarnGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="warn", description="Gestión de advertencias de miembros")

    @app_commands.command(name="check", description="Ver advertencias de un usuario")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(user="Usuario a consultar")
    async def warn_check(self, interaction: discord.Interaction, user: discord.Member):
        count = get_warnings(user.id)
        bar   = "🟥" * count + "⬛" * (MAX_WARNINGS - count)
        e = discord.Embed(title="📋 Advertencias", color=discord.Color.orange())
        e.add_field(name="Usuario",      value=user.mention,              inline=False)
        e.add_field(name="Advertencias", value=f"{bar} `{count}/{MAX_WARNINGS}`", inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="reset", description=app_commands.locale_str("warn_reset"))
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario al que resetear advertencias")
    async def warn_reset(self, interaction: discord.Interaction, user: discord.Member):
        if interaction.user.id not in OWNER_IDS and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
        reset_warnings(user.id)
        await interaction.response.send_message(f"✅ Advertencias de {user.mention} reseteadas a `0/{MAX_WARNINGS}`.", ephemeral=True)

# ─────────────────────────────────────────────
#  COMANDOS RAÍZ
# ─────────────────────────────────────────────

DISCORD_TIMEOUT_MAX = datetime.timedelta(days=28)

@bot.tree.command(name="ban", description=app_commands.locale_str("ban"))
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(user="Usuario a banear", reason="Motivo", duration="Duración ej: 30s, 5m, 2h, 7d. Vacío = permanente.")
async def slash_ban(interaction: discord.Interaction, user: discord.Member,
                    reason: str = "No especificado", duration: str = None):
    if duration:
        td = parse_timespan(duration)
        if not td:
            return await interaction.response.send_message("❌ Formato inválido. Usa ej: `30s`, `10m`, `2h`, `7d`.", ephemeral=True)
        desc = f"{user.mention} baneado por **{duration}**"
    else:
        desc = f"{user.mention} baneado permanentemente"
    try:
        await user.ban(reason=reason)
    except discord.Forbidden:
        return await interaction.response.send_message("❌ Sin permisos para banear a este usuario.", ephemeral=True)
    e = discord.Embed(
        description=f"### 🔨 {desc}\n**Motivo:** {reason}\n**Staff:** {interaction.user.mention}",
        color=discord.Color.red(),
    )
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="clear", description=app_commands.locale_str("clear"))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(amount="Mensajes a borrar (máx 1000)", only_user="Solo de este usuario", only_bots="Solo bots")
async def slash_clear(interaction: discord.Interaction, amount: int,
                      only_user: discord.Member = None, only_bots: bool = False):
    if amount <= 0 or amount > 1000:
        return await interaction.response.send_message("❌ La cantidad debe estar entre 1 y 1000.", ephemeral=True)
    await interaction.response.send_message("⏳ Procesando…", ephemeral=True)

    def check(m):
        if only_user and m.author.id != only_user.id:
            return False
        if only_bots and not m.author.bot:
            return False
        return True

    try:
        await interaction.channel.purge(limit=amount, check=check)
    except discord.Forbidden:
        return await interaction.edit_original_response(content="❌ Sin permisos para eliminar mensajes.")
    except discord.HTTPException:
        return await interaction.edit_original_response(content="❌ Algo salió mal.")

    await interaction.edit_original_response(content=f"✅ Eliminados hasta **{amount}** mensajes.")
    await asyncio.sleep(3)
    try:
        await interaction.delete_original_response()
    except discord.HTTPException:
        pass


@bot.tree.command(name="kick", description=app_commands.locale_str("kick"))
@app_commands.default_permissions(kick_members=True)
@app_commands.describe(user="Usuario a expulsar", reason="Motivo")
async def slash_kick(interaction: discord.Interaction, user: discord.Member, reason: str = "No especificado"):
    try:
        await user.kick(reason=reason)
    except discord.Forbidden:
        return await interaction.response.send_message("❌ Sin permisos para expulsar a este usuario.", ephemeral=True)
    e = discord.Embed(
        description=f"### 👢 {user.mention} expulsado\n**Motivo:** {reason}\n**Staff:** {interaction.user.mention}",
        color=discord.Color.red(),
    )
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="mute", description=app_commands.locale_str("mute"))
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(user="Usuario a silenciar", duration="Duración ej: 30s, 5m, 2h, 7d, 28d", reason="Motivo")
async def slash_mute(interaction: discord.Interaction, user: discord.Member,
                     duration: str, reason: str = "No especificado"):
    td = parse_timespan(duration)
    if not td:
        return await interaction.response.send_message("❌ Formato inválido. Usa ej: `30s`, `10m`, `2h`, `7d`, `28d`.", ephemeral=True)
    if td > DISCORD_TIMEOUT_MAX:
        return await interaction.response.send_message("❌ El máximo de Discord es **28 días**.", ephemeral=True)
    try:
        await user.timeout(td, reason=reason)
    except discord.Forbidden:
        return await interaction.response.send_message("❌ Sin permisos para silenciar a este usuario.", ephemeral=True)
    e = discord.Embed(
        description=f"### 🔇 {user.mention} silenciado por **{duration}**\n**Motivo:** {reason}\n**Staff:** {interaction.user.mention}",
        color=discord.Color.orange(),
    )
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="upload", description=app_commands.locale_str("upload"))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(game="Link del juego", channel="Canal destino", key="Contraseña/key", uploader="Usuario", ping="¿Mencionar rol especial?")
async def slash_upload(interaction: discord.Interaction, game: str, channel: discord.TextChannel,
                       key: str = None, uploader: str = None, ping: bool = False):
    if interaction.user.id not in OWNER_IDS:
        return await interaction.response.send_message("❌ Acceso denegado.", ephemeral=True)
    e = discord.Embed(title="📥 Upload", color=discord.Color.blue(), timestamp=datetime.datetime.utcnow())
    e.add_field(name="🎮 Game",  value=f"[Link]({game})",   inline=True)
    e.add_field(name="🔑 Key",   value=key or "N/A",        inline=True)
    e.add_field(name="👤 By",    value=uploader or "N/A",   inline=True)
    try:
        await channel.send(content="<@&1503716913937911838>" if ping else None, embed=e)
        await interaction.response.send_message(f"✅ Enviado a {channel.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Sin permisos en ese canal.", ephemeral=True)


# ─────────────────────────────────────────────
#  COMANDOS PREFIX
# ─────────────────────────────────────────────

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def prefix_ban(ctx, user: discord.Member, *, reason: str = "No especificado"):
    await user.ban(reason=reason)
    e = discord.Embed(
        description=f"### 🔨 {user.mention} baneado permanentemente\n**Motivo:** {reason}\n**Staff:** {ctx.author.mention}",
        color=discord.Color.red(),
    )
    await ctx.send(embed=e)

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def prefix_kick(ctx, user: discord.Member, *, reason: str = "No especificado"):
    await user.kick(reason=reason)
    e = discord.Embed(
        description=f"### 👢 {user.mention} expulsado\n**Motivo:** {reason}\n**Staff:** {ctx.author.mention}",
        color=discord.Color.red(),
    )
    await ctx.send(embed=e)

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def prefix_mute(ctx, user: discord.Member, duration: str, *, reason: str = "No especificado"):
    td = parse_timespan(duration)
    if not td:
        return await ctx.send("❌ Formato inválido. Usa ej: `30s`, `5m`, `2h`, `7d`.")
    if td > DISCORD_TIMEOUT_MAX:
        return await ctx.send("❌ El máximo de Discord es 28 días.")
    await user.timeout(td, reason=reason)
    e = discord.Embed(
        description=f"### 🔇 {user.mention} silenciado por **{duration}**\n**Motivo:** {reason}\n**Staff:** {ctx.author.mention}",
        color=discord.Color.orange(),
    )
    await ctx.send(embed=e)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Espera **{error.retry_after:.1f}s** antes de usar esto de nuevo.", delete_after=6)
    elif isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
        pass
    else:
        print(f"[Command error] {ctx.command}: {error}")

# ─────────────────────────────────────────────
#  PANEL DE VERIFICACIÓN — botón persistente
# ─────────────────────────────────────────────

class VerificationPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅  Verify",
        style=discord.ButtonStyle.success,
        custom_id="verify_panel_btn",
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        guild  = interaction.guild
        if not guild or not isinstance(member, discord.Member):
            return await interaction.response.send_message(
                "Could not resolve your server membership. Try again.", ephemeral=True
            )

        lang = get_user_lang(member.id)
        if lang == "AUTO":
            lang = "ES"

        # Obtener role_id y unrole_id del panel
        role_id, unrole_id = get_verification_panel(interaction.message.id)

        # Fallback: buscar en reaction_roles si no hay entrada en verification_panels
        if role_id is None:
            cursor.execute(
                "SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji='__button__'",
                (interaction.message.id,),
            )
            row = cursor.fetchone()
            role_id = row[0] if row else None

        # ── Ya verificado: no permitir re-verificación ──
        if is_verified(member.id):
            _already = {
                "EN": "You are already verified. You cannot verify again.",
                "ES": "Ya estas verificado/a. No puedes verificarte de nuevo.",
                "PT": "Voce ja esta verificado/a. Nao pode se verificar novamente.",
            }
            return await interaction.response.send_message(
                _already.get(lang, _already["ES"]), ephemeral=True
            )

        # ── Si ya tiene el rol: no verificar de nuevo ──
        if role_id:
            role = guild.get_role(role_id)
            if role and role in member.roles:
                _already = {
                    "EN": "You already have the verified role.",
                    "ES": "Ya tienes el rol de verificado.",
                    "PT": "Voce ja possui o cargo de verificado.",
                }
                return await interaction.response.send_message(
                    _already.get(lang, _already["ES"]), ephemeral=True
                )

        # ── Cooldown (solo no-owner) ──
        if member.id not in OWNER_IDS:
            cooldown_until = captcha_cooldowns.get(member.id)
            if cooldown_until and time.time() < cooldown_until:
                remaining = int(cooldown_until - time.time())
                mins, secs = divmod(remaining, 60)
                _cd = {
                    "EN": f"You failed the captcha. Please wait **{mins}m {secs}s** before trying again.",
                    "ES": f"Fallaste el captcha. Espera **{mins}m {secs}s** antes de intentarlo de nuevo.",
                    "PT": f"Voce errou o captcha. Aguarde **{mins}m {secs}s** antes de tentar novamente.",
                }
                return await interaction.response.send_message(_cd.get(lang, _cd["ES"]), ephemeral=True)
            captcha_cooldowns.pop(member.id, None)

        # ── Captcha pendiente ──
        if member.id in pending_captchas:
            _pend = {
                "EN": "You already have a captcha in progress. Check your DMs or use the button in the previous captcha message.",
                "ES": "Ya tienes un captcha en curso. Revisa tus DMs o usa el boton del mensaje anterior.",
                "PT": "Voce ja tem um captcha em andamento. Verifique seus DMs ou use o botao da mensagem anterior.",
            }
            return await interaction.response.send_message(_pend.get(lang, _pend["ES"]), ephemeral=True)

        # ── Confirmar y enviar captcha ──
        _sending = {
            "EN": "Sending your captcha via DM. If your DMs are closed, it will appear here (only you will see it).",
            "ES": "Enviando tu captcha por DM. Si tienes los DMs cerrados, aparecerá aquí (solo tú lo verás).",
            "PT": "Enviando seu captcha por DM. Se seus DMs estiverem fechados, aparecerá aqui (só você verá).",
        }
        await interaction.response.send_message(_sending.get(lang, _sending["ES"]), ephemeral=True)
        asyncio.create_task(
            start_captcha(member, guild, role_id=role_id, unrole_id=unrole_id, interaction=interaction)
        )


class PanelGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="panel", description="Paneles interactivos del servidor")

    @app_commands.command(
        name="verification",
        description="[Obsoleto] Usa /set verification en su lugar",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Canal donde se enviará el panel",
        role="Rol que se asigna al pasar el captcha",
        mention_role="(Opcional) Rol a mencionar en el mensaje del panel",
    )
    async def panel_verification(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
        mention_role: discord.Role | None = None,
    ):
        if interaction.user.id != CAPTCHA_OWNER_ID:
            return await interaction.response.send_message(
                "❌ No tienes permiso para usar este comando.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        perms = channel.permissions_for(interaction.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return await interaction.followup.send(
                f"❌ No tengo permisos para enviar mensajes o embeds en {channel.mention}.", ephemeral=True
            )

        embed = discord.Embed(
            title="Server Verification",
            description=(
                "To gain access to the server you must complete a quick verification.\n\n"
                "**Click the button below** to receive a captcha image.\n"
                "Type the text shown in the image to get verified. **Spaces are ignored.**\n\n"
                f"Upon completing verification you will receive the **{role.name}** role."
            ),
            color=0x57F287,
        )
        embed.set_footer(text="If you fail the captcha you must wait 2 minutes before trying again.")

        mention_content = mention_role.mention if mention_role else ""

        try:
            panel_msg = await channel.send(
                content=mention_content or None,
                embed=embed,
                view=VerificationPanelView(),
            )
        except discord.HTTPException as exc:
            return await interaction.followup.send(f"❌ Error al enviar el panel: {exc}", ephemeral=True)

        cursor.execute(
            "REPLACE INTO reaction_roles(message_id, emoji, role_id, requires_captcha) VALUES(?,?,?,?)",
            (panel_msg.id, "__button__", role.id, 1),
        )
        cursor.execute(
            "REPLACE INTO verification_panels(message_id, role_id, unrole_id) VALUES(?,?,?)",
            (panel_msg.id, role.id, None),
        )
        conn.commit()

        await interaction.followup.send(
            f"✅ Panel enviado en {channel.mention}.\n"
            f"Rol que se asignará: **{role.name}**\n"
            f"ID del mensaje: `{panel_msg.id}`\n"
            f"*Considera usar `/set verification` para configurar también un `unrole`.*",
            ephemeral=True,
        )


# ─────────────────────────────────────────────
#  ON READY
# ─────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user} (ID {bot.user.id})")
    print(f"🤖 Backend de IA: {_AI_BACKEND}")

    for group in [LanguageGroup(), LevelGroup(), PanelGroup(), RoleGroup(), SendGroup(),
                  SetGroup(), TicketGroup(), TranslateGroup(), WarnGroup()]:
        try:
            bot.tree.add_command(group)
        except app_commands.CommandAlreadyRegistered:
            pass

    bot.add_view(TicketView())
    bot.add_view(TicketControlView())
    bot.add_view(DeleteChannelView())
    bot.add_view(ContactStaffView())
    bot.add_view(VerificationPanelView())

    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados.")
    except Exception as e:
        print(f"[Sync error] {e}")

# ─────────────────────────────────────────────
#  INICIO
# ─────────────────────────────────────────────

bot.run(TOKEN)
