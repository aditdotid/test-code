"""Pinterest Downloader Telegram Bot.

A Telegram bot to download Pinterest images and videos directly from Telegram chats.
Supports single pins, shortlinks (pin.it), boards, and search queries.
"""

import asyncio
import logging
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from telegram import InputMediaPhoto, InputMediaVideo, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Ensure current directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from pinterest_dl import PinterestDL
from pinterest_dl.domain.media import PinterestMedia

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger("PinterestBot")

# Environment configurations
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEFAULT_NUM = int(os.getenv("DEFAULT_NUM", "5"))
MAX_NUM = int(os.getenv("MAX_NUM", "10"))
COOKIES_PATH = os.getenv("COOKIES_PATH", "cookies.json")

# Regex to match Pinterest links
PINTEREST_URL_PATTERN = re.compile(
    r"https?://(?:[a-zA-Z0-9-]+\.)?(?:pinterest\.[a-z.]+|pin\.it)/[^\s]+",
    re.IGNORECASE,
)

# Telegram limits
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB


def get_scraper() -> "PinterestDL":
    """Create and configure ApiScraper instance with optional cookies."""
    scraper = PinterestDL.with_api(timeout=15, verbose=False)
    cookie_file = BASE_DIR / COOKIES_PATH
    if cookie_file.exists():
        try:
            scraper.with_cookies_path(cookie_file)
            logger.info("Loaded cookies from %s", cookie_file)
        except Exception as e:
            logger.warning("Failed to load cookies from %s: %s", cookie_file, e)
    return scraper


def _sync_download_url(url: str, output_dir: Path, num: int) -> List[PinterestMedia]:
    """Synchronous worker to download media from a Pinterest URL."""
    scraper = get_scraper()
    results = scraper.scrape_and_download(
        url=url,
        output_dir=output_dir,
        num=num,
        download_streams=True,
        skip_remux=False,
    )
    return results or []


