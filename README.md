# Assistant telegram bot

Assistant bot monitors homework status submitted for code review. It sends API 
request every 10 minutes to Yandex.Practicum API endpoint and checks homework 
status change. When homework status have been changed, assistant bot parses the 
API response and sends message to Telegram.  


## Technology stack
- Python 3.7
- python-telegram-bot 13.7


## How it works
Functionality of the assitant bot is defined by functions:
- `main()` - program loop function.
- `check_tokens()` - checks environment variables and tokens.
- `get_api_answer()` - makes API request.
- `check_response()` - checks API response.
- `parse_status()` - parse homework status.
- `send_message()` - sends message to Telegram.

Custom exceptions are defined in `exceptions.py` file.


## How to install and run
1. Clone the repository.
```sh
# Clone the repositiry
git clone https://github.com/evgeny81d/homework_bot

# Go to the project directory
cd homework_bot

# Create Python 3.7 virtual environment
python3.7 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt --upgrade pip
```

2. Prepare access tokens. 
```
# Create .env file in the projects root directory with the following content
# API access token
PRACTICUM_TOKEN=...
# Telegram bot token
TELEGRAM_TOKEN=...
# Telegram chat ID
TELEGRAM_CHAT_ID=...
```


3. Start the assistan bot.
```sh
# Запускаем программу
python3 assistance_bot.py
```