import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ============================
# 🔧 НАСТРОЙКИ
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
CALENDAR_ID = "85f813a348453bc70b98c82024ac2d7db492896a82798537ce2a4e7175a0feb3@group.calendar.google.com"

GROUP_ID = -1003680698112
STRATBOOK_TOPIC_ID = 1542
SCRIMS_TOPIC_ID = 15
CHAT_TOPIC_ID = 13  # Раздел ЧАТ для цитат дня
ADMIN_ID = 557066322
PINNED_MESSAGE_ID = 1707

PLAYERS = "@Rogachev_E @gladnessorrow @YakobsMonarch0_0 @FREEDOM5O"
INSTA_LINK = "https://docs.google.com/spreadsheets/d/1C4ZIfJKl4WvnCkH3eVB7v0lw7N94pyYZwj98VPhOcTk/edit?gid=1511020141#gid=1511020141"

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

PROCESSED_EVENTS_FILE = "/tmp/processed_events.json"
LOGS_FILE = "/tmp/bot_logs.json"
LAST_QUOTE_DATE_FILE = "/tmp/last_quote_date.txt"
USED_QUOTES_FILE = "/tmp/used_quotes.json"
processed_events = {}
action_logs = []
used_quotes = []  # Индексы использованных цитат

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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


def load_processed():
    global processed_events
    if os.path.exists(PROCESSED_EVENTS_FILE):
        try:
            with open(PROCESSED_EVENTS_FILE, 'r') as f:
                processed_events = json.load(f)
        except:
            processed_events = {}


def save_processed():
    with open(PROCESSED_EVENTS_FILE, 'w') as f:
        json.dump(processed_events, f)


def load_logs():
    global action_logs
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, 'r') as f:
                action_logs = json.load(f)
        except:
            action_logs = []


def save_logs():
    with open(LOGS_FILE, 'w') as f:
        json.dump(action_logs[-100:], f, ensure_ascii=False)


def log_action(user, action: str):
    moscow_tz = timezone(timedelta(hours=3))
    timestamp = datetime.now(moscow_tz).strftime("%d.%m.%Y %H:%M")
    username = user.username or user.full_name or str(user.id)
    action_logs.append({
        "time": timestamp,
        "user": f"@{username}" if user.username else username,
        "action": action
    })
    save_logs()


def load_used_quotes():
    global used_quotes
    if os.path.exists(USED_QUOTES_FILE):
        try:
            with open(USED_QUOTES_FILE, 'r') as f:
                used_quotes = json.load(f)
        except:
            used_quotes = []


def save_used_quotes():
    with open(USED_QUOTES_FILE, 'w') as f:
        json.dump(used_quotes, f)


def get_unused_quote():
    """Возвращает (quote, author, index) из неиспользованных цитат"""
    import random
    available = [i for i in range(len(QUOTES)) if i not in used_quotes]
    
    # Если все цитаты использованы — сбрасываем список
    if not available:
        used_quotes.clear()
        available = list(range(len(QUOTES)))
    
    idx = random.choice(available)
    used_quotes.append(idx)
    save_used_quotes()
    quote, author = QUOTES[idx]
    return quote, author


