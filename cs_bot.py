"""
EGOIST CS2 Telegram Bot - with Availability Mini App
@stratbook_bot
"""

import os
import json
import random
import asyncio
import logging
import hmac
import hashlib
from urllib.parse import parse_qsl
from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery, WebAppInfo
)
from aiohttp import web
from aiohttp.web import Request, Response, json_response
import aiohttp_cors
from google.oauth2 import service_account
from googleapiclient.discovery import build
import asyncpg


# ============================================================================
# 🔧 CONFIGURATION
# ============================================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://egoist-avail.vercel.app")
API_PORT = int(os.getenv("PORT", 8080))

CALENDAR_ID = "85f813a348453bc70b98c82024ac2d7db492896a82798537ce2a4e7175a0feb3@group.calendar.google.com"

GROUP_ID = -1003680698112
STRATBOOK_TOPIC_ID = 1542
SCRIMS_TOPIC_ID = 15
CHAT_TOPIC_ID = 13
ADMIN_ID = 557066322
PINNED_MESSAGE_ID = 1707

# Default team (admin only — добавь остальных через /addplayer)
DEFAULT_TEAM = {
    557066322: {"username": "FREEDOM5O", "display": "FREEDOM"},
}

TIME_SLOTS = [
    {"id": "morning", "name": "Утро", "emoji": "🌅", "hours": "10-14"},
    {"id": "day", "name": "День", "emoji": "🌇", "hours": "14-19"},
    {"id": "evening", "name": "Вечер", "emoji": "🌃", "hours": "19-23"},
]

CALENDAR_CHECK_INTERVAL = 600
QUOTE_CHECK_INTERVAL = 300
AVAIL_CHECK_INTERVAL = 60
AUTO_DELETE_DEFAULT = 60
AUTO_DELETE_HOUR = 3600
AUTO_DELETE_DAY = 82800
MENU_RESET_DELAY = 15
QUOTE_TIME_HOUR = 10
QUOTE_TIME_MINUTE_MAX = 5
AVAILABILITY_DAYS_AHEAD = 14
TEAM_SIZE = 5

MOSCOW_TZ = timezone(timedelta(hours=3))
UTC = timezone.utc

PLAYERS_TAG = "@Rogachev_E @gladnessorrow @YakobsMonarch0_0 @FREEDOM5O"
INSTA_LINK = "https://docs.google.com/spreadsheets/d/1C4ZIfJKl4WvnCkH3eVB7v0lw7N94pyYZwj98VPhOcTk/edit?gid=1511020141#gid=1511020141"
MAIN_MENU_TEXT = "📚 <b>EGOIST STRATBOOK</b>\n\nВыбери раздел и получи нужную информацию:"

STRAT_BOOKS = {
    "mirage": "https://docs.google.com/document/d/1KfaADUAV4jy2QqHyjUlAJ5rBd9SQuFokAmQN86DDHEE/edit?tab=t.5w09v52hr780",
    "dust2": "https://docs.google.com/document/d/1o_B5xguuRmTO1lw2b9NB7sphzWZFvlEiQaU2VKlbzDU/edit?tab=t.5w09v52hr780",
    "ancient": None,
}

NADES = {
    "mirage": "https://youtu.be/WCX87Hl5auE",
    "dust2": "https://youtu.be/T6WxmGJYC9w",
    "ancient": "https://www.youtube.com/watch?v=ETTmq_xxPLk",
}

MAP_KEYWORDS = {
    "mirage": "mirage", "мираж": "mirage",
    "dust2": "dust2", "dust 2": "dust2", "de dust 2": "dust2",
    "даст": "dust2", "даст2": "dust2", "даст 2": "dust2",
    "ancient": "ancient",
}

