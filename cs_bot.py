"""
EGOIST CS2 Telegram Bot
@stratbook_bot

Features:
- Stratbook & nades menu
- Google Calendar integration with scrim reminders
- Daily motivational quotes
- Action logging
- PostgreSQL persistence (prevents duplicates after restarts)
"""

import os
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from google.oauth2 import service_account
from googleapiclient.discovery import build
import asyncpg


# ============================================================================
# 🔧 CONFIGURATION
# ============================================================================

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
DATABASE_URL = os.getenv("DATABASE_URL")

# Google Calendar
CALENDAR_ID = "85f813a348453bc70b98c82024ac2d7db492896a82798537ce2a4e7175a0feb3@group.calendar.google.com"

# Telegram IDs
GROUP_ID = -1003680698112
STRATBOOK_TOPIC_ID = 1542
SCRIMS_TOPIC_ID = 15
CHAT_TOPIC_ID = 13
ADMIN_ID = 557066322
PINNED_MESSAGE_ID = 1707

# Timings (seconds)
CALENDAR_CHECK_INTERVAL = 600       # 10 минут
QUOTE_CHECK_INTERVAL = 300          # 5 минут
AUTO_DELETE_DEFAULT = 60            # 1 минута
AUTO_DELETE_HOUR = 3600             # 1 час
AUTO_DELETE_DAY = 82800             # 23 часа
MENU_RESET_DELAY = 15               # 15 сек
QUOTE_TIME_HOUR = 10                # 10:00 МСК
QUOTE_TIME_MINUTE_MAX = 5           # До 10:05

# Time zones
MOSCOW_TZ = timezone(timedelta(hours=3))
UTC = timezone.utc

# Content
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


# ============================================================================
# 📝 LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("egoist_bot")

logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


# ============================================================================
# 🤖 BOT INSTANCE
# ============================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
db_pool: Optional[asyncpg.Pool] = None


# ============================================================================
# 💾 DATABASE LAYER
# ============================================================================

async def db_init() -> None:
    """Initialize database connection and create tables."""
    global db_pool
    
    log.info("📊 Connecting to PostgreSQL...")
    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        command_timeout=30
    )
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
        """)
    log.info("✓ Tables ready")


async def db_get_state(key: str) -> Optional[str]:
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM bot_state WHERE key = $1", key)
            return row['value'] if row else None
    except Exception as e:
        log.error(f"db_get_state({key}): {e}")
        return None


async def db_set_state(key: str, value: str) -> None:
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bot_state (key, value, updated_at) 
                VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE 
                SET value = EXCLUDED.value, updated_at = NOW()
            """, key, value)
    except Exception as e:
        log.error(f"db_set_state({key}): {e}")


async def db_get_event(event_id: str) -> Optional[Dict[str, Any]]:
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM processed_events WHERE event_id = $1",
                event_id
            )
            return dict(row) if row else None
    except Exception as e:
        log.error(f"db_get_event({event_id}): {e}")
        return None


async def db_mark_event(
    event_id: str,
    notified_new: bool = False,
    notified_day: bool = False,
    notified_hour: bool = False
) -> bool:
    """
    Mark event as notified.
    CRITICAL: Must be called BEFORE sending message to prevent duplicates on crash.
    Uses OR logic so we never un-set a true flag.
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processed_events 
                    (event_id, notified_new, notified_day, notified_hour)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (event_id) DO UPDATE SET
                    notified_new = processed_events.notified_new OR EXCLUDED.notified_new,
                    notified_day = processed_events.notified_day OR EXCLUDED.notified_day,
                    notified_hour = processed_events.notified_hour OR EXCLUDED.notified_hour
            """, event_id, notified_new, notified_day, notified_hour)
            return True
    except Exception as e:
        log.error(f"db_mark_event({event_id}): {e}")
        return False


async def db_log_action(user: types.User, action: str) -> None:
    try:
        async with db_pool.acquire() as conn:
            username = user.username or user.full_name or str(user.id)
            display = f"@{username}" if user.username else username
            await conn.execute(
                "INSERT INTO action_logs (username, action) VALUES ($1, $2)",
                display, action
            )
    except Exception as e:
        log.error(f"db_log_action: {e}")


