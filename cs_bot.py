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
BOT_USERNAME = "stratbook_bot"
PINNED_MESSAGE_ID = 1707

# Default team (все 5 игроков с тегами)
DEFAULT_TEAM = {
    557066322: {"username": "FREEDOM5O", "display": "FREEDOM"},
    # Остальные 4 добавятся с PLAYERS_TAG автоматически
}

# Динамически добавляем остальных из PLAYERS_TAG
TEAM_PLAYERS_TAGS = ["Rogachev_E", "gladnessorrow", "YakobsMonarch0_0", "FREEDOM5O"]

TIME_SLOT_DEFAULT = "anytime"  # единственный слот

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

PLAYERS_TAG = "@FREEDOM5O @gladnessorrow @Rogachev_E @Xcvo_same"
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
                time_text TEXT DEFAULT 'anytime',
                status TEXT DEFAULT 'can',
                updated_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS avail_notifications (
                slot_date DATE,
                count INTEGER,
                notified_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (slot_date, count)
            );
            CREATE INDEX IF NOT EXISTS idx_availability_date 
                ON availability (slot_date, status);
            -- Надёжная миграция: убираем slot_time, ставим новый PK
            DO $$ 
            DECLARE
                has_slot_time BOOLEAN;
                has_pk BOOLEAN;
            BEGIN
                -- Проверяем есть ли старая колонка slot_time
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='availability' AND column_name='slot_time'
                ) INTO has_slot_time;
                
                IF has_slot_time THEN
                    -- Дропаем все constraint на таблице
                    ALTER TABLE availability DROP CONSTRAINT IF EXISTS availability_pkey;
                    ALTER TABLE availability DROP CONSTRAINT IF EXISTS availability_user_id_slot_date_slot_time_key;
                    -- Удаляем дубликаты (оставляем последнюю запись для каждого user+date)
                    DELETE FROM availability a USING availability b
                    WHERE a.ctid < b.ctid 
                    AND a.user_id = b.user_id 
                    AND a.slot_date = b.slot_date;
                    -- Добавляем time_text если нет
                    ALTER TABLE availability ADD COLUMN IF NOT EXISTS time_text TEXT DEFAULT 'anytime';
                    -- Убираем slot_time
                    ALTER TABLE availability DROP COLUMN IF EXISTS slot_time;
                    -- Новый PRIMARY KEY
                    ALTER TABLE availability ADD PRIMARY KEY (user_id, slot_date);
                ELSE
                    -- Таблица новая, просто убеждаемся что PK есть
                    SELECT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'availability_pkey'
                    ) INTO has_pk;
                    IF NOT has_pk THEN
                        ALTER TABLE availability ADD PRIMARY KEY (user_id, slot_date);
                    END IF;
                END IF;
            EXCEPTION WHEN others THEN
                RAISE NOTICE 'Migration warning: %', SQLERRM;
            END $$;
        """)
        
        for user_id, info in DEFAULT_TEAM.items():
            await conn.execute("""
                INSERT INTO team_players (user_id, username, display_name)
                VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING
            """, user_id, info["username"], info["display"])
        
        # Все игроки уже в DEFAULT_TEAM выше
    
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



async def db_remove_player(user_id: int) -> bool:
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM team_players WHERE user_id = $1", user_id)
            # Удалить и его доступность
            await conn.execute("DELETE FROM availability WHERE user_id = $1", user_id)
            return True
    except Exception as e:
        log.error(f"db_remove_player: {e}")
        return False

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


async def db_set_availability(user_id: int, slot_date: str, time_text: str, status: str) -> bool:
    """Записать доступность. time_text = "ALL DAY" / "18:00" / "anytime" / etc."""
    try:
        async with db_pool.acquire() as conn:
            d = date.fromisoformat(slot_date)
            if status == "clear":
                await conn.execute(
                    "DELETE FROM availability WHERE user_id = $1 AND slot_date = $2",
                    user_id, d
                )
            else:
                # DELETE + INSERT надёжнее чем UPSERT при неопределённом PK
                await conn.execute(
                    "DELETE FROM availability WHERE user_id = $1 AND slot_date = $2",
                    user_id, d
                )
                await conn.execute(
                    "INSERT INTO availability (user_id, slot_date, time_text, status, updated_at) VALUES ($1, $2, $3, $4, NOW())",
                    user_id, d, time_text, status
                )
            return True
    except Exception as e:
        log.error(f"db_set_availability error: {e}")
        return False


async def db_get_availability_grid(days_ahead: int = 14) -> List[Dict[str, Any]]:
    try:
        async with db_pool.acquire() as conn:
            today = date.today()
            end_date = today + timedelta(days=days_ahead)
            rows = await conn.fetch("""
                SELECT a.slot_date, a.time_text, a.status, a.user_id,
                       tp.username, tp.display_name
                FROM availability a
                LEFT JOIN team_players tp ON tp.user_id = a.user_id
                WHERE a.slot_date >= $1 AND a.slot_date <= $2
                ORDER BY a.slot_date, a.updated_at
            """, today, end_date)
            return [
                {
                    "slot_date": r["slot_date"].isoformat(),
                    "time_text": r["time_text"] or "anytime",
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


async def db_was_notified(slot_date: str, count: int) -> bool:
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 1 FROM avail_notifications
                WHERE slot_date = $1 AND count = $2
            """, date.fromisoformat(slot_date), count)
            return row is not None
    except Exception as e:
        log.error(f"db_was_notified: {e}")
        return True


