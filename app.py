import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import re
import json
import os
from dotenv import load_dotenv
from datetime import date

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set higher logging level for libraries to avoid excessive noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

load_dotenv()

OLLAMA_URL = os.getenv('OLLAMA_URL')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL')
BOT_TOKEN = os.getenv('BOT_TOKEN')
APP_SCRIPT_URL = os.getenv('APP_SCRIPT_URL')
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID')) 

# --- Configuration Validation ---
REQUIRED_ENV_VARS = ['OLLAMA_URL', 'OLLAMA_MODEL', 'BOT_TOKEN', 'APP_SCRIPT_URL', 'AUTHORIZED_USER_ID']
missing_vars = [var for var in REQUIRED_ENV_VARS if not globals().get(var)]

if missing_vars:
    logger.critical(f"Missing required environment variables: {', '.join(missing_vars)}. Please check your .env file.")
    exit(1) # Exit if critical configuration is missing

# --- Constants for Prompt ---
PAYMENT_METHODS = "[BCA, Jago, ShopeePay, Gopay, Cash]"
CATEGORIES = "[Makanan, Bahan Makanan, Transportasi, Belanja Harian, Belanja Online, Tagihan, Hiburan, Buah, Kesehatan, Pemasukan]"
DEFAULT_PAYMENT_METHOD = "Cash"

def build_prompt(user_input):
     return f"""
Kamu adalah seorang pengurai transaksi keuangan pribadi. Berdasarkan input dari pengguna yang menjelaskan suatu transaksi (pengeluaran atau pemasukan), ekstrak dan kembalikan hasilnya dalam format JSON saja, dengan kolom berikut:

- transaction_type: "income" jika merupakan pemasukan atau ambil uang dari atm, "expense" jika merupakan pengeluaran. Jika tidak disebutkan, anggap sebagai "expense".
- amount: jumlah uang dalam Rupiah (bilangan bulat) tanpa tanda mata uang
- description: deskripsi singkat transaksi
- payment_method: salah satu dari {PAYMENT_METHODS}, jika tidak disebutkan gunakan {DEFAULT_PAYMENT_METHOD}
- category: salah satu dari {CATEGORIES}, jika transaction_type nya "income", gunakan "Pemasukan"


Contoh:

Input: "Ambil uang dari atm 500000"

Hanya balas dalam format JSON:
{{
  "transaction_type": "income",
  "amount": 500000,
  "description": "Ambil uang dari atm",
  "payment_method": "Cash",
  "category": "Pemasukan"
}}

Input: "25K nasi goreng via ShopeePay"

Hanya balas dalam format JSON:
{{
  "transaction_type": "expense",
  "amount": 25000,
  "description": "nasi goreng",
  "payment_method": "ShopeePay",
  "category": "Makanan"
}}
Sekarang, analisis input berikut dan balas hanya dalam format JSON:
"{user_input}"
"""

def kirim_ke_gsheet(data_json, webhook_url):
    """Sends data to Google Apps Script Webhook."""
    try:
        response = requests.post(webhook_url, json=data_json, timeout=60) # Add timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logger.info("✅ Data successfully sent to Google Sheets.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to send data to Google Sheets: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred while sending to Google Sheets: {e}")
        return False