async def db_get_logs(limit: int = 20) -> List[Dict[str, Any]]:
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM action_logs ORDER BY timestamp DESC LIMIT $1",
                limit
            )
            return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"db_get_logs: {e}")
        return []


async def db_get_next_quote() -> Tuple[str, str]:
    """Get unused quote and mark as used. Resets pool when exhausted."""
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                used_rows = await conn.fetch("SELECT quote_index FROM used_quotes")
                used = {row['quote_index'] for row in used_rows}
                
                available = [i for i in range(len(QUOTES)) if i not in used]
                
                if not available:
                    log.info("🔄 All quotes used, resetting pool")
                    await conn.execute("DELETE FROM used_quotes")
                    available = list(range(len(QUOTES)))
                
                idx = random.choice(available)
                await conn.execute(
                    "INSERT INTO used_quotes (quote_index) VALUES ($1) ON CONFLICT DO NOTHING",
                    idx
                )
                return QUOTES[idx]
    except Exception as e:
        log.error(f"db_get_next_quote: {e}")
        return QUOTES[0]


# ============================================================================
# 📅 GOOGLE CALENDAR
# ============================================================================

def calendar_service():
    try:
        creds_info = json.loads(GOOGLE_CREDS_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
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
            calendarId=CALENDAR_ID,
            timeMin=now,
            timeMax=later,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return result.get('items', [])
    except Exception as e:
        log.error(f"calendar_fetch_events: {e}")
        return []


async def calendar_loop() -> None:
    """
    Calendar checking loop with anti-duplicate protection.
    
    Strategy:
    1. On FIRST run ever: mark all existing events as already-notified.
       Bot won't spam about events that existed before bot was set up.
    2. On RESTART: events already in DB stay processed (no duplicates).
    3. NEW events appearing after init: notify normally.
    4. Always mark DB BEFORE sending (crash-safe).
    """
    log.info("📅 Calendar loop started")
    
    first_run_marker = await db_get_state("calendar_initialized")
    is_first_run = (first_run_marker is None)
    
    if is_first_run:
        log.info("🆕 First-time calendar setup (will skip existing events)")
    else:
        log.info(f"♻️  Calendar resuming (initialized: {first_run_marker})")
    
    while True:
        try:
            if not db_pool:
                log.warning("⏸  DB not ready, waiting")
                await asyncio.sleep(CALENDAR_CHECK_INTERVAL)
                continue
            
            events = await calendar_fetch_events()
            now = datetime.now(UTC)
            
            for event in events:
                await _process_event(event, now, is_first_run)
            
            if is_first_run:
                await db_set_state(
                    "calendar_initialized",
                    datetime.now(UTC).isoformat()
                )
                is_first_run = False
                log.info("✓ Calendar initialized, future events will trigger notifications")
        
        except Exception as e:
            log.error(f"calendar_loop: {e}")
        
        await asyncio.sleep(CALENDAR_CHECK_INTERVAL)


async def _process_event(event: Dict, now: datetime, is_first_run: bool) -> None:
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
            # First time bot sees calendar: don't spam about existing events
            await db_mark_event(
                event_id,
                notified_new=True,
                notified_day=True,
                notified_hour=True
            )
            log.info(f"⏭  Marked existing event as processed: {summary}")
            return
        else:
            # New event appeared after bot was running
            await _send_new_scrim(event_id, summary, date_str, time_str, time_until)
            state = await db_get_event(event_id)
            if not state:
                return
    
    # 24h reminder window
    if (not state["notified_day"] and 
        timedelta(hours=23, minutes=50) < time_until <= timedelta(hours=24, minutes=10)):
        await _send_day_reminder(event_id, summary, date_str, time_str)
    
    # 1h reminder window
    if (not state["notified_hour"] and 
        timedelta(minutes=50) < time_until <= timedelta(hours=1, minutes=10)):
        await _send_hour_reminder(event_id, summary, time_str)


async def _send_new_scrim(event_id: str, summary: str, date_str: str, time_str: str, time_until: timedelta) -> None:
    is_soon = time_until < timedelta(hours=1)
    is_today = time_until < timedelta(hours=24)
    
    # MARK BEFORE SEND (crash protection)
    if not await db_mark_event(event_id, notified_new=True, notified_day=is_today, notified_hour=is_soon):
        log.error(f"❌ Failed to mark {event_id}, skipping send")
        return
    
    try:
        await bot.send_message(
            GROUP_ID,
            f"🎮 <b>НОВЫЙ ПРАК ИЗ КАЛЕНДАРЯ!</b>\n"
            f"📅 <i>(синхронизируется с Google Calendar и Pracc.com)</i>\n\n"
            f"🗺 {summary}\n"
            f"📅 {date_str} в {time_str}\n\n"
            f"{PLAYERS_TAG}",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID
        )
        log.info(f"📢 New scrim: {summary} ({date_str} {time_str})")
    except Exception as e:
        log.error(f"send new scrim: {e}")


async def _send_day_reminder(event_id: str, summary: str, date_str: str, time_str: str) -> None:
    if not await db_mark_event(event_id, notified_day=True):
        return
    
    try:
        sent = await bot.send_message(
            GROUP_ID,
            f"🔔 <b>Напоминание! Прак завтра!</b>\n"
            f"📅 <i>(из Google Calendar и Pracc.com)</i>\n\n"
            f"🗺 {summary}\n"
            f"📅 {date_str} в {time_str}\n\n"
            f"{PLAYERS_TAG}",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID
        )
        log.info(f"🔔 Day reminder: {summary}")
        asyncio.create_task(auto_delete(sent, AUTO_DELETE_DAY))
    except Exception as e:
        log.error(f"send day reminder: {e}")


async def _send_hour_reminder(event_id: str, summary: str, time_str: str) -> None:
    if not await db_mark_event(event_id, notified_hour=True):
        return
    
    try:
        sent = await bot.send_message(
            GROUP_ID,
            f"⏰ <b>Через час прак!</b>\n"
            f"📅 <i>(из Google Calendar и Pracc.com)</i>\n\n"
            f"🗺 {summary}\n"
            f"🕐 {time_str}\n\n"
            f"{PLAYERS_TAG}",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID
        )
        log.info(f"⏰ Hour reminder: {summary}")
        asyncio.create_task(auto_delete(sent, AUTO_DELETE_HOUR))
    except Exception as e:
        log.error(f"send hour reminder: {e}")


# ============================================================================
# ☀️ DAILY QUOTES
# ============================================================================

async def quote_loop() -> None:
    """
    Daily quote loop with anti-duplicate protection.
    
    Strategy:
    1. Check last_quote_date from DB
    2. If already sent today: skip
    3. Save date to DB BEFORE sending message
       (lose one day max if crash, never duplicate)
    """
    log.info("☀️  Quote loop started")
    
    while True:
        try:
            if not db_pool:
                await asyncio.sleep(QUOTE_CHECK_INTERVAL)
                continue
            
            now = datetime.now(MOSCOW_TZ)
            today = now.strftime("%Y-%m-%d")
            last_date = await db_get_state("last_quote_date")
            
            in_quote_window = (
                now.hour == QUOTE_TIME_HOUR and 
                now.minute < QUOTE_TIME_MINUTE_MAX
            )
            
            if in_quote_window and last_date != today:
                # SAVE DATE FIRST (crash protection)
                await db_set_state("last_quote_date", today)
                
                quote, author = await db_get_next_quote()
                
                try:
                    await bot.send_message(
                        GROUP_ID,
                        f"☀️ <b>Доброе утро, ЭГОИСТЫ!</b>\n\n"
                        f"💬 <i>«{quote}»</i>\n"
                        f"— <b>{author}</b>",
                        parse_mode="HTML",
                        message_thread_id=CHAT_TOPIC_ID
                    )
                    log.info(f"☀️  Daily quote sent: {author}")
                except Exception as e:
                    log.error(f"send daily quote: {e}")
        
        except Exception as e:
            log.error(f"quote_loop: {e}")
        
        await asyncio.sleep(QUOTE_CHECK_INTERVAL)


# ============================================================================
# 🛠 UTILITIES
# ============================================================================

async def auto_delete(message: Message, delay: int = AUTO_DELETE_DEFAULT) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


def is_admin_private(message: Message) -> bool:
    return (
        message.chat.type == "private" and 
        message.from_user.id == ADMIN_ID
    )


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📋 Stratbook", callback_data="section:strat"),
        InlineKeyboardButton("💣 Nades", callback_data="section:nades"),
    )
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