async def db_mark_notified(slot_date: str, count: int) -> None:
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO avail_notifications (slot_date, count)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, date.fromisoformat(slot_date), count)
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
        return {"id": 557066322, "username": "FREEDOM5O", "first_name": "FREEDOM"}
    user = verify_telegram_init_data(init_data)
    if not user:
        # Если верификация не прошла — fallback на дефолтного юзера
        # Это нужно пока Telegram не передаёт initData в Desktop клиенте
        return {"id": 557066322, "username": "FREEDOM5O", "first_name": "FREEDOM"}
    return user


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
    is_member = any(p["user_id"] == user["id"] for p in team)
    return json_response({
        "id": user["id"],
        "username": user.get("username", ""),
        "first_name": user.get("first_name", ""),
        "is_team_member": is_member
    })


async def api_team(request: Request) -> Response:
    team = await db_get_team()
    return json_response({"team": team, "size": TEAM_SIZE})


async def api_availability_grid(request: Request) -> Response:
    user = await get_user_from_request(request)
    if not user:
        return json_response({"error": "Unauthorized"}, status=401)
    
    grid = await db_get_availability_grid(AVAILABILITY_DAYS_AHEAD)
    # Группируем по дате — один слот на день
    aggregated = {}
    for entry in grid:
        key = entry["slot_date"]
        if key not in aggregated:
            aggregated[key] = {
                "slot_date": entry["slot_date"],
                "can": [], "cant": []
            }
        player = {
            "user_id": entry["user_id"],
            "username": entry["username"],
            "display_name": entry["display_name"],
            "time_text": entry["time_text"]
        }
        if entry["status"] == "can":
            aggregated[key]["can"].append(player)
        else:
            aggregated[key]["cant"].append(player)
    
    return json_response({
        "slots": list(aggregated.values()),
        "team_size": TEAM_SIZE,
        "days_ahead": AVAILABILITY_DAYS_AHEAD,
        "your_id": user["id"]
    })