QUOTES = [
    ("Я не проиграю никогда. Я либо побеждаю, либо учусь.", "s1mple"),
    ("Тренировка делает чемпиона.", "ZywOo"),
    ("Лучше один правильный аим, чем сто промахов.", "NiKo"),
    ("В CS нет случайностей, есть только подготовка.", "device"),
    ("Командная игра больше индивидуальных скилов.", "GeT_RiGhT"),
    ("Калм важнее реакции. Голова решает всё.", "olofmeister"),
    ("Каждый матч — это возможность стать лучше.", "f0rest"),
    ("Не бойся проигрывать — бойся не учиться.", "shox"),
    ("Снайпер делает разницу между топ-1 и топ-10.", "kennyS"),
    ("Скилл — это привычка, повторённая тысячу раз.", "coldzera"),
    ("Дисциплина побеждает талант.", "FalleN"),
    ("Лучший игрок — тот, кто помогает команде.", "Xyp9x"),
    ("Уверенность приходит с подготовкой.", "dupreeh"),
    ("Не играй ради статы — играй ради победы.", "karrigan"),
    ("Слушай айгиэля и доверяй сокомандникам.", "gla1ve"),
    ("Аим без головы — это просто клики.", "ScreaM"),
    ("Каждая граната — это инвестиция в раунд.", "Magisk"),
    ("Лучшая защита — это правильный setup.", "Snax"),
    ("Не повторяй одни и те же ошибки. Учись быстро.", "pashaBiceps"),
    ("Микро-движения решают перестрелки.", "GuardiaN"),
    ("CS — это шахматы со стволами.", "TaZ"),
    ("Тимплей важнее, чем индивидуальные действия.", "Snappi"),
    ("Учись у поражений больше, чем у побед.", "Twistzz"),
    ("Лучше тихо победить, чем громко проиграть.", "EliGE"),
    ("Каждый раунд — это новая возможность.", "NAF"),
    ("Стратегия без исполнения — это ничего.", "stanislaw"),
    ("Терпение — главное оружие снайпера.", "JW"),
    ("Не играй против врагов — играй против карты.", "Aleksib"),
    ("Самое важное — это коммуникация в команде.", "allu"),
    ("В сложной ситуации делай простое.", "blameF"),
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("egoist_bot")
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
db_pool: Optional[asyncpg.Pool] = None


# ============================================================================
# 💾 DATABASE
# ============================================================================

async def db_init() -> None:
    global db_pool
    log.info("📊 Connecting to PostgreSQL...")
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10, command_timeout=30)
    log.info("✓ Connected to database")
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                notified_new BOOLEAN DEFAULT FALSE,
                notified_day BOOLEAN DEFAULT FALSE,
                notified_hour BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS action_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                username TEXT,
                action TEXT
            );
            CREATE TABLE IF NOT EXISTS used_quotes (
                quote_index INTEGER PRIMARY KEY,
                used_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS team_players (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                added_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS availability (
                user_id BIGINT,
                slot_date DATE,
                slot_time TEXT,
                status TEXT DEFAULT 'can',
                updated_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, slot_date, slot_time)
            );
            CREATE TABLE IF NOT EXISTS avail_notifications (
                slot_date DATE,
                slot_time TEXT,
                count INTEGER,
                notified_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (slot_date, slot_time, count)
            );
            CREATE INDEX IF NOT EXISTS idx_availability_date 
                ON availability (slot_date, slot_time, status);
        """)
        
        for user_id, info in DEFAULT_TEAM.items():
            await conn.execute("""
                INSERT INTO team_players (user_id, username, display_name)
                VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING
            """, user_id, info["username"], info["display"])
    
    log.info("✓ Tables ready")


async def db_get_state(key: str) -> Optional[str]:
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM bot_state WHERE key = $1", key)
            return row['value'] if row else None
    except Exception as e:
        log.error(f"db_get_state: {e}")
        return None


async def db_set_state(key: str, value: str) -> None:
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bot_state (key, value, updated_at) VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, key, value)
    except Exception as e:
        log.error(f"db_set_state: {e}")


async def db_get_event(event_id: str) -> Optional[Dict[str, Any]]:
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM processed_events WHERE event_id = $1", event_id)
            return dict(row) if row else None
    except Exception as e:
        log.error(f"db_get_event: {e}")
        return None


async def db_mark_event(event_id, notified_new=False, notified_day=False, notified_hour=False) -> bool:
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processed_events (event_id, notified_new, notified_day, notified_hour)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (event_id) DO UPDATE SET
                    notified_new = processed_events.notified_new OR EXCLUDED.notified_new,
                    notified_day = processed_events.notified_day OR EXCLUDED.notified_day,
                    notified_hour = processed_events.notified_hour OR EXCLUDED.notified_hour
            """, event_id, notified_new, notified_day, notified_hour)
            return True
    except Exception as e:
        log.error(f"db_mark_event: {e}")
        return False


async def db_log_action(user: types.User, action: str) -> None:
    try:
        async with db_pool.acquire() as conn:
            username = user.username or user.full_name or str(user.id)
            display = f"@{username}" if user.username else username
            await conn.execute(
                "INSERT INTO action_logs (username, action) VALUES ($1, $2)", display, action
            )
    except Exception as e:
        log.error(f"db_log_action: {e}")


async def db_get_logs(limit: int = 20) -> List[Dict[str, Any]]:
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM action_logs ORDER BY timestamp DESC LIMIT $1", limit
            )
            return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"db_get_logs: {e}")
        return []