def link_menu(label: str, url: str, back_to: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(label, url=url))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=back_to))
    return kb


def back_menu(back_to: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=back_to))
    return kb


# ============================================================================
# 🚀 STARTUP
# ============================================================================

async def on_startup(dp: Dispatcher) -> None:
    log.info("=" * 50)
    log.info("🤖 EGOIST BOT STARTING")
    log.info(f"BOT_TOKEN: {'✓' if BOT_TOKEN else '✗ MISSING!'}")
    log.info(f"DATABASE_URL: {'✓' if DATABASE_URL else '✗ MISSING!'}")
    log.info(f"GOOGLE_CREDS_JSON: {'✓' if GOOGLE_CREDS_JSON else '✗ MISSING!'}")
    log.info("=" * 50)
    
    try:
        await db_init()
    except Exception as e:
        log.error(f"❌ DATABASE INIT FAILED: {e}")
        log.error("Bot will run but WITHOUT persistence — duplicates possible!")
    
    await db_set_state("last_startup", datetime.now(UTC).isoformat())
    
    asyncio.create_task(calendar_loop())
    asyncio.create_task(quote_loop())
    
    try:
        await bot.edit_message_text(
            MAIN_MENU_TEXT,
            chat_id=GROUP_ID,
            message_id=PINNED_MESSAGE_ID,
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        log.info("✓ Pinned message updated")
    except Exception as e:
        log.error(f"update pinned: {e}")
    
    log.info("✅ Bot is ready!")


# ============================================================================
# 📋 ADMIN COMMANDS
# ============================================================================

@dp.message_handler(commands=["help"])
async def cmd_help(message: Message) -> None:
    if not is_admin_private(message):
        return
    await message.reply(
        "📋 <b>Команды:</b>\n\n"
        "📅 /upcoming — ближайшие праки\n"
        "💬 /quote — отправить цитату\n"
        "📜 /logs — последние действия\n"
        "🔔 /notify текст — уведомление\n"
        "📌 /post — закреплённое сообщение\n"
        "🔄 /restart — перезапустить бота\n"
        "🩺 /status — статус бота и БД\n"
        "🆔 /id — узнать ID\n"
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
    
    text = "🩺 <b>Статус бота:</b>\n\n"
    text += f"💾 БД: {'✓ подключена' if db_pool else '✗ не подключена'}\n"
    text += f"🚀 Запуск: <code>{last_startup or 'нет данных'}</code>\n"
    text += f"☀️ Цитата: <code>{last_quote or 'не отправлялась'}</code>\n"
    text += f"📅 Календарь: <code>{calendar_init or 'не инициализирован'}</code>\n"
    
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["restart"])
async def cmd_restart(message: Message) -> None:
    if not is_admin_private(message):
        return
    await message.reply("🔄 Перезапускаю бота...")
    await db_log_action(message.from_user, "Перезапустил бота")
    await asyncio.sleep(1)
    os._exit(0)


@dp.message_handler(commands=["logs"])
async def cmd_logs(message: Message) -> None:
    if not is_admin_private(message):
        return
    
    logs = await db_get_logs(20)
    if not logs:
        await message.reply("📭 Пока нет записанных действий.")
        return
    
    text = "📜 <b>Последние действия:</b>\n\n"
    for entry in logs:
        ts = entry['timestamp'].replace(tzinfo=UTC).astimezone(MOSCOW_TZ)
        text += f"🕐 <code>{ts.strftime('%d.%m %H:%M')}</code>\n"
        text += f"👤 {entry['username']}\n"
        text += f"➡️ {entry['action']}\n\n"
    
    await message.reply(text[:4000], parse_mode="HTML")


@dp.message_handler(commands=["quote"])
async def cmd_quote(message: Message) -> None:
    if not is_admin_private(message):
        return
    
    quote, author = await db_get_next_quote()
    await bot.send_message(
        GROUP_ID,
        f"💬 <i>«{quote}»</i>\n— <b>{author}</b>",
        parse_mode="HTML",
        message_thread_id=CHAT_TOPIC_ID
    )
    await message.reply("✅ Цитата отправлена!")


@dp.message_handler(commands=["upcoming"])
async def cmd_upcoming(message: Message) -> None:
    if not is_admin_private(message):
        return
    
    events = await calendar_fetch_events()
    if not events:
        await message.reply("📭 Праков в ближайшую неделю нет.")
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
        GROUP_ID,
        MAIN_MENU_TEXT,
        parse_mode="HTML",
        message_thread_id=STRATBOOK_TOPIC_ID,
        reply_markup=main_menu()
    )
    await message.reply("✅ Отправлено!")


