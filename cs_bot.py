import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================
# 🔧 НАСТРОЙКИ
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN")

GROUP_ID = -1003680698112  # ID группы команды
STRATBOOK_TOPIC_ID = 1542  # ID топика STRATBOOK
ADMIN_ID = 557066322  # Твой Telegram ID

INSTA_LINK = "https://docs.google.com/spreadsheets/d/1C4ZIfJKl4WvnCkH3eVB7v0lw7N94pyYZwj98VPhOcTk/edit?gid=1511020141#gid=1511020141"

STRAT_BOOKS = {
    "mirage": "https://docs.google.com/document/d/1KfaADUAV4jy2QqHyjUlAJ5rBd9SQuFokAmQN86DDHEE/edit?tab=t.5w09v52hr780",
    "dust2":  "https://docs.google.com/document/d/1o_B5xguuRmTO1lw2b9NB7sphzWZFvlEiQaU2VKlbzDU/edit?tab=t.5w09v52hr780",
    "ancient": None,  # добавишь позже
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

# ============================
# 🤖 БОТ
# ============================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


async def auto_delete(message: types.Message, delay: int = 60):
    """Удаляет сообщение бота через delay секунд"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


def main_menu():
    """Главное меню — выбор раздела"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📋 Stratbook", callback_data="section:strat"),
        InlineKeyboardButton("💣 Nades", callback_data="section:nades"),
    )
    return kb


def map_menu(section: str):
    """Меню выбора карты"""
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


@dp.message_handler(commands=["post"])
async def cmd_post(message: types.Message):
    if message.chat.type != "private":
        await message.delete()
        return

    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔️ У тебя нет доступа к этой команде.")
        return

    await bot.send_message(
        GROUP_ID,
        "📚 <b>EGOIST STRATBOOK</b>\n\n"
        "Выбери раздел и получи нужную информацию:",
        parse_mode="HTML",
        message_thread_id=STRATBOOK_TOPIC_ID,
        reply_markup=main_menu()
    )
    await message.reply("✅ Сообщение отправлено в STRATBOOK — закрепи его!")


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
    await message.reply("✅ Уведомление отправлено в группу!")


@dp.message_handler(commands=["id"])
async def cmd_id(message: types.Message):
    sent = await message.reply(
        f"🆔 <b>ID этого чата:</b> <code>{message.chat.id}</code>",
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
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"section:strat"))
            await call.message.edit_text(
                f"📋 <b>Stratbook — {map_id.upper()}</b>",
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"section:strat"))
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
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"section:nades"))
            await call.message.edit_text(
                f"💣 <b>Nades — {map_id.upper()}</b>",
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"section:nades"))
            await call.message.edit_text(
                f"😔 Nades для <b>{map_id.upper()}</b> пока не добавлены",
                parse_mode="HTML",
                reply_markup=kb
            )

    await call.answer()

    # Автовозврат в главное меню через 30 секунд
    await asyncio.sleep(30)
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
    executor.start_polling(dp, skip_updates=True)