async def db_get_next_quote() -> Tuple[str, str]:
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                used_rows = await conn.fetch("SELECT quote_index FROM used_quotes")
                used = {row['quote_index'] for row in used_rows}
                available = [i for i in range(len(QUOTES)) if i not in used]
                if not available:
                    await conn.execute("DELETE FROM used_quotes")
                    available = list(range(len(QUOTES)))
                idx = random.choice(available)
                await conn.execute(
                    "INSERT INTO used_quotes (quote_index) VALUES ($1) ON CONFLICT DO NOTHING", idx
                )
                return QUOTES[idx]
    except Exception as e:
        log.error(f"db_get_next_quote: {e}")
        return QUOTES[0]


# ============== AVAILABILITY ==============

async def db_get_team() -> List[Dict[str, Any]]:
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id, username, display_name FROM team_players ORDER BY added_at"
            )
            return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"db_get_team: {e}")
        return []


async def db_add_player(user_id: int, username: str, display_name: str) -> bool:
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO team_players (user_id, username, display_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE 
                SET username = EXCLUDED.username, display_name = EXCLUDED.display_name
            """, user_id, username, display_name)
            return True
    except Exception as e:
        log.error(f"db_add_player: {e}")
        return False


async def db_set_availability(user_id: int, slot_date: str, slot_time: str, status: str) -> bool:
    try:
        async with db_pool.acquire() as conn:
            if status == "clear":
                await conn.execute("""
                    DELETE FROM availability WHERE user_id = $1 AND slot_date = $2 AND slot_time = $3
                """, user_id, date.fromisoformat(slot_date), slot_time)
            else:
                await conn.execute("""
                    INSERT INTO availability (user_id, slot_date, slot_time, status, updated_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (user_id, slot_date, slot_time) 
                    DO UPDATE SET status = EXCLUDED.status, updated_at = NOW()
                """, user_id, date.fromisoformat(slot_date), slot_time, status)
            return True
    except Exception as e:
        log.error(f"db_set_availability: {e}")
        return False


async def db_get_availability_grid(days_ahead: int = 14) -> List[Dict[str, Any]]:
    try:
        async with db_pool.acquire() as conn:
            today = date.today()
            end_date = today + timedelta(days=days_ahead)
            rows = await conn.fetch("""
                SELECT a.slot_date, a.slot_time, a.status, a.user_id,
                       tp.username, tp.display_name
                FROM availability a
                LEFT JOIN team_players tp ON tp.user_id = a.user_id
                WHERE a.slot_date >= $1 AND a.slot_date <= $2
                ORDER BY a.slot_date, a.slot_time
            """, today, end_date)
            return [
                {
                    "slot_date": r["slot_date"].isoformat(),
                    "slot_time": r["slot_time"],
                    "status": r["status"],
                    "user_id": r["user_id"],
                    "username": r["username"],
                    "display_name": r["display_name"]
                }
                for r in rows
            ]
    except Exception as e:
        log.error(f"db_get_availability_grid: {e}")
        return []


async def db_was_notified(slot_date: str, slot_time: str, count: int) -> bool:
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 1 FROM avail_notifications
                WHERE slot_date = $1 AND slot_time = $2 AND count = $3
            """, date.fromisoformat(slot_date), slot_time, count)
            return row is not None
    except Exception as e:
        log.error(f"db_was_notified: {e}")
        return True


async def db_mark_notified(slot_date: str, slot_time: str, count: int) -> None:
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO avail_notifications (slot_date, slot_time, count)
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """, date.fromisoformat(slot_date), slot_time, count)
    except Exception as e:
        log.error(f"db_mark_notified: {e}")


# ============================================================================
# 🔐 TELEGRAM WEB APP AUTH
# ============================================================================

def verify_telegram_init_data(init_data: str) -> Optional[Dict]:
    try:
        parsed = dict(parse_qsl(init_data))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash != received_hash:
            return None
        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return None
    except Exception as e:
        log.error(f"verify_telegram_init_data: {e}")
        return None


async def get_user_from_request(request: Request) -> Optional[Dict]:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        return None
    return verify_telegram_init_data(init_data)


# ============================================================================
# 🌐 API ENDPOINTS
# ============================================================================

async def api_health(request: Request) -> Response:
    return json_response({"status": "ok", "bot": "egoist"})


async def api_me(request: Request) -> Response:
    user = await get_user_from_request(request)
    if not user:
        return json_response({"error": "Unauthorized"}, status=401)
    team = await db_get_team()
    return json_response({
        "id": user["id"],
        "username": user.get("username", ""),
        "first_name": user.get("first_name", ""),
        "is_team_member": any(p["user_id"] == user["id"] for p in team)
    })


async def api_team(request: Request) -> Response:
    team = await db_get_team()
    return json_response({"team": team, "size": TEAM_SIZE})


async def api_availability_grid(request: Request) -> Response:
    user = await get_user_from_request(request)
    if not user:
        return json_response({"error": "Unauthorized"}, status=401)
    
    grid = await db_get_availability_grid(AVAILABILITY_DAYS_AHEAD)
    aggregated = {}
    for entry in grid:
        key = f"{entry['slot_date']}_{entry['slot_time']}"
        if key not in aggregated:
            aggregated[key] = {
                "slot_date": entry["slot_date"],
                "slot_time": entry["slot_time"],
                "can": [], "cant": []
            }
        player = {
            "user_id": entry["user_id"],
            "username": entry["username"],
            "display_name": entry["display_name"]
        }
        if entry["status"] == "can":
            aggregated[key]["can"].append(player)
        else:
            aggregated[key]["cant"].append(player)
    
    return json_response({
        "slots": list(aggregated.values()),
        "team_size": TEAM_SIZE,
        "days_ahead": AVAILABILITY_DAYS_AHEAD,
        "your_id": user["id"],
        "time_slots": TIME_SLOTS
    })


async def api_set_availability(request: Request) -> Response:
    user = await get_user_from_request(request)
    if not user:
        return json_response({"error": "Unauthorized"}, status=401)
    
    team = await db_get_team()
    if not any(p["user_id"] == user["id"] for p in team):
        return json_response({"error": "Not a team member"}, status=403)
    
    try:
        body = await request.json()
        slot_date = body["slot_date"]
        slot_time = body["slot_time"]
        status = body["status"]
        if status not in ("can", "cant", "clear"):
            return json_response({"error": "Invalid status"}, status=400)
        success = await db_set_availability(user["id"], slot_date, slot_time, status)
        if not success:
            return json_response({"error": "DB error"}, status=500)
        return json_response({"ok": True})
    except Exception as e:
        return json_response({"error": str(e)}, status=400)


async def setup_api(app: web.Application) -> None:
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, expose_headers="*",
            allow_headers="*", allow_methods="*"
        )
    })
    
    routes = [
        ("/", "GET", api_health),
        ("/api/health", "GET", api_health),
        ("/api/me", "GET", api_me),
        ("/api/team", "GET", api_team),
        ("/api/availability", "GET", api_availability_grid),
        ("/api/availability", "POST", api_set_availability),
    ]
    
    for path, method, handler in routes:
        resource = cors.add(app.router.add_resource(path))
        cors.add(resource.add_route(method, handler))


async def start_api_server() -> None:
    app = web.Application()
    await setup_api(app)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    log.info(f"🌐 API server started on port {API_PORT}")


# ============================================================================
# 👁 AVAILABILITY WATCHER
# ============================================================================

async def availability_watcher() -> None:
    log.info("👁  Availability watcher started")
    while True:
        try:
            if not db_pool:
                await asyncio.sleep(AVAIL_CHECK_INTERVAL)
                continue
            
            grid = await db_get_availability_grid(AVAILABILITY_DAYS_AHEAD)
            slots = {}
            for entry in grid:
                key = f"{entry['slot_date']}_{entry['slot_time']}"
                if key not in slots:
                    slots[key] = {"date": entry["slot_date"], "time": entry["slot_time"], "can": []}
                if entry["status"] == "can" and entry["username"]:
                    slots[key]["can"].append(entry["username"])
            
            for slot in slots.values():
                if len(slot["can"]) == TEAM_SIZE:
                    if not await db_was_notified(slot["date"], slot["time"], TEAM_SIZE):
                        await notify_full_house(slot["date"], slot["time"], slot["can"])
                        await db_mark_notified(slot["date"], slot["time"], TEAM_SIZE)
        except Exception as e:
            log.error(f"availability_watcher: {e}")
        await asyncio.sleep(AVAIL_CHECK_INTERVAL)


async def notify_full_house(slot_date: str, slot_time: str, usernames: List[str]) -> None:
    try:
        slot_info = next((s for s in TIME_SLOTS if s["id"] == slot_time), None)
        if not slot_info:
            return
        date_obj = date.fromisoformat(slot_date)
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday = weekdays[date_obj.weekday()]
        date_str = date_obj.strftime("%d.%m.%Y")
        tags = " ".join(f"@{u}" for u in usernames if u)
        
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=WEBAPP_URL)))
        
        await bot.send_message(
            GROUP_ID,
            f"🔥 <b>ВСЕ В СБОРЕ!</b>\n\n"
            f"📅 {weekday}, {date_str}\n"
            f"{slot_info['emoji']} {slot_info['name']} ({slot_info['hours']} МСК)\n\n"
            f"{tags}\n\n"
            f"🎯 Можем играть прак!\n"
            f"• Создавайте событие в Google Calendar\n"
            f"• Ищите противника на Pracc.com",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID,
            reply_markup=kb
        )
        log.info(f"🔥 Full house notification: {slot_date} {slot_time}")
    except Exception as e:
        log.error(f"notify_full_house: {e}")


# ============================================================================
# 📅 GOOGLE CALENDAR
# ============================================================================

def calendar_service():
    try:
        creds_info = json.loads(GOOGLE_CREDS_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        log.error(f"calendar_service: {e}")
        return None


async def calendar_fetch_events() -> List[Dict]:
    service = calendar_service()
    if not service:
        return []
    now = datetime.now(UTC).isoformat()
    later = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    try:
        result = service.events().list(
            calendarId=CALENDAR_ID, timeMin=now, timeMax=later,
            singleEvents=True, orderBy='startTime'
        ).execute()
        return result.get('items', [])
    except Exception as e:
        log.error(f"calendar_fetch_events: {e}")
        return []


async def calendar_loop() -> None:
    log.info("📅 Calendar loop started")
    first_run_marker = await db_get_state("calendar_initialized")
    is_first_run = (first_run_marker is None)
    
    while True:
        try:
            if not db_pool:
                await asyncio.sleep(CALENDAR_CHECK_INTERVAL)
                continue
            events = await calendar_fetch_events()
            now = datetime.now(UTC)
            for event in events:
                await _process_event(event, now, is_first_run)
            if is_first_run:
                await db_set_state("calendar_initialized", datetime.now(UTC).isoformat())
                is_first_run = False
                log.info("✓ Calendar initialized")
        except Exception as e:
            log.error(f"calendar_loop: {e}")
        await asyncio.sleep(CALENDAR_CHECK_INTERVAL)


async def _process_event(event, now, is_first_run):
    event_id = event['id']
    summary = event.get('summary', 'Прак')
    start = event['start'].get('dateTime') or event['start'].get('date')
    if not start or 'T' not in start:
        return
    event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
    local_time = event_time.astimezone(MOSCOW_TZ)
    date_str = local_time.strftime("%d.%m.%Y")
    time_str = local_time.strftime("%H:%M")
    time_until = event_time - now
    
    state = await db_get_event(event_id)
    if state is None:
        if is_first_run:
            await db_mark_event(event_id, True, True, True)
            return
        else:
            await _send_new_scrim(event_id, summary, date_str, time_str, time_until)
            state = await db_get_event(event_id)
            if not state:
                return
    
    if not state["notified_day"] and timedelta(hours=23, minutes=50) < time_until <= timedelta(hours=24, minutes=10):
        await _send_day_reminder(event_id, summary, date_str, time_str)
    if not state["notified_hour"] and timedelta(minutes=50) < time_until <= timedelta(hours=1, minutes=10):
        await _send_hour_reminder(event_id, summary, time_str)


async def _send_new_scrim(event_id, summary, date_str, time_str, time_until):
    is_soon = time_until < timedelta(hours=1)
    is_today = time_until < timedelta(hours=24)
    if not await db_mark_event(event_id, True, is_today, is_soon):
        return
    try:
        await bot.send_message(
            GROUP_ID,
            f"🎮 <b>НОВЫЙ ПРАК ИЗ КАЛЕНДАРЯ!</b>\n"
            f"📅 <i>(синхронизируется с Google Calendar и Pracc.com)</i>\n\n"
            f"🗺 {summary}\n📅 {date_str} в {time_str}\n\n{PLAYERS_TAG}",
            parse_mode="HTML", message_thread_id=SCRIMS_TOPIC_ID
        )
    except Exception as e:
        log.error(f"send new scrim: {e}")


async def _send_day_reminder(event_id, summary, date_str, time_str):
    if not await db_mark_event(event_id, notified_day=True):
        return
    try:
        sent = await bot.send_message(
            GROUP_ID,
            f"🔔 <b>Напоминание! Прак завтра!</b>\n"
            f"📅 <i>(из Google Calendar и Pracc.com)</i>\n\n"
            f"🗺 {summary}\n📅 {date_str} в {time_str}\n\n{PLAYERS_TAG}",
            parse_mode="HTML", message_thread_id=SCRIMS_TOPIC_ID
        )
        asyncio.create_task(auto_delete(sent, AUTO_DELETE_DAY))
    except Exception as e:
        log.error(f"send day reminder: {e}")


async def _send_hour_reminder(event_id, summary, time_str):
    if not await db_mark_event(event_id, notified_hour=True):
        return
    try:
        sent = await bot.send_message(
            GROUP_ID,
            f"⏰ <b>Через час прак!</b>\n"
            f"📅 <i>(из Google Calendar и Pracc.com)</i>\n\n"
            f"🗺 {summary}\n🕐 {time_str}\n\n{PLAYERS_TAG}",
            parse_mode="HTML", message_thread_id=SCRIMS_TOPIC_ID
        )
        asyncio.create_task(auto_delete(sent, AUTO_DELETE_HOUR))
    except Exception as e:
        log.error(f"send hour reminder: {e}")


# ============================================================================
# ☀️ QUOTES
# ============================================================================

async def quote_loop() -> None:
    log.info("☀️  Quote loop started")
    while True:
        try:
            if not db_pool:
                await asyncio.sleep(QUOTE_CHECK_INTERVAL)
                continue
            now = datetime.now(MOSCOW_TZ)
            today = now.strftime("%Y-%m-%d")
            last_date = await db_get_state("last_quote_date")
            if now.hour == QUOTE_TIME_HOUR and now.minute < QUOTE_TIME_MINUTE_MAX and last_date != today:
                await db_set_state("last_quote_date", today)
                quote, author = await db_get_next_quote()
                try:
                    await bot.send_message(
                        GROUP_ID,
                        f"☀️ <b>Доброе утро, ЭГОИСТЫ!</b>\n\n"
                        f"💬 <i>«{quote}»</i>\n— <b>{author}</b>",
                        parse_mode="HTML", message_thread_id=CHAT_TOPIC_ID
                    )
                    log.info(f"☀️  Quote sent: {author}")
                except Exception as e:
                    log.error(f"send daily quote: {e}")
        except Exception as e:
            log.error(f"quote_loop: {e}")
        await asyncio.sleep(QUOTE_CHECK_INTERVAL)


# ============================================================================
# 🛠 UTILITIES
# ============================================================================

async def auto_delete(message, delay: int = AUTO_DELETE_DEFAULT) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


def is_admin_private(message: Message) -> bool:
    return message.chat.type == "private" and message.from_user.id == ADMIN_ID


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📋 Stratbook", callback_data="section:strat"),
        InlineKeyboardButton("💣 Nades", callback_data="section:nades"),
    )
    kb.add(InlineKeyboardButton("📅 Календарь", web_app=WebAppInfo(url=WEBAPP_URL)))
    return kb


def map_menu(section: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("Mirage", callback_data=f"map:{section}:mirage"),
        InlineKeyboardButton("Dust 2", callback_data=f"map:{section}:dust2"),
        InlineKeyboardButton("Ancient", callback_data=f"map:{section}:ancient"),
    )
    if section == "nades":
        kb.add(InlineKeyboardButton("⚡️ Insta", url=INSTA_LINK))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back:main"))
    return kb


def link_menu(label, url, back_to):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(label, url=url))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=back_to))
    return kb


def back_menu(back_to):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=back_to))
    return kb


async def on_startup(dp: Dispatcher) -> None:
    log.info("=" * 50)
    log.info("🤖 EGOIST BOT STARTING")
    log.info(f"BOT_TOKEN: {'✓' if BOT_TOKEN else '✗'}")
    log.info(f"DATABASE_URL: {'✓' if DATABASE_URL else '✗'}")
    log.info(f"WEBAPP_URL: {WEBAPP_URL}")
    log.info("=" * 50)
    try:
        await db_init()
    except Exception as e:
        log.error(f"❌ DB INIT FAILED: {e}")
    await db_set_state("last_startup", datetime.now(UTC).isoformat())
    asyncio.create_task(calendar_loop())
    asyncio.create_task(quote_loop())
    asyncio.create_task(availability_watcher())
    asyncio.create_task(start_api_server())
    try:
        await bot.edit_message_text(
            MAIN_MENU_TEXT, chat_id=GROUP_ID, message_id=PINNED_MESSAGE_ID,
            parse_mode="HTML", reply_markup=main_menu()
        )
        log.info("✓ Pinned message updated")
    except Exception as e:
        log.error(f"update pinned: {e}")
    log.info("✅ Bot is ready!")


# ============================================================================
# 📋 COMMANDS
# ============================================================================

@dp.message_handler(commands=["help"])
async def cmd_help(message: Message) -> None:
    if not is_admin_private(message):
        return
    await message.reply(
        "📋 <b>Команды:</b>\n\n"
        "📅 /calendar — открыть календарь сборов\n"
        "📌 /calendarpost — закрепить кнопку календаря в ПРАКАХ\n"
        "📅 /upcoming — ближайшие праки\n"
        "💬 /quote — отправить цитату\n"
        "📜 /logs — последние действия\n"
        "🔔 /notify текст — уведомление\n"
        "📌 /post — закреплённое сообщение\n"
        "🔄 /restart — перезапустить бота\n"
        "🩺 /status — статус бота\n"
        "👥 /team — состав команды\n"
        "➕ /addplayer ID username display — добавить игрока\n"
        "🆔 /id — узнать ID топика\n"
        "🆔 /myid — узнать свой ID (для игроков)\n"
        "📖 /maps — меню карт",
        parse_mode="HTML"
    )


@dp.message_handler(commands=["status"])
async def cmd_status(message: Message) -> None:
    if not is_admin_private(message):
        return
    last_startup = await db_get_state("last_startup")
    last_quote = await db_get_state("last_quote_date")
    calendar_init = await db_get_state("calendar_initialized")
    team = await db_get_team()
    text = "🩺 <b>Статус бота:</b>\n\n"
    text += f"💾 БД: {'✓' if db_pool else '✗'}\n"
    text += f"🌐 API: порт {API_PORT}\n"
    text += f"🚀 Запуск: <code>{last_startup or '-'}</code>\n"
    text += f"☀️ Цитата: <code>{last_quote or '-'}</code>\n"
    text += f"📅 Календарь: <code>{calendar_init or '-'}</code>\n"
    text += f"👥 Игроков: {len(team)}/{TEAM_SIZE}\n"
    text += f"🌐 WebApp: {WEBAPP_URL}\n"
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["team"])
async def cmd_team(message: Message) -> None:
    if not is_admin_private(message):
        return
    team = await db_get_team()
    if not team:
        await message.reply("👥 Команда пустая. Добавь игроков через /addplayer")
        return
    text = "👥 <b>Состав команды:</b>\n\n"
    for p in team:
        text += f"• <code>{p['user_id']}</code> @{p['username']} ({p['display_name']})\n"
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["addplayer"])
async def cmd_addplayer(message: Message) -> None:
    if not is_admin_private(message):
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.reply(
            "ℹ️ Использование:\n"
            "<code>/addplayer USER_ID username display_name</code>\n\n"
            "USER_ID можно узнать попросив игрока написать боту /myid",
            parse_mode="HTML"
        )
        return
    try:
        user_id = int(parts[1])
        username = parts[2].lstrip("@")
        display = parts[3]
        if await db_add_player(user_id, username, display):
            await message.reply(f"✅ Добавлен: @{username} ({display})")
        else:
            await message.reply("❌ Ошибка")
    except ValueError:
        await message.reply("❌ USER_ID должен быть числом")


@dp.message_handler(commands=["myid"])
async def cmd_myid(message: Message) -> None:
    sent = await message.reply(
        f"🆔 Твой ID: <code>{message.from_user.id}</code>\n"
        f"👤 @{message.from_user.username or 'нет'}",
        parse_mode="HTML"
    )
    asyncio.create_task(auto_delete(sent, 120))


@dp.message_handler(commands=["calendar"])
async def cmd_calendar(message: Message) -> None:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=WEBAPP_URL)))
    await message.reply(
        "📅 <b>Календарь сборов</b>\n\n"
        "Отметь когда можешь играть на ближайшие 14 дней.\n"
        "Когда все 5 готовы — бот сразу уведомит!",
        parse_mode="HTML", reply_markup=kb
    )


@dp.message_handler(commands=["calendarpost"])
async def cmd_calendarpost(message: Message) -> None:
    if not is_admin_private(message):
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=WEBAPP_URL)))
    sent = await bot.send_message(
        GROUP_ID,
        "📅 <b>Календарь сборов команды</b>\n\n"
        "Отметь когда можешь играть на ближайшие 14 дней.\n"
        "Когда все 5 в сборе — бот сразу сообщит!\n\n"
        "🌅 Утро (10-14) • 🌇 День (14-19) • 🌃 Вечер (19-23)",
        parse_mode="HTML",
        message_thread_id=SCRIMS_TOPIC_ID,
        reply_markup=kb
    )
    try:
        await bot.pin_chat_message(GROUP_ID, sent.message_id, disable_notification=True)
    except Exception as e:
        log.error(f"pin calendar: {e}")
    await message.reply("✅ Отправлено в ПРАКИ и закреплено!")


@dp.message_handler(commands=["restart"])
async def cmd_restart(message: Message) -> None:
    if not is_admin_private(message):
        return
    await message.reply("🔄 Перезапускаю...")
    await db_log_action(message.from_user, "Перезапустил бота")
    await asyncio.sleep(1)
    os._exit(0)


@dp.message_handler(commands=["logs"])
async def cmd_logs(message: Message) -> None:
    if not is_admin_private(message):
        return
    logs = await db_get_logs(20)
    if not logs:
        await message.reply("📭 Пока пусто.")
        return
    text = "📜 <b>Последние действия:</b>\n\n"
    for entry in logs:
        ts = entry['timestamp'].replace(tzinfo=UTC).astimezone(MOSCOW_TZ)
        text += f"🕐 <code>{ts.strftime('%d.%m %H:%M')}</code>\n👤 {entry['username']}\n➡️ {entry['action']}\n\n"
    await message.reply(text[:4000], parse_mode="HTML")


@dp.message_handler(commands=["quote"])
async def cmd_quote(message: Message) -> None:
    if not is_admin_private(message):
        return
    quote, author = await db_get_next_quote()
    await bot.send_message(
        GROUP_ID, f"💬 <i>«{quote}»</i>\n— <b>{author}</b>",
        parse_mode="HTML", message_thread_id=CHAT_TOPIC_ID
    )
    await message.reply("✅ Отправлено!")


@dp.message_handler(commands=["upcoming"])
async def cmd_upcoming(message: Message) -> None:
    if not is_admin_private(message):
        return
    events = await calendar_fetch_events()
    if not events:
        await message.reply("📭 Праков нет.")
        return
    text = "📅 <b>Ближайшие праки:</b>\n\n"
    for event in events[:10]:
        summary = event.get('summary', 'Прак')
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = event_time.astimezone(MOSCOW_TZ)
            text += f"🗺 {summary} — {local_time.strftime('%d.%m.%Y %H:%M')}\n"
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["post"])
async def cmd_post(message: Message) -> None:
    if not is_admin_private(message):
        return
    await bot.send_message(
        GROUP_ID, MAIN_MENU_TEXT,
        parse_mode="HTML", message_thread_id=STRATBOOK_TOPIC_ID,
        reply_markup=main_menu()
    )
    await message.reply("✅ Отправлено!")


@dp.message_handler(commands=["notify"])
async def cmd_notify(message: Message) -> None:
    if not is_admin_private(message):
        return
    text = message.text.replace("/notify", "").strip()
    if not text:
        return
    await bot.send_message(
        GROUP_ID, f"🔔 <b>Обновление от 5 LVL FACEIT!</b>\n\n{text}",
        parse_mode="HTML", message_thread_id=STRATBOOK_TOPIC_ID
    )
    await message.reply("✅ Отправлено!")


@dp.message_handler(commands=["id"])
async def cmd_id(message: Message) -> None:
    sent = await message.reply(
        f"🆔 Чат: <code>{message.chat.id}</code>\n"
        f"🆔 Топик: <code>{message.message_thread_id}</code>",
        parse_mode="HTML"
    )
    asyncio.create_task(auto_delete(sent))


@dp.message_handler(commands=["maps"])
async def cmd_maps(message: Message) -> None:
    sent = await message.reply(
        "🗺️ <b>Выбери раздел:</b>",
        parse_mode="HTML", reply_markup=main_menu()
    )
    asyncio.create_task(auto_delete(sent))


@dp.message_handler()
async def handle_keywords(message: Message) -> None:
    if not message.text:
        return
    text = message.text.lower().strip()
    for keyword, map_id in MAP_KEYWORDS.items():
        if keyword in text:
            sent = await message.reply(
                f"📍 <b>{map_id.upper()}</b>\nВыбери раздел:",
                parse_mode="HTML", reply_markup=main_menu()
            )
            asyncio.create_task(auto_delete(sent))
            return


@dp.callback_query_handler(lambda c: c.data.startswith("section:"))
async def cb_section(call: CallbackQuery) -> None:
    section = call.data.split(":")[1]
    label = "📋 Stratbook" if section == "strat" else "💣 Nades"
    await db_log_action(call.from_user, f"Открыл {label}")
    await call.message.edit_text(
        f"{label}\n\n🗺️ <b>Выбери карту:</b>",
        parse_mode="HTML", reply_markup=map_menu(section)
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("map:"))
async def cb_map(call: CallbackQuery) -> None:
    _, section, map_id = call.data.split(":")
    section_name = "Stratbook" if section == "strat" else "Nades"
    await db_log_action(call.from_user, f"Открыл {section_name} — {map_id.upper()}")
    source = STRAT_BOOKS if section == "strat" else NADES
    link = source.get(map_id)
    if link:
        title = f"📋 <b>Stratbook — {map_id.upper()}</b>" if section == "strat" else f"💣 <b>Nades — {map_id.upper()}</b>"
        button_label = "📋 Открыть" if section == "strat" else "💣 Смотреть"
        await call.message.edit_text(
            title, parse_mode="HTML",
            reply_markup=link_menu(button_label, link, f"section:{section}")
        )
    else:
        await call.message.edit_text(
            f"😔 Нет для {map_id.upper()}",
            parse_mode="HTML", reply_markup=back_menu(f"section:{section}")
        )
    await call.answer()
    await asyncio.sleep(MENU_RESET_DELAY)
    try:
        await call.message.edit_text(MAIN_MENU_TEXT, parse_mode="HTML", reply_markup=main_menu())
    except Exception:
        pass


@dp.callback_query_handler(lambda c: c.data == "back:main")
async def cb_back(call: CallbackQuery) -> None:
    await call.message.edit_text(MAIN_MENU_TEXT, parse_mode="HTML", reply_markup=main_menu())
    await call.answer()


if __name__ == "__main__":
    log.info("🎬 Starting polling...")
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