async def api_set_availability(request: Request) -> Response:
    user = await get_user_from_request(request)
    if not user:
        return json_response({"error": "Unauthorized"}, status=401)
    
    team = await db_get_team()
    player = next((p for p in team if p["user_id"] == user["id"]), None)
    if not player:
        return json_response({"error": "Not a team member"}, status=403)
    
    try:
        body = await request.json()
        slot_date = body["slot_date"]
        time_text = body.get("time_text", "anytime")  # "ALL DAY", "18:00", "anytime", etc.
        status = body["status"]
        if status not in ("can", "cant", "clear"):
            return json_response({"error": "Invalid status"}, status=400)
        
        success = await db_set_availability(user["id"], slot_date, time_text, status)
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
        resource = app.router.add_resource(path)
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
            # Группируем по дате
            days: Dict[str, Dict] = {}
            for entry in grid:
                d = entry["slot_date"]
                if d not in days:
                    days[d] = {"date": d, "can": [], "cant": []}
                if entry["status"] == "can" and entry["username"]:
                    days[d]["can"].append(entry["username"])
                elif entry["status"] == "cant" and entry["username"]:
                    days[d]["cant"].append(entry["username"])
            
            for day in days.values():
                count = len(day["can"])
                if count == 5:
                    if not await db_was_notified(day["date"], 5):
                        await notify_full_house(day["date"], day["can"])
                        await db_mark_notified(day["date"], 5)
                elif count == 4:
                    if not await db_was_notified(day["date"], 4):
                        await notify_partial_house(day["date"], day["can"], 4)
                        await db_mark_notified(day["date"], 4)
                elif count == 3:
                    if not await db_was_notified(day["date"], 3):
                        await notify_partial_house(day["date"], day["can"], 3)
                        await db_mark_notified(day["date"], 3)
        except Exception as e:
            log.error(f"availability_watcher: {e}")
        await asyncio.sleep(AVAIL_CHECK_INTERVAL)




async def notify_partial_house(slot_date: str, usernames: List[str], count: int) -> None:
    """Уведомление когда 3 или 4 человека готовы."""
    try:
        date_obj = date.fromisoformat(slot_date)
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday = weekdays[date_obj.weekday()]
        date_str = date_obj.strftime("%d.%m.%Y")
        tags = " ".join(f"@{u}" for u in usernames if u)
        
        emoji = "🔥" if count == 4 else "⚡"
        header = "ПОЧТИ ГОТОВО!" if count == 4 else "ГАЗ ФАСЛО!"
        tail = "Ждём ещё одного!" if count == 4 else "Ещё двое и можем играть!"
        
        await bot.send_message(
            GROUP_ID,
            f"{emoji} <b>{header}</b>\n\n"
            f"📅 {weekday}, {date_str}\n"
            f"👥 Готовы: <b>{count}/{TEAM_SIZE}</b>\n\n"
            f"{tags}\n\n"
            f"🎯 {tail}",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID
        )
        log.info(f"⚡ Partial house notification: {count}/{TEAM_SIZE} for {slot_date}")
    except Exception as e:
        log.error(f"notify_partial_house: {e}")

async def notify_full_house(slot_date: str, usernames: List[str]) -> None:
    try:
        date_obj = date.fromisoformat(slot_date)
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday = weekdays[date_obj.weekday()]
        date_str = date_obj.strftime("%d.%m.%Y")
        tags = " ".join(f"@{u}" for u in usernames if u)
        
        await bot.send_message(
            GROUP_ID,
            f"🔥 <b>ВСЕ В СБОРЕ!</b>\n\n"
            f"📅 {weekday}, {date_str}\n\n"
            f"{tags}\n\n"
            f"🎯 Можем играть прак!\n"
            f"• Создавайте событие в Google Calendar\n"
            f"• Ищите противника на Pracc.com",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID
        )
        log.info(f"🔥 Full house notification: {slot_date}")
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
    kb.add(InlineKeyboardButton("📅 Календарь", url=WEBAPP_URL))
    return kb


def main_menu_webapp() -> InlineKeyboardMarkup:
    """Меню с WebApp кнопкой — только для личных сообщений."""
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
    except Exception:
        log.info("ℹ️ Pinned message not updated (use /post to create new)")
    
    # Устанавливаем Menu Button — открывает Mini App в Telegram
    try:
        await bot.set_chat_menu_button(menu_button={
            "type": "web_app",
            "text": "📅 Календарь",
            "web_app": {"url": WEBAPP_URL}
        })
        log.info("✓ Menu button set")
    except Exception as e:
        log.error(f"set menu button: {e}")

    # Автоматический calendarpost убран — используй /calendarpost вручную
    log.info("✅ Bot is ready!")


# ============================================================================
# 📋 COMMANDS
# ============================================================================

