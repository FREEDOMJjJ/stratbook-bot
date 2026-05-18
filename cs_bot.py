import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# ============================
# 🔧 НАСТРОЙКИ
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Получить у @BotFather

# Ключевые слова -> ссылки (можно добавлять любые)
MIRAGE_LINK = "https://docs.google.com/document/d/1KfaADUAV4jy2QqHyjUlAJ5rBd9SQuFokAmQN86DDHEE/edit?tab=t.5w09v52hr780"

DUST2_LINK = "https://docs.google.com/document/d/1o_B5xguuRmTO1lw2b9NB7sphzWZFvlEiQaU2VKlbzDU/edit?tab=t.5w09v52hr780"

MAP_LINKS = {
    "mirage":    MIRAGE_LINK,
    "мираж":     MIRAGE_LINK,
    "даст2":     DUST2_LINK,
    "даст 2":    DUST2_LINK,
    "de dust 2": DUST2_LINK,
    "даст":      DUST2_LINK,
    "dust2":     DUST2_LINK,
    "dust 2":    DUST2_LINK,
    # Остальные карты — добавляй по аналогии:
    # "inferno": "https://...",
}

# ============================
# 🤖 БОТ
# ============================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(F.text)
async def handle_message(message: Message):
    text = message.text.lower().strip()

    # Проверяем каждое ключевое слово
    for keyword, link in MAP_LINKS.items():
        if keyword in text:
            await message.reply(
                f"📍 <b>{keyword.upper()}</b>\n"
                f"🔗 {link}",
                parse_mode="HTML"
            )
            return  # Отвечаем только на первое совпадение


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
