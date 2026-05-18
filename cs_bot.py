import os
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================
# 🔧 НАСТРОЙКИ
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN")

GROUP_ID = -1003680698112
STRATBOOK_TOPIC_ID = 1542
SCRIMS_TOPIC_ID = 15
ADMIN_ID = 557066322
PINNED_MESSAGE_ID = 1707

PLAYERS = "@Rogachev_E @gladnessorrow @YakobsMonarch0_0 @FREEDOM5O"

INSTA_LINK = "https://docs.google.com/spreadsheets/d/1C4ZIfJKl4WvnCkH3eVB7v0lw7N94pyYZwj98VPhOcTk/edit?gid=1511020141#gid=1511020141"

STRAT_BOOKS = {
    "mirage":  "https://docs.google.com/document/d/1KfaADUAV4jy2QqHyjUlAJ5rBd9SQuFokAmQN86DDHEE/edit?tab=t.5w09v52hr780",
    "dust2":   "https://docs.google.com/document/d/1o_B5xguuRmTO1lw2b9NB7sphzWZFvlEiQaU2VKlbzDU/edit?tab=t.5w09v52hr780",
    "ancient": None,
}

NADES = {
    "mirage":  "https://youtu.be/WCX87Hl5auE",
    "dust2":   "https://youtu.be/T6WxmGJYC9w",
    "ancient": "https://www.youtube.com/watch?v=ETTmq_xxPLk",
}

MAP_KEYWORDS = {
    "mirage": "mirage", "мираж": "mirage",
    "dust2": "dust2", "dust 2": "dust2", "de dust 2": "dust2",
    "даст": "dust2", "даст2": "dust2", "даст 2": "dust2",
    "ancient": "ancient",
}

scrims = []  # Список праков