def ambil_json_dari_response(text):
    """Extracts the first valid JSON object from a string."""
    try:
        # Use a non-greedy match to find the first JSON object
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            json_str = match.group()
            # Basic validation before parsing
            if json_str.startswith('{') and json_str.endswith('}'):
                return json.loads(json_str)
            else:
                logger.warning(f"Extracted string doesn't look like valid JSON: {json_str}")
        else:
            logger.warning(f"No JSON object found in the text: {text}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from text: {e}\nText was: {text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during JSON extraction: {e}\nText was: {text}")
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages, processes them with Ollama, and sends to GSheet."""
    user_message = update.message.text
    if update.effective_user.id != AUTHORIZED_USER_ID:
        logger.info(f"Message from unauthorized user {update.effective_user.id}. Skipping processing.")
        await update.message.reply_text("Maaf, Anda tidak berwenang untuk menggunakan fitur ini.")
        return
    chat_id = update.effective_chat.id
    logger.info(f"Received message from chat_id {chat_id}: {user_message}")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": build_prompt(user_message),
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120) # Add timeout
        response.raise_for_status()
        ollama_response_data = response.json()
        ollama_text_response = ollama_response_data.get("response")

        if not ollama_text_response:
            logger.error("Ollama response did not contain 'response' key.")
            await update.message.reply_text("Maaf, terjadi masalah saat memproses respons dari AI.")
            return

        extracted_data = ambil_json_dari_response(ollama_text_response)

        if extracted_data:
            logger.info(f"Extracted data: {extracted_data}")

            # --- Amount Validation ---
            amount = extracted_data.get("amount")
            is_amount_valid = isinstance(amount, (int, float)) and amount > 0 # Check if amount is a positive number

            if not is_amount_valid:
                logger.warning(f"Invalid or missing 'amount' in extracted data: {amount}. Skipping GSheet upload.")
                await update.message.reply_text(f"⚠️ Jumlah pengeluaran ('amount') tidak terdeteksi atau tidak valid ({amount}). Data tidak disimpan.")
                return # Stop processing here

            # Send structured data back to user for confirmation (optional but good UX)
            # await update.message.reply_text(f"Data yang diekstrak:\n```json\n{json.dumps(extracted_data, indent=2)}\n```", parse_mode='MarkdownV2')

            if kirim_ke_gsheet(extracted_data, APP_SCRIPT_URL):
                await update.message.reply_text(f"✅ Data {extracted_data.get('category', 'N/A')} - {extracted_data.get('description', 'N/A')} ({extracted_data.get('amount', 'N/A')}) berhasil dicatat!")
            else:
                # Notify user that data was extracted but GSheet saving failed
                await update.message.reply_text(f"⚠️ Data {extracted_data.get('category', 'N/A')} - {extracted_data.get('description', 'N/A')} ({extracted_data.get('amount', 'N/A')}) berhasil diekstrak, TAPI GAGAL disimpan ke Google Sheets. Mohon periksa log atau coba lagi nanti.")
        else:
            logger.warning(f"Could not extract valid JSON from Ollama response: {ollama_text_response}")
            await update.message.reply_text("Maaf, saya tidak bisa mengekstrak informasi transaksi dari pesan Anda. Coba format yang berbeda?")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout connecting to Ollama API at {OLLAMA_URL}")
        await update.message.reply_text("Maaf, koneksi ke AI sedang lambat. Coba lagi sebentar.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Ollama API: {e}")
        await update.message.reply_text("Maaf, terjadi masalah saat menghubungi AI.")
    except KeyError as e:
        logger.error(f"Missing key in Ollama response: {e}. Response: {ollama_response_data}")
        await update.message.reply_text("Maaf, format respons dari AI tidak sesuai.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_message: {e}") # Use logger.exception to include traceback
        await update.message.reply_text("Maaf, terjadi kesalahan internal.")

async def show_daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and displays the expense summary for the current day."""
    today_str = date.today().isoformat() # Format: YYYY-MM-DD
    chat_id = update.effective_chat.id
    logger.info(f"Received /harian command from chat_id {chat_id}")

    # Construct the GET request URL for Google Apps Script
    # IMPORTANT: Assumes your Apps Script doGet function handles these parameters
    get_url = f"{APP_SCRIPT_URL}?action=get_daily&date={today_str}"

    await update.message.reply_text(f"⏳ Mengambil ringkasan pengeluaran untuk hari ini ({today_str})...")

    try:
        response = requests.get(get_url, timeout=20) # Timeout for GET request
        response.raise_for_status() # Check for HTTP errors

        daily_data = response.json() # Expecting JSON response from Apps Script

        if daily_data.get("status") == "success" and "expenses" in daily_data:
            expenses = daily_data["expenses"]
            total_today = daily_data.get("total", 0) # Get total if provided by Apps Script

            if not expenses:
                await update.message.reply_text(f"Belum ada pengeluaran yang tercatat untuk hari ini ({today_str}).")
                return

            # Format the message
            message_lines = [f"🧾 *Ringkasan Pengeluaran Hari Ini ({today_str})* 🧾\n"]
            for i, expense in enumerate(expenses, 1):
                # Assuming expense is a dict like {"description": "...", "amount": ...}
                desc = expense.get('description', 'N/A')
                amount = expense.get('amount', 0)
                category = expense.get('category', '')
                payment = expense.get('payment_method', '')
                message_lines.append(f"{i}. {desc} ({category}/{payment}) - Rp{amount:,}")

            message_lines.append(f"\n*Total Hari Ini: Rp{total_today:,}*")
            await update.message.reply_text("\n".join(message_lines), parse_mode='Markdown')

        else:
            error_message = daily_data.get("message", "Format respons tidak dikenali.")
            logger.warning(f"Failed to get daily summary from Apps Script: {error_message}")
            await update.message.reply_text(f"Gagal mengambil data: {error_message}")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout connecting to Google Apps Script GET endpoint at {get_url}")
        await update.message.reply_text("Maaf, koneksi ke Google Sheets sedang lambat. Coba lagi sebentar.")
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.error(f"Error fetching or parsing daily summary: {e}")
        await update.message.reply_text("Maaf, terjadi masalah saat mengambil atau memproses data dari Google Sheets.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in show_daily_summary: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan internal saat menampilkan ringkasan harian.")