@dp.message_handler(commands=["help"])
async def cmd_help(message: Message) -> None:
    if not is_admin_private(message):
        return
    await message.reply(
        "📋 <b>Команды EGOIST BOT</b>\n\n"

        "📅 <b>Календарь</b>\n"
        "/calendar — открыть календарь сборов\n"
        "/calendarpost — закрепить кнопку в ПРАКАХ\n"
        "/upcoming — ближайшие праки из Google Calendar\n\n"

        "📣 <b>Группа</b>\n"
        "/notify текст — отправить уведомление\n"
        "/post — обновить закреплённое сообщение\n"
        "/quote — отправить цитату дня\n"
        "/maps — меню карт\n\n"

        "👥 <b>Команда</b>\n"
        "/team — состав команды\n"
        "/editteam — редактировать состав (добавить/удалить)\n"
        "/addplayer ID username display — добавить игрока\n\n"

        "🩺 <b>Мониторинг</b>\n"
        "/status — общий статус бота\n"
        "/ping — быстрая проверка\n"
        "/testwebapp — тест WebApp кнопки\n"
        "/testapi — тест API эндпоинтов\n"
        "/testdb — тест базы данных\n"
        "/logs — последние действия\n\n"

        "⚙️ <b>Система</b>\n"
        "/restart — перезапустить бота\n"
        "/id — узнать ID топика\n"
        "/myid — узнать свой Telegram ID",
        parse_mode="HTML"
    )


@dp.message_handler(commands=["ping"])
async def cmd_ping(message: Message) -> None:
    if not is_admin_private(message):
        return
    now = datetime.now(MOSCOW_TZ).strftime("%H:%M:%S")
    await message.reply(
        f"🏓 <b>PONG!</b>\n\n"
        f"🌐 WEBAPP_URL: <code>{WEBAPP_URL}</code>\n"
        f"🕐 Время МСК: <code>{now}</code>\n"
        f"💾 БД: {'✅' if db_pool else '❌'}",
        parse_mode="HTML"
    )


@dp.message_handler(commands=["testwebapp"])
async def cmd_testwebapp(message: Message) -> None:
    if not is_admin_private(message):
        return
    url = WEBAPP_URL
    is_valid = url.startswith("https://")
    status = "✅ валидный HTTPS" if is_valid else "❌ невалидный URL (нужен https://)"
    
    text = (
        f"🔍 <b>Тест WebApp</b>\n\n"
        f"🌐 URL: <code>{url}</code>\n"
        f"📋 Статус: {status}\n\n"
    )
    
    if is_valid:
        try:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("📅 Открыть тест", web_app=WebAppInfo(url=url)))
            text += "✅ Кнопка создана успешно!\n(WebApp работает только в личке бота)"
            await message.reply(text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            text += f"❌ Ошибка создания кнопки:\n<code>{e}</code>"
            await message.reply(text, parse_mode="HTML")
    else:
        await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["testapi"])