# ============================
# 🤖 БОТ
# ============================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


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
    try:
        await bot.edit_message_text(
            "📚 <b>EGOIST STRATBOOK</b>\n\n"
            "Выбери раздел и получи нужную информацию:",
            chat_id=GROUP_ID,
            message_id=PINNED_MESSAGE_ID,
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception as e:
        logging.error(f"Ошибка при редактировании сообщения: {e}")


async def scrim_reminder(scrim_text: str, scrim_time: datetime):
    """Отправляет напоминание за день и за час до прака"""
    now = datetime.now()

    # Напоминание за день
    day_before = scrim_time - timedelta(days=1)
    seconds_to_day = (day_before - now).total_seconds()
    if seconds_to_day > 0:
        await asyncio.sleep(seconds_to_day)
        await bot.send_message(
            GROUP_ID,
            f"🔔 <b>Напоминание! Прак завтра!</b>\n\n"
            f"🗺 {scrim_text}\n\n"
            f"{PLAYERS}",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID
        )

    # Напоминание за час
    hour_before = scrim_time - timedelta(hours=1)
    seconds_to_hour = (hour_before - datetime.now()).total_seconds()
    if seconds_to_hour > 0:
        await asyncio.sleep(seconds_to_hour)
        await bot.send_message(
            GROUP_ID,
            f"⏰ <b>Через час прак!</b>\n\n"
            f"🗺 {scrim_text}\n\n"
            f"{PLAYERS}",
            parse_mode="HTML",
            message_thread_id=SCRIMS_TOPIC_ID
        )


# ============================
# 📋 КОМАНДЫ
# ============================

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    if message.chat.type != "private":
        await message.delete()
        return
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔️ У тебя нет доступа.")
        return
    await message.reply(
        "📋 <b>Список команд:</b>\n\n"
        "🗺 <b>Праки:</b>\n"
        "/scrim Mirage 23.05.2026 20:00 — добавить прак\n"
        "/clearscrim — очистить список праков\n\n"
        "🔔 <b>Уведомления:</b>\n"
        "/notify текст — отправить уведомление в STRATBOOK\n\n"
        "📌 <b>Прочее:</b>\n"
        "/post — обновить закреплённое сообщение в STRATBOOK\n"
        "/id — узнать ID чата или топика\n"
        "/help — список команд",
        parse_mode="HTML"
    )


@dp.message_handler(commands=["scrim"])
async def cmd_scrim(message: types.Message):
    if message.chat.type != "private":
        await message.delete()
        return
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔️ У тебя нет доступа к этой команде.")
        return

    args = message.text.replace("/scrim", "").strip()
    if not args:
        await message.reply("✏️ Формат: /scrim Mirage 23.05.2026 20:00")
        return

    # Парсим дату и время
    try:
        parts = args.split()
        map_name = parts[0]
        date_str = parts[1]
        time_str = parts[2]
        scrim_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    except Exception:
        await message.reply("❌ Неверный формат! Используй: /scrim Mirage 23.05.2026 20:00")
        return

    scrim_text = f"{map_name} — {date_str} в {time_str}"
    scrims.append(scrim_text)

    scrim_list = "\n".join([f"🗺 {s}" for s in scrims])
    text = (
        f"🎮 <b>РАСПИСАНИЕ ПРАКОВ</b>\n\n"
        f"{scrim_list}\n\n"
        f"{PLAYERS}"
    )
    await bot.send_message(
        GROUP_ID,
        text,
        parse_mode="HTML",
        message_thread_id=SCRIMS_TOPIC_ID
    )
    await message.reply(f"✅ Прак добавлен! Напомню за день и за час.")

    # Запускаем напоминания
    asyncio.create_task(scrim_reminder(scrim_text, scrim_time))


@dp.message_handler(commands=["clearscrim"])
async def cmd_clearscrim(message: types.Message):
    if message.chat.type != "private":
        await message.delete()
        return
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔️ У тебя нет доступа к этой команде.")
        return
    scrims.clear()
    await message.reply("✅ Список праков очищен!")


@dp.message_handler(commands=["post"])
async def cmd_post(message: types.Message):
    if message.chat.type != "private":
        await message.delete()
        return
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔️ У тебя нет доступа к этой команде.")
        return
    sent = await bot.send_message(
        GROUP_ID,
        "📚 <b>EGOIST STRATBOOK</b>\n\n"
        "Выбери раздел и получи нужную информацию:",
        parse_mode="HTML",
        message_thread_id=STRATBOOK_TOPIC_ID,
        reply_markup=main_menu()
    )
    await message.reply(f"✅ Сообщение отправлено! ID: {sent.message_id}")


@dp.message_handler(commands=["notify"])
async def cmd_notify(message: types.Message):
    if message.chat.type != "private":
        await message.delete()
        return
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔️ У тебя нет доступа к этой команде.")
        return
    text = message.text.replace("/notify", "").strip()
    if not text:
        await message.reply("✏️ Укажи текст: /notify Добавлен stratbook на Ancient")
        return
    await bot.send_message(
        GROUP_ID,
        f"🔔 <b>Обновление от 5 LVL FACEIT!</b>\n\n{text}",
        parse_mode="HTML",
        message_thread_id=STRATBOOK_TOPIC_ID
    )
    await message.reply("✅ Уведомление отправлено!")


@dp.message_handler(commands=["id"])
async def cmd_id(message: types.Message):
    sent = await message.reply(
        f"🆔 <b>ID чата:</b> <code>{message.chat.id}</code>\n"
        f"🆔 <b>ID топика:</b> <code>{message.message_thread_id}</code>",
        parse_mode="HTML"
    )
    asyncio.create_task(auto_delete(sent))


@dp.message_handler(commands=["maps"])
async def cmd_maps(message: types.Message):
    sent = await message.reply(
        "🗺️ <b>Выбери раздел:</b>",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
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
            kb.add(InlineKeyboardButton("📋 Открыть Stratbook", url=link))
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:strat"))
            await call.message.edit_text(
                f"📋 <b>Stratbook — {map_id.upper()}</b>",
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:strat"))
            await call.message.edit_text(
                f"😔 Stratbook для <b>{map_id.upper()}</b> пока не добавлен",
                parse_mode="HTML",
                reply_markup=kb
            )

    elif section == "nades":
        link = NADES.get(map_id)
        if link:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("💣 Смотреть Nades", url=link))
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:nades"))
            await call.message.edit_text(
                f"💣 <b>Nades — {map_id.upper()}</b>",
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="section:nades"))
            await call.message.edit_text(
                f"😔 Nades для <b>{map_id.upper()}</b> пока не добавлены",
                parse_mode="HTML",
                reply_markup=kb
            )

    await call.answer()

    # Автовозврат через 5 секунд
    await asyncio.sleep(5)
    try:
        await call.message.edit_text(
            "📚 <b>EGOIST STRATBOOK</b>\n\n"
            "Выбери раздел и получи нужную информацию:",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception:
        pass


@dp.callback_query_handler(lambda c: c.data == "back:main")
async def back_to_main(call: types.CallbackQuery):
    await call.message.edit_text(
        "📚 <b>EGOIST STRATBOOK</b>\n\n"
        "Выбери раздел и получи нужную информацию:",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await call.answer()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