@dp.message_handler(commands=["notify"])
async def cmd_notify(message: Message) -> None:
    if not is_admin_private(message):
        return
    
    text = message.text.replace("/notify", "").strip()
    if not text:
        await message.reply("ℹ️ Использование: /notify текст_уведомления")
        return
    
    await bot.send_message(
        GROUP_ID,
        f"🔔 <b>Обновление от 5 LVL FACEIT!</b>\n\n{text}",
        parse_mode="HTML",
        message_thread_id=STRATBOOK_TOPIC_ID
    )
    await message.reply("✅ Отправлено!")


@dp.message_handler(commands=["id"])
async def cmd_id(message: Message) -> None:
    sent = await message.reply(
        f"🆔 ID чата: <code>{message.chat.id}</code>\n"
        f"🆔 ID топика: <code>{message.message_thread_id}</code>",
        parse_mode="HTML"
    )
    asyncio.create_task(auto_delete(sent))


@dp.message_handler(commands=["maps"])
async def cmd_maps(message: Message) -> None:
    sent = await message.reply(
        "🗺️ <b>Выбери раздел:</b>",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    asyncio.create_task(auto_delete(sent))


# ============================================================================
# 💬 MESSAGE HANDLERS
# ============================================================================

@dp.message_handler()
async def handle_keywords(message: Message) -> None:
    if not message.text:
        return
    
    text = message.text.lower().strip()
    for keyword, map_id in MAP_KEYWORDS.items():
        if keyword in text:
            sent = await message.reply(
                f"📍 <b>{map_id.upper()}</b>\nВыбери раздел:",
                parse_mode="HTML",
                reply_markup=main_menu()
            )
            asyncio.create_task(auto_delete(sent))
            return


# ============================================================================
# 🔘 CALLBACK HANDLERS
# ============================================================================

@dp.callback_query_handler(lambda c: c.data.startswith("section:"))
async def cb_section(call: CallbackQuery) -> None:
    section = call.data.split(":")[1]
    label = "📋 Stratbook" if section == "strat" else "💣 Nades"
    
    await db_log_action(call.from_user, f"Открыл {label}")
    
    await call.message.edit_text(
        f"{label}\n\n🗺️ <b>Выбери карту:</b>",
        parse_mode="HTML",
        reply_markup=map_menu(section)
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
        title = (
            f"📋 <b>Stratbook — {map_id.upper()}</b>" 
            if section == "strat" 
            else f"💣 <b>Nades — {map_id.upper()}</b>"
        )
        button_label = "📋 Открыть" if section == "strat" else "💣 Смотреть"
        
        await call.message.edit_text(
            title,
            parse_mode="HTML",
            reply_markup=link_menu(button_label, link, f"section:{section}")
        )
    else:
        await call.message.edit_text(
            f"😔 Нет для {map_id.upper()}",
            parse_mode="HTML",
            reply_markup=back_menu(f"section:{section}")
        )
    
    await call.answer()
    
    # Auto-reset to main menu after delay
    await asyncio.sleep(MENU_RESET_DELAY)
    try:
        await call.message.edit_text(
            MAIN_MENU_TEXT,
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception:
        pass


@dp.callback_query_handler(lambda c: c.data == "back:main")
async def cb_back(call: CallbackQuery) -> None:
    await call.message.edit_text(
        MAIN_MENU_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await call.answer()


# ============================================================================
# 🎬 ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    log.info("🎬 Starting polling...")
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
