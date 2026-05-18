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
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")  # JSON ключа сервисного аккаунта
CALENDAR_ID = "85f813a348453bc70b98c82024ac2d7db492896a82798537ce2a4e7175a0feb3@group.calendar.google.com"

GROUP_ID = -1003680698112
STRATBOOK_TOPIC_ID = 1542
SCRIMS_TOPIC_ID = 15
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

# Файл для хранения уже обработанных событий
PROCESSED_EVENTS_FILE = "/tmp/processed_events.json"
processed_events = {}  # {event_id: {"notified_day": bool, "notified_hour_half": bool, "notified_hour": bool}}

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


def get_calendar_service():
    """Создаёт сервис Google Calendar"""
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
    """Получает события из календаря на ближайшие 7 дней"""
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


async def check_calendar_loop():
    """Проверяет календарь каждые 10 минут"""
    while True:
        try:
            events = await fetch_calendar_events()
            now = datetime.now(timezone.utc)

            for event in events:
                event_id = event['id']
                summary = event.get('summary', 'Прак')
                start = event['start'].get('dateTime', event['start'].get('date'))

                if 'T' not in start:
                    continue

                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))

                if event_id not in processed_events:
                    processed_events[event_id] = {
                        "notified_new": False,
                        "notified_day": False,
                        "notified_hour_half": False,
                        "notified_hour": False
                    }

                state = processed_events[event_id]
                time_until = event_time - now
                local_time = event_time.astimezone()
                date_str = local_time.strftime("%d.%m.%Y")
                time_str = local_time.strftime("%H:%M")

                # Уведомление о новом праке (не удаляется)
                if not state["notified_new"]:
                    await bot.send_message(
                        GROUP_ID,
                        f"🎮 <b>НОВЫЙ ПРАК ИЗ КАЛЕНДАРЯ!</b>\n\n"
                        f"🗺 {summary}\n"
                        f"📅 {date_str} в {time_str}\n\n"
                        f"{PLAYERS}",
                        parse_mode="HTML",
                        message_thread_id=SCRIMS_TOPIC_ID
                    )
                    state["notified_new"] = True
                    save_processed()

                # За сутки (удалится через 24 часа)
                if not state["notified_day"] and timedelta(hours=23, minutes=50) < time_until <= timedelta(hours=24, minutes=10):
                    sent = await bot.send_message(
                        GROUP_ID,
                        f"🔔 <b>Напоминание! Прак завтра!</b>\n\n"
                        f"🗺 {summary}\n"
                        f"📅 {date_str} в {time_str}\n\n"
                        f"{PLAYERS}",
                        parse_mode="HTML",
                        message_thread_id=SCRIMS_TOPIC_ID
                    )
                    state["notified_day"] = True
                    save_processed()
                    asyncio.create_task(auto_delete(sent, 82800))

                # За час (удалится через 24 часа)
                if not state["notified_hour"] and timedelta(minutes=50) < time_until <= timedelta(hours=1, minutes=10):
                    sent = await bot.send_message(
                        GROUP_ID,
                        f"⏰ <b>Через час прак!</b>\n\n"
                        f"🗺 {summary}\n"
                        f"🕐 {time_str}\n\n"
                        f"{PLAYERS}",
                        parse_mode="HTML",
                        message_thread_id=SCRIMS_TOPIC_ID
                    )
                    state["notified_hour"] = True
                    save_processed()
                    asyncio.create_task(auto_delete(sent, 3600))

        except Exception as e:
            logging.error(f"Ошибка в check_calendar_loop: {e}")

        await asyncio.sleep(600)  # Проверка каждые 10 минут


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
    asyncio.create_task(check_calendar_loop())
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
        "🔔 /notify текст — отправить уведомление в STRATBOOK\n"
        "📌 /post — обновить закреплённое сообщение\n"
        "🆔 /id — узнать ID чата\n"
        "📖 /maps — меню карт",
        parse_mode="HTML"
    )


@dp.message_handler(commands=["upcoming"])
async def cmd_upcoming(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN_ID:
        return
    
    events = await fetch_calendar_events()
    if not events:
        await message.reply("📭 Праков в ближайшую неделю нет.")
        return

    text = "📅 <b>Ближайшие праки:</b>\n\n"
    for event in events[:10]:
        summary = event.get('summary', 'Прак')
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = event_time.astimezone()
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
    await call.message.edit_text(
        f"{label}\n\n🗺️ <b>Выбери карту:</b>",
        parse_mode="HTML",
        reply_markup=map_menu(section)
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("map:"))
async def map_chosen(call: types.CallbackQuery):
    _, section, map_id = call.data.split(":")

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

    await asyncio.sleep(5)
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