async def show_all_time_financial_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and displays the all-time financial summary (expense - income)."""
    chat_id = update.effective_chat.id
    logger.info(f"Received /sisa_cash command from chat_id {chat_id}")

    get_url = f"{APP_SCRIPT_URL}?action=calculate_expense_minus_income"

    await update.message.reply_text("⏳ Menghitung ringkasan keuangan sepanjang waktu...")

    try:
        response = requests.get(get_url, timeout=20)
        response.raise_for_status()
        summary_data = response.json()

        if summary_data.get("status") == "success":
            total_expense = summary_data.get("totalExpense", 0)
            total_income = summary_data.get("totalIncome", 0)
            expense_minus_income = summary_data.get("expenseMinusIncome", 0)

            message_lines = [
                "📊 *Ringkasan Keuangan Sepanjang Waktu* 📊\n",
                f"💰 Total Pemasukan: Rp{total_income:,}",
                f"💸 Total Pengeluaran: Rp{total_expense:,}",
            ]

            # Jika expense_minus_income negatif, berarti income > expense
            # Ini bisa diinterpretasikan sebagai "Kelebihan Pemasukan" atau "Sisa Kas Bersih"
            message_lines.append(f"🏦 Sisa Cash: Rp{abs(expense_minus_income):,}")

            await update.message.reply_text("\n".join(message_lines), parse_mode='Markdown')
        else:
            error_message = summary_data.get("message", "Format respons tidak dikenali.")
            logger.warning(f"Failed to get all-time financial summary from Apps Script: {error_message}")
            await update.message.reply_text(f"Gagal mengambil data: {error_message}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching or parsing all-time financial summary: {e}")
        await update.message.reply_text("Maaf, terjadi masalah saat mengambil atau memproses data dari Google Sheets.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in show_all_time_financial_summary: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan internal saat menampilkan ringkasan keuangan.")

def main() -> None:
    """Starts the bot."""
    logger.info("Starting bot...")

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handler for text messages (excluding commands)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Add command handler for daily summary
    application.add_handler(CommandHandler("harian", show_daily_summary))

    # Add command handler for all-time financial summary
    application.add_handler(CommandHandler("sisa_cash", show_all_time_financial_summary))

    logger.info("Bot is running...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