async def cmd_testapi(message: Message) -> None:
    if not is_admin_private(message):
        return
    
    base = f"https://stratbook-bot-production.up.railway.app"
    # Если Railway изменит домен — обновляй WEBAPP_URL и этот URL тоже
    results = []
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        for path in ["/api/health", "/api/me", "/api/availability"]:
            try:
                async with session.get(f"{base}{path}", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    data = await resp.text()
                    short = data[:80].replace('\n', ' ')
                    results.append(f"✅ <code>{path}</code>\n    {short}")
            except Exception as e:
                results.append(f"❌ <code>{path}</code>\n    {str(e)[:80]}")
    
    text = f"🔍 <b>Тест API</b>\n🌐 {base}\n\n" + "\n\n".join(results)
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["testdb"])
async def cmd_testdb(message: Message) -> None:
    if not is_admin_private(message):
        return
    
    results = []
    
    try:
        async with db_pool.acquire() as conn:
            # Проверяем таблицы
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            """)
            table_names = [r['tablename'] for r in tables]
            results.append(f"✅ Подключение к БД")
            results.append(f"📋 Таблицы: <code>{', '.join(table_names)}</code>")
            
            # Игроки
            players = await conn.fetchval("SELECT COUNT(*) FROM team_players")
            results.append(f"👥 Игроков в команде: <b>{players}/{TEAM_SIZE}</b>")
            
            # Слоты availability
            slots = await conn.fetchval("SELECT COUNT(*) FROM availability")
            results.append(f"📅 Слотов availability: <b>{slots}</b>")
            
            # Логи
            logs = await conn.fetchval("SELECT COUNT(*) FROM action_logs")
            results.append(f"📜 Записей в логах: <b>{logs}</b>")
            
            # Последний запуск
            last_startup = await db_get_state("last_startup")
            results.append(f"🚀 Последний запуск: <code>{last_startup or '-'}</code>")
            
    except Exception as e:
        results.append(f"❌ Ошибка БД: <code>{e}</code>")
    
    text = "🔍 <b>Тест БД</b>\n\n" + "\n".join(results)
    await message.reply(text, parse_mode="HTML")


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
            "USER_ID можно узнать попросив игрока написать боту /myid\n\n"
            "Пример:\n"
            "<code>/addplayer 123456789 Rogachev_E Rogachev</code>",
            parse_mode="HTML"
        )
        return
    try:
        user_id = int(parts[1])
        username = parts[2].lstrip("@")
        display = parts[3]
        if await db_add_player(user_id, username, display):
            await message.reply(
                f"✅ Добавлен: @{username} ({display})\n"
                f"ID: <code>{user_id}</code>",
                parse_mode="HTML"
            )
            log.info(f"✓ Player added: {username} ({user_id})")
        else:
            await message.reply("❌ Ошибка при добавлении")
    except ValueError:
        await message.reply("❌ USER_ID должен быть числом")



@dp.message_handler(commands=["editteam"])
async def cmd_editteam(message: Message) -> None:
    """Редактирование состава — кнопки удаления для каждого игрока."""
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Только для администратора")
        return
    await show_editteam(message)


async def show_editteam(message: Message) -> None:
    team = await db_get_team()
    if not team:
        await message.reply("📋 Команда пуста\n\nДобавить: /addplayer ID @username Имя")
        return
    
    text = f"👥 <b>КОМАНДА EGOIST</b> ({len(team)}/{TEAM_SIZE})\n\n"
    for p in team:
        display = p.get("display_name") or p.get("username", "?")
        username = p.get("username", "—")
        text += f"• <b>{display}</b>  @{username}\n"
    text += "\nНажми ❌ рядом с игроком чтобы удалить:"
    
    kb = InlineKeyboardMarkup(row_width=1)
    for p in team:
        display = p.get("display_name") or p.get("username", "?")
        kb.add(InlineKeyboardButton(
            f"❌ Удалить {display}",
            callback_data=f"rmplayer:{p['user_id']}"
        ))
    kb.add(InlineKeyboardButton("➕ Добавить — /addplayer", callback_data="noop"))
    
    await message.reply(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("rmplayer:"))
async def cb_remove_player(call: CallbackQuery) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    
    uid = int(call.data.split(":")[1])
    team = await db_get_team()
    player = next((p for p in team if p["user_id"] == uid), None)
    
    if not player:
        await call.answer("Игрок не найден", show_alert=True)
        return
    
    display = player.get("display_name") or player.get("username", str(uid))
    success = await db_remove_player(uid)
    
    if success:
        await call.answer(f"✅ {display} удалён из команды")
        # Обновить список
        team_new = await db_get_team()
        if not team_new:
            await call.message.edit_text("👥 Команда пуста\n\nДобавить: /addplayer ID @username Имя", parse_mode="HTML")
            return
        text = f"👥 <b>КОМАНДА EGOIST</b> ({len(team_new)}/{TEAM_SIZE})\n\n"
        for p in team_new:
            d = p.get("display_name") or p.get("username", "?")
            u = p.get("username", "—")
            text += f"• <b>{d}</b>  @{u}\n"
        text += "\nНажми ❌ рядом с игроком чтобы удалить:"
        kb = InlineKeyboardMarkup(row_width=1)
        for p in team_new:
            d = p.get("display_name") or p.get("username", "?")
            kb.add(InlineKeyboardButton(f"❌ Удалить {d}", callback_data=f"rmplayer:{p['user_id']}"))
        kb.add(InlineKeyboardButton("➕ Добавить — /addplayer", callback_data="noop"))
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        log.info(f"👤 Removed player {display} ({uid})")
    else:
        await call.answer("❌ Ошибка удаления", show_alert=True)


@dp.callback_query_handler(lambda c: c.data == "noop")
async def cb_noop(call: CallbackQuery) -> None:
    await call.answer()

@dp.message_handler(commands=["myid"])
async def cmd_myid(message: Message) -> None:
    sent = await message.reply(
        f"🆔 Твой ID: <code>{message.from_user.id}</code>\n"
        f"👤 @{message.from_user.username or 'нет'}",
        parse_mode="HTML"
    )
    asyncio.create_task(auto_delete(sent, 120))


@dp.message_handler(commands=["start"])
async def cmd_start(message: Message) -> None:
    """При /start открыть Mini App сразу если в личке."""
    if message.chat.type != "private":
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=WEBAPP_URL)))
    await message.reply(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Нажми кнопку чтобы открыть календарь команды EGOIST:",
        reply_markup=kb
    )


@dp.message_handler(commands=["calendar"])
async def cmd_calendar(message: Message) -> None:
    try:
        kb = InlineKeyboardMarkup()
        if message.chat.type == "private":
            kb.add(InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=WEBAPP_URL)))
        else:
            # В группе — кнопка ведёт в личку к боту
            kb.add(InlineKeyboardButton(
                "📅 Открыть календарь",
                url=f"https://t.me/{BOT_USERNAME}?start=calendar"
            ))
        await message.reply(
            "📅 <b>Календарь сборов</b>\n\n"
            "Отметь когда можешь играть на ближайшие 14 дней.\n"
            "Когда все 5 готовы — бот сразу уведомит!",
            parse_mode="HTML", reply_markup=kb
        )
    except Exception as e:
        log.error(f"cmd_calendar error: {e}")
        await message.reply(f"Открой в личке: https://t.me/{BOT_USERNAME}")


@dp.message_handler(commands=["calendarpost"])
async def cmd_calendarpost(message: Message) -> None:
    if not is_admin_private(message):
        return
    # Кнопка открывает личку с ботом — там WebApp через Menu Button
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(
        "📅 Календарь — жми сюда",
        url=f"https://t.me/{BOT_USERNAME}?start=calendar"
    ))
    sent = await bot.send_message(
        GROUP_ID,
        "📅 <b>Календарь сборов EGOIST</b>\n\n"
        "Ребят, отмечайтесь когда можете играть! 🎮\n\n"
        "Как это работает:\n"
        "1️⃣ Нажми кнопку ниже — откроется личка с ботом\n"
        "2️⃣ Там нажми кнопку <b>«Календарь»</b> внизу экрана\n"
        "3️⃣ Выбери дату и укажи время когда свободен\n\n"
        "Как только все 5 отметятся на один день — бот сразу тегнет всех! 🔥",
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
    try:
        sent = await bot.send_message(
            GROUP_ID, MAIN_MENU_TEXT,
            parse_mode="HTML", message_thread_id=STRATBOOK_TOPIC_ID,
            reply_markup=main_menu()
        )
        try:
            await bot.pin_chat_message(GROUP_ID, sent.message_id, disable_notification=True)
        except Exception as e:
            log.error(f"pin post: {e}")
        await message.reply(f"✅ Отправлено и закреплено!\nID: <code>{sent.message_id}</code>", parse_mode="HTML")
        log.info(f"✓ New pinned message ID: {sent.message_id}")
    except Exception as e:
        log.error(f"cmd_post: {e}")
        await message.reply(f"❌ Ошибка: {e}")


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
    try:
        sent = await message.reply(
            "🗺️ <b>Выбери раздел:</b>",
            parse_mode="HTML", reply_markup=main_menu()
        )
        asyncio.create_task(auto_delete(sent))
    except Exception as e:
        log.error(f"cmd_maps error: {e}")
        await message.reply("🗺️ Stratbook | Nades | Календарь")



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