def get_calendar_service():
    try:
        creds_info = json.loads(GOOGLE_CREDS_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        logging.error(f"Ошибка создания сервиса календаря: {e}")
        return None


async def fetch_calendar_events():
    service = get_calendar_service()
    if not service:
        return []

    now = datetime.now(timezone.utc).isoformat()
    week_later = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now,
            timeMax=week_later,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logging.error(f"Ошибка получения событий: {e}")
        return []


async def daily_quote_loop():
    """Отправляет цитату дня в 10:00 по МСК каждый день"""
    import random
    moscow_tz = timezone(timedelta(hours=3))
    
    while True:
        try:
            now = datetime.now(moscow_tz)
            
            # Проверяем была ли уже сегодня цитата
            today_str = now.strftime("%Y-%m-%d")
            last_date = ""
            if os.path.exists(LAST_QUOTE_DATE_FILE):
                with open(LAST_QUOTE_DATE_FILE, 'r') as f:
                    last_date = f.read().strip()
            
            # Если уже 10:00 или позже и сегодня ещё не отправляли
            if now.hour >= 10 and last_date != today_str:
                quote, author = get_unused_quote()
                await bot.send_message(
                    GROUP_ID,
                    f"☀️ <b>Доброе утро, ЭГОИСТЫ!</b>\n\n"
                    f"💬 <i>«{quote}»</i>\n"
                    f"— <b>{author}</b>",
                    parse_mode="HTML",
                    message_thread_id=CHAT_TOPIC_ID
                )
                with open(LAST_QUOTE_DATE_FILE, 'w') as f:
                    f.write(today_str)
        except Exception as e:
            logging.error(f"Ошибка в daily_quote_loop: {e}")
        
        await asyncio.sleep(300)  # Проверяем каждые 5 минут


async def check_calendar_loop():
    is_first_run = True  # Флаг первого запуска после деплоя
    while True:
        try:
            events = await fetch_calendar_events()
            now = datetime.now(timezone.utc)
            moscow_tz = timezone(timedelta(hours=3))

            for event in events:
                event_id = event['id']
                summary = event.get('summary', 'Прак')
                start = event['start'].get('dateTime', event['start'].get('date'))

                if 'T' not in start:
                    continue

                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                local_time = event_time.astimezone(moscow_tz)
                date_str = local_time.strftime("%d.%m.%Y")
                time_str = local_time.strftime("%H:%M")
                time_until = event_time - now

                if event_id not in processed_events:
                    # При первом запуске после деплоя считаем все существующие праки уже обработанными
                    if is_first_run:
                        processed_events[event_id] = {
                            "notified_new": True,
                            "notified_day": time_until < timedelta(hours=24),
                            "notified_hour": time_until < timedelta(hours=1)
                        }
                        save_processed()
                        continue
                    else:
                        processed_events[event_id] = {
                            "notified_new": False,
                            "notified_day": time_until < timedelta(hours=24),
                            "notified_hour": time_until < timedelta(hours=1)
                        }

                state = processed_events[event_id]

                # Уведомление о новом праке (всегда, даже если он скоро)
                if not state["notified_new"]:
                    await bot.send_message(
                        GROUP_ID,
                        f"🎮 <b>НОВЫЙ ПРАК ИЗ КАЛЕНДАРЯ!</b>\n"
                        f"📅 <i>(синхронизируется с Google Calendar и Pracc.com)</i>\n\n"
                        f"🗺 {summary}\n"
                        f"📅 {date_str} в {time_str}\n\n"
                        f"{PLAYERS}",
                        parse_mode="HTML",
                        message_thread_id=SCRIMS_TOPIC_ID
                    )
                    state["notified_new"] = True
                    save_processed()

                # За сутки
                if not state["notified_day"] and timedelta(hours=23, minutes=50) < time_until <= timedelta(hours=24, minutes=10):
                    sent = await bot.send_message(
                        GROUP_ID,
                        f"🔔 <b>Напоминание! Прак завтра!</b>\n"
                        f"📅 <i>(из Google Calendar и Pracc.com)</i>\n\n"
                        f"🗺 {summary}\n"
                        f"📅 {date_str} в {time_str}\n\n"
                        f"{PLAYERS}",
                        parse_mode="HTML",
                        message_thread_id=SCRIMS_TOPIC_ID
                    )
                    state["notified_day"] = True
                    save_processed()
                    asyncio.create_task(auto_delete(sent, 82800))

                # За час
                if not state["notified_hour"] and timedelta(minutes=50) < time_until <= timedelta(hours=1, minutes=10):
                    sent = await bot.send_message(
                        GROUP_ID,
                        f"⏰ <b>Через час прак!</b>\n"
                        f"📅 <i>(из Google Calendar и Pracc.com)</i>\n\n"
                        f"🗺 {summary}\n"
                        f"🕐 {time_str}\n\n"
                        f"{PLAYERS}",
                        parse_mode="HTML",
                        message_thread_id=SCRIMS_TOPIC_ID
                    )
                    state["notified_hour"] = True
                    save_processed()
                    asyncio.create_task(auto_delete(sent, 3600))

            is_first_run = False  # После первого прохода флаг снимается

        except Exception as e:
            logging.error(f"Ошибка в check_calendar_loop: {e}")

        await asyncio.sleep(600)


async def auto_delete(message: types.Message, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📋 Stratbook", callback_data="section:strat"),
        InlineKeyboardButton("💣 Nades", callback_data="section:nades"),
    )
    return kb


def map_menu(section: str):
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


async def on_startup(dp):
    load_processed()
    load_logs()
    load_used_quotes()
    asyncio.create_task(check_calendar_loop())
    asyncio.create_task(daily_quote_loop())
    try:
        await bot.edit_message_text(
            "📚 <b>EGOIST STRATBOOK</b>\n\nВыбери раздел и получи нужную информацию:",
            chat_id=GROUP_ID,
            message_id=PINNED_MESSAGE_ID,
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception as e:
        logging.error(f"Ошибка: {e}")


@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    await message.reply(
        "📋 <b>Команды:</b>\n\n"
        "📅 /upcoming — ближайшие праки из календаря\n"
        "💬 /quote — отправить случайную цитату в чат\n"
        "📜 /logs — последние 20 действий в боте\n"
        "🔔 /notify текст — уведомление в STRATBOOK\n"
        "📌 /post — обновить закреплённое сообщение\n"
        "🔄 /restart — перезапустить бота\n"
        "🆔 /id — узнать ID чата\n"
        "📖 /maps — меню карт",
        parse_mode="HTML"
    )


@dp.message_handler(commands=["restart"])
async def cmd_restart(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    await message.reply("🔄 Перезапускаю бота... Через 5-10 секунд он будет онлайн.")
    log_action(message.from_user, "Перезапустил бота")
    await asyncio.sleep(1)
    os._exit(0)  # Railway автоматически перезапустит


@dp.message_handler(commands=["logs"])
async def cmd_logs(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    
    if not action_logs:
        await message.reply("📭 Пока нет записанных действий.")
        return
    
    last_logs = action_logs[-20:]
    text = "📜 <b>Последние действия:</b>\n\n"
    for log in reversed(last_logs):
        text += f"🕐 <code>{log['time']}</code>\n"
        text += f"👤 {log['user']}\n"
        text += f"➡️ {log['action']}\n\n"
    
    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["quote"])
async def cmd_quote(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    
    quote, author = get_unused_quote()
    await bot.send_message(
        GROUP_ID,
        f"💬 <i>«{quote}»</i>\n— <b>{author}</b>",
        parse_mode="HTML",
        message_thread_id=CHAT_TOPIC_ID
    )
    await message.reply("✅ Цитата отправлена!")


@dp.message_handler(commands=["upcoming"])
async def cmd_upcoming(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    
    events = await fetch_calendar_events()
    if not events:
        await message.reply("📭 Праков в ближайшую неделю нет.")
        return

    moscow_tz = timezone(timedelta(hours=3))
    text = "📅 <b>Ближайшие праки:</b>\n\n"
    for event in events[:10]:
        summary = event.get('summary', 'Прак')
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = event_time.astimezone(moscow_tz)
            date_str = local_time.strftime("%d.%m.%Y %H:%M")
            text += f"🗺 {summary} — {date_str}\n"

    await message.reply(text, parse_mode="HTML")


@dp.message_handler(commands=["post"])
async def cmd_post(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    await bot.send_message(
        GROUP_ID,
        "📚 <b>EGOIST STRATBOOK</b>\n\nВыбери раздел и получи нужную информацию:",
        parse_mode="HTML",
        message_thread_id=STRATBOOK_TOPIC_ID,
        reply_markup=main_menu()
    )
    await message.reply("✅ Отправлено!")


@dp.message_handler(commands=["notify"])
async def cmd_notify(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/notify", "").strip()
    if not text:
        return
    await bot.send_message(
        GROUP_ID,
        f"🔔 <b>Обновление от 5 LVL FACEIT!</b>\n\n{text}",
        parse_mode="HTML",
        message_thread_id=STRATBOOK_TOPIC_ID
    )
    await message.reply("✅ Отправлено!")


@dp.message_handler(commands=["id"])
async def cmd_id(message: types.Message):
    sent = await message.reply(
        f"🆔 ID чата: <code>{message.chat.id}</code>\n"
        f"🆔 ID топика: <code>{message.message_thread_id}</code>",
        parse_mode="HTML"
    )
    asyncio.create_task(auto_delete(sent))


@dp.message_handler(commands=["maps"])
async def cmd_maps(message: types.Message):
    sent = await message.reply("🗺️ <b>Выбери раздел:</b>", parse_mode="HTML", reply_markup=main_menu())
    asyncio.create_task(auto_delete(sent))


@dp.message_handler()
async def handle_message(message: types.Message):
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


@dp.callback_query_handler(lambda c: c.data.startswith("section:"))
async def section_chosen(call: types.CallbackQuery):
    section = call.data.split(":")[1]
    label = "📋 Stratbook" if section == "strat" else "💣 Nades"
    log_action(call.from_user, f"Открыл {label}")
    await call.message.edit_text(
        f"{label}\n\n🗺️ <b>Выбери карту:</b>",
        parse_mode="HTML",
        reply_markup=map_menu(section)
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("map:"))
async def map_chosen(call: types.CallbackQuery):
    _, section, map_id = call.data.split(":")
    section_name = "Stratbook" if section == "strat" else "Nades"
    log_action(call.from_user, f"Открыл {section_name} — {map_id.upper()}")

    if section == "strat":
        link = STRAT_BOOKS.get(map_id)
        if link:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("📋 Открыть", url=link))
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:strat"))
            await call.message.edit_text(f"📋 <b>Stratbook — {map_id.upper()}</b>", parse_mode="HTML", reply_markup=kb)
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:strat"))
            await call.message.edit_text(f"😔 Нет для {map_id.upper()}", parse_mode="HTML", reply_markup=kb)

    elif section == "nades":
        link = NADES.get(map_id)
        if link:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("💣 Смотреть", url=link))
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:nades"))
            await call.message.edit_text(f"💣 <b>Nades — {map_id.upper()}</b>", parse_mode="HTML", reply_markup=kb)
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:nades"))
            await call.message.edit_text(f"😔 Нет для {map_id.upper()}", parse_mode="HTML", reply_markup=kb)

    await call.answer()

    await asyncio.sleep(15)
    try:
        await call.message.edit_text(
            "📚 <b>EGOIST STRATBOOK</b>\n\nВыбери раздел и получи нужную информацию:",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except:
        pass


@dp.callback_query_handler(lambda c: c.data == "back:main")
async def back_to_main(call: types.CallbackQuery):
    await call.message.edit_text(
        "📚 <b>EGOIST STRATBOOK</b>\n\nВыбери раздел и получи нужную информацию:",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await call.answer()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