def _sync_search_and_download(query: str, output_dir: Path, num: int) -> List[PinterestMedia]:
    """Synchronous worker to search and download media from Pinterest."""
    scraper = get_scraper()
    results = scraper.search_and_download(
        query=query,
        output_dir=output_dir,
        num=num,
        download_streams=True,
        skip_remux=False,
    )
    return results or []


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and instructions."""
    welcome_text = (
        "👋 *Halo! Selamat datang di Pinterest Downloader Bot.*\n\n"
        "Kirimkan tautan (link) Pinterest langsung ke obrolan ini untuk mengunduh gambar atau video kualitas tertinggi.\n\n"
        "📌 *Cara Penggunaan:*\n"
        "• *Unduh Langsung*: Cukup tempel link pin Pinterest (misal: `https://pin.it/...` atau `https://pinterest.com/pin/...`).\n"
        "• *Cari Pin*: Ketik `/search <kata kunci> [jumlah]`\n"
        "  Contoh: `/search aesthetic wallpaper 5`\n"
        "• *Unduh Board*: Ketik `/scrape <link_board> [jumlah]`\n"
        "  Contoh: `/scrape https://www.pinterest.com/username/board-name/ 5`\n"
        "• *Bantuan*: Ketik `/help`\n\n"
        "💡 *Tips:* Bot otomatis mendeteksi apakah pin berupa gambar atau video MP4."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = (
        "ℹ️ *Panduan Bantuan Pinterest Downloader Bot*\n\n"
        "1. *Unduh Single Pin (Foto / Video)*:\n"
        "   Kirim tautan pin Pinterest secara langsung tanpa perintah apa pun.\n\n"
        "2. *Pencarian Pin*:\n"
        "   Gunakan perintah `/search` atau `/cari`.\n"
        "   Contoh: `/search minimalist interior 4`\n\n"
        "3. *Unduh Board / Koleksi*:\n"
        "   Gunakan perintah `/scrape <link_board> [jumlah]`.\n"
        "   Contoh: `/scrape https://pinterest.com/user/aesthetic/ 5`\n\n"
        "⚠️ *Catatan:*\n"
        f"• Batas maksimal per unduhan: {MAX_NUM} item.\n"
        "• Batas ukuran file Telegram bot adalah 50MB."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def send_media_items(update: Update, media_list: List[PinterestMedia]) -> None:
    """Send downloaded media back to the user, either as single media or album."""
    # Filter items that have a valid local path
    valid_items = [
        item for item in media_list if item.local_path and Path(item.local_path).exists()
    ]

    if not valid_items:
        await update.message.reply_text("❌ Gagal mengunduh media. File tidak ditemukan.")
        return

    # If only 1 media item
    if len(valid_items) == 1:
        item = valid_items[0]
        file_path = Path(item.local_path)
        file_size = file_path.stat().st_size

        if file_size > MAX_TELEGRAM_FILE_SIZE:
            alt_text = f"\nJudul: {item.alt}" if item.alt else ""
            await update.message.reply_text(
                f"⚠️ Ukuran file ({file_size / (1024*1024):.1f} MB) melebihi batas upload Telegram Bot (50 MB).\n"
                f"{alt_text}\n"
                f"🔗 Link Sumber: {item.origin or item.src}"
            )
            return

        caption = f"📌 {item.alt}\n" if item.alt else ""
        if item.origin:
            caption += f"🔗 [Sumber Pin]({item.origin})"
        caption = caption.strip()

        ext = file_path.suffix.lower()
        try:
            if ext in [".mp4", ".mov", ".ts"]:
                with open(file_path, "rb") as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=caption or None,
                        parse_mode=ParseMode.MARKDOWN if caption else None,
                        supports_streaming=True,
                    )
            elif ext in [".jpg", ".jpeg", ".png", ".webp"] and file_size <= MAX_PHOTO_SIZE:
                with open(file_path, "rb") as photo_file:
                    await update.message.reply_photo(
                        photo=photo_file,
                        caption=caption or None,
                        parse_mode=ParseMode.MARKDOWN if caption else None,
                    )
            else:
                with open(file_path, "rb") as doc_file:
                    await update.message.reply_document(
                        document=doc_file,
                        caption=caption or None,
                        parse_mode=ParseMode.MARKDOWN if caption else None,
                    )
        except Exception as e:
            logger.error("Error sending single media: %s", e)
            await update.message.reply_text(f"❌ Gagal mengirim file: {e}")
        return

    # If multiple media items: send as album / media group (max 10 per group)
    # Chunk into groups of 10
    chunks = [valid_items[i : i + 10] for i in range(0, len(valid_items), 10)]

    for chunk in chunks:
        open_files = []
        media_group = []
        try:
            for idx, item in enumerate(chunk):
                file_path = Path(item.local_path)
                file_size = file_path.stat().st_size
                if file_size > MAX_TELEGRAM_FILE_SIZE:
                    continue

                f = open(file_path, "rb")
                open_files.append(f)
                ext = file_path.suffix.lower()

                caption = None
                if idx == 0:
                    caption = f"📦 Berhasil mengunduh {len(valid_items)} item dari Pinterest."

                if ext in [".mp4", ".mov", ".ts"]:
                    media_group.append(
                        InputMediaVideo(
                            media=f,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN if caption else None,
                        )
                    )
                else:
                    media_group.append(
                        InputMediaPhoto(
                            media=f,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN if caption else None,
                        )
                    )

            if media_group:
                await update.message.reply_media_group(media=media_group)
        except Exception as e:
            logger.error("Error sending media group: %s", e)
            await update.message.reply_text(f"❌ Gagal mengirim sebagian media: {e}")
        finally:
            for f in open_files:
                try:
                    f.close()
                except Exception:
                    pass


async def handle_pinterest_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages containing Pinterest URLs."""
    text = update.message.text
    match = PINTEREST_URL_PATTERN.search(text)
    if not match:
        return

    url = match.group(0)
    # Check if URL is a single pin or board
    is_single_pin = "/pin/" in url or "pin.it" in url

    status_msg = await update.message.reply_text(
        "⏳ Sedang memproses dan mengunduh media dari Pinterest..."
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="pin_dl_"))
    try:
        num_to_download = 1 if is_single_pin else DEFAULT_NUM
        # Run synchronous scraper in background thread
        media_list = await asyncio.to_thread(
            _sync_download_url,
            url,
            temp_dir,
            num_to_download,
        )

        if not media_list:
            await status_msg.edit_text(
                "❌ Gagal mengunduh media. Pastikan tautan Pinterest valid dan dapat diakses publik."
            )
            return

        await status_msg.delete()
        await send_media_items(update, media_list)

    except Exception as e:
        logger.error("Error handling URL %s: %s", url, e, exc_info=True)
        await status_msg.edit_text(f"❌ Terjadi kesalahan: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scrape <url> [num] command."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Format penggunaan:\n`/scrape <link_pinterest> [jumlah]`\n\n"
            "Contoh:\n`/scrape https://pinterest.com/user/board/ 5`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    url = context.args[0]
    num = DEFAULT_NUM
    if len(context.args) > 1:
        try:
            num = int(context.args[1])
            num = max(1, min(num, MAX_NUM))
        except ValueError:
            num = DEFAULT_NUM

    status_msg = await update.message.reply_text(
        f"⏳ Sedang mengunduh {num} item dari `{url}`...",
        parse_mode=ParseMode.MARKDOWN,
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="pin_scrape_"))
    try:
        media_list = await asyncio.to_thread(
            _sync_download_url,
            url,
            temp_dir,
            num,
        )

        if not media_list:
            await status_msg.edit_text("❌ Gagal mengunduh media dari tautan tersebut.")
            return

        await status_msg.delete()
        await send_media_items(update, media_list)

    except Exception as e:
        logger.error("Error in scrape command: %s", e, exc_info=True)
        await status_msg.edit_text(f"❌ Terjadi kesalahan saat mengunduh: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search <query> [num] command."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Format penggunaan:\n`/search <kata kunci> [jumlah]`\n\n"
            "Contoh:\n`/search cyber punk city 5`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Check if last argument is a number
    num = DEFAULT_NUM
    query_parts = list(context.args)
    if query_parts[-1].isdigit():
        num = int(query_parts.pop())
        num = max(1, min(num, MAX_NUM))

    query = " ".join(query_parts).strip()
    if not query:
        await update.message.reply_text("⚠️ Silakan masukkan kata kunci pencarian.")
        return

    status_msg = await update.message.reply_text(
        f"🔍 Mencari `{query}` di Pinterest ({num} item)...",
        parse_mode=ParseMode.MARKDOWN,
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="pin_search_"))
    try:
        media_list = await asyncio.to_thread(
            _sync_search_and_download,
            query,
            temp_dir,
            num,
        )

        if not media_list:
            await status_msg.edit_text(f"❌ Tidak ditemukan pin untuk kata kunci: `{query}`")
            return

        await status_msg.delete()
        await send_media_items(update, media_list)

    except Exception as e:
        logger.error("Error searching %s: %s", query, e, exc_info=True)
        await status_msg.edit_text(f"❌ Terjadi kesalahan saat pencarian: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    """Start the Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        logger.error(
            "TELEGRAM_BOT_TOKEN belum disetel! Harap setel token di file .env atau environment variable."
        )
        print(
            "\n[ERROR] TELEGRAM_BOT_TOKEN belum diatur!\n"
            "Silakan salin .env.example menjadi .env lalu isi token bot dari @BotFather:\n"
            "  cp .env.example .env\n"
            "  nano .env\n"
        )
        sys.exit(1)

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler(["start"], start_command))
    application.add_handler(CommandHandler(["help"], help_command))
    application.add_handler(CommandHandler(["search", "cari"], search_command))
    application.add_handler(CommandHandler(["scrape", "download"], scrape_command))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_pinterest_url)
    )

    logger.info("Bot Pinterest Downloader berhasil dijalankan dan siap menerima pesan.")
    print("Bot Pinterest Downloader sedang berjalan... Tekan Ctrl+C untuk berhenti.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
