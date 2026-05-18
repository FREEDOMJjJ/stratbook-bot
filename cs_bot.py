import os
import logging
from aiogram import Bot, Dispatcher, executor, types

# ============================
# 🔧 НАСТРОЙКИ
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN")

MIRAGE_LINK = "https://docs.google.com/document/d/1KfaADUAV4jy2QqHyjUlAJ5rBd9SQuFokAmQN86DDHEE/edit?tab=t.5w09v52hr780"
DUST2_LINK = "https://docs.google.com/document/d/1o_B5xguuRmTO1lw2b9NB7sphzWZFvlEiQaU2VKlbzDU/edit?tab=t.5w09v52hr780"

MIRAGE_NADES = "https://youtu.be/WCX87Hl5auE"
DUST2_NADES = "https://youtu.be/T6WxmGJYC9w"
ANCIENT_NADES = "https://www.youtube.com/watch?v=ETTmq_xxPLk"

MAP_LINKS = {
    "mirage":    MIRAGE_LINK,
    "мираж":     MIRAGE_LINK,
    "даст2":     DUST2_LINK,
    "даст 2":    DUST2_LINK,
    "de dust 2": DUST2_LINK,
    "даст":      DUST2_LINK,
    "dust2":     DUST2_LINK,
    "dust 2":    DUST2_LINK,
}

# ============================
# 🤖 БОТ
# ============================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=["maps"])
async def cmd_maps(message: types.Message):
    await message.reply(
        "🗺️ <b>Доступные карты:</b>\n\n"
        "• <b>Mirage</b> — напиши <code>mirage</code> или <code>мираж</code>\n"
        "  🎯 Utility: напиши <code>mirage utility</code>\n\n"
        "• <b>Dust 2</b> — напиши <code>dust2</code> или <code>даст</code>\n"
        "  🎯 Utility: напиши <code>dust2 utility</code>\n\n"
        "• <b>Ancient</b>\n"
        "  🎯 Utility: напиши <code>ancient utility</code>",
        parse_mode="HTML"
    )


@dp.message_handler()
async def handle_message(message: types.Message):
    text = message.text.lower().strip()

    # Utility команды
    if "mirage utility" in text or "мираж utility" in text or "мираж утил" in text or "mirage утил" in text:
        await message.reply(
            "🎯 <b>MIRAGE — Utility</b>\n"
            f"📹 {MIRAGE_NADES}",
            parse_mode="HTML"
        )
        return

    if "dust2 utility" in text or "dust 2 utility" in text or "даст utility" in text or "даст утил" in text:
        await message.reply(
            "🎯 <b>DUST 2 — Utility</b>\n"
            f"📹 {DUST2_NADES}",
            parse_mode="HTML"
        )
        return

    if "ancient utility" in text or "ancient утил" in text:
        await message.reply(
            "🎯 <b>ANCIENT — Utility</b>\n"
            f"📹 {ANCIENT_NADES}",
            parse_mode="HTML"
        )
        return

    # Страт буки по картам
    for keyword, link in MAP_LINKS.items():
        if keyword in text:
            await message.reply(
                f"📍 <b>{keyword.upper()}</b>\n🔗 {link}",
                parse_mode="HTML"
            )
            return


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
