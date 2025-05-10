# Pengeluaran Bot

This is a Telegram bot that helps track personal expenses by analyzing input messages and extracting the details in a structured format. The bot uses the Ollama API to process the user's messages and send the extracted data to Google Sheets for further analysis.

## Features

- **Expense Tracking**: The bot listens to text messages from authorized users, extracts expense data, and logs it in Google Sheets.
- **Daily Summary**: Users can request a summary of all expenses for the current day.
- **Error Handling**: If something goes wrong, the bot will provide feedback to the user.
  
## Requirements

- Python 3.8+
- Install the required Python libraries using `pip`:
    ```bash
    pip install -r requirements.txt
    ```

## Setup

1. **Create a Telegram Bot**:
   - Go to [BotFather](https://core.telegram.org/bots#botfather) and create a new bot.
   - Get the bot's token from @BotFather, example 
    ```123456789:AAHhL8abcDefGhIjKlMnOpQrStUvWxYz```   


2. **Google Apps Script**:
   - Set up a Google Apps Script to handle the Google Sheets interaction. The bot will send expense data via POST requests to your Apps Script URL.
   - file for google sheet script google_sheet_script.js
   

3. **Run the Bot**:
   - Using supervisorctl to make it run, to set up
        Create a configuration file for the script in `/etc/supervisor/supervisord.conf`

        ```ini
        sudo nano /etc/supervisor/supervisord.conf
        ```

        add program

        ```ini
        [program:telegram_cost_tracker]
        command=/home/gws/project/telegram_cost_tracker/run_cost_tracker.sh
        directory=directory=/home/gws/project/telegram_cost_tracker
        autostart=true
        autorestart=true
        stderr_logfile=/home/gws/project/telegram_cost_tracker/log/run_cost_tracker.err.log
        stdout_logfile=/home/gws/project/telegram_cost_tracker/log/run_cost_tracker.out.log
        stopasgroup=true
        killasgroup=true
        ```

        #### Update Supervisor

        Once the configuration is added, update `supervisord` to read the new configuration:

        ```bash
        sudo supervisorctl reread
        sudo supervisorctl update
        ```

        #### Start the Program

        To start the program, use:

        ```bash
        sudo supervisorctl start telegram_cost_tracker
        ```
4. **Set up Environment Variables**:
   - Create a `.env` file in the project root directory with the following content:
     ```env
     OLLAMA_URL=your_ollama_url
     OLLAMA_MODEL=your_ollama_model
     BOT_TOKEN=your_telegram_bot_token
     APP_SCRIPT_URL=your_google_apps_script_url
     AUTHORIZED_USER_ID=your_telegram_user_id
     ```

## How it Works

1. **Message Handling**: 
   - When a user sends a message, the bot checks if the user is authorized.
   - The bot sends the user's message to the Ollama API for processing.
   - Ollama returns the processed response in JSON format, which is parsed by the bot.

2. **Expense Extraction**: 
   - The bot extracts the following fields from the user's message:
     - `amount`: The total expense in Rupiah.
     - `description`: A brief description of the item/service.
     - `payment_method`: The payment method used (e.g., ShopeePay, Cash).
     - `category`: The category of the expense (e.g., Makanan, Tagihan).

3. **Google Sheets Integration**:
   - The extracted data is sent to a Google Apps Script, which logs it in Google Sheets.

4. **Daily Summary**:
   - The bot can fetch the daily summary of expenses from the Google Sheets via the Apps Script endpoint and send it back to the user in a formatted message.

## Commands

- `/harian`: Fetches the expense summary for the current day.

