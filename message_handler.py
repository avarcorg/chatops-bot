import logging
from logging.handlers import TimedRotatingFileHandler
from requests.exceptions import RequestException
import os

# Define the log directory and file
log_directory = 'logs'
log_file = os.path.join(log_directory, 'message_handler.log')

# Create the log directory if it doesn't exist
if not os.path.exists(log_directory):
    os.makedirs(log_directory, exist_ok=True)

# Create a dedicated logger for message_handler
logger = logging.getLogger('message_handler')

# Set logging level (this can be customized)
logger.setLevel(logging.DEBUG)

# Create handlers for both file and console
file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
file_handler.suffix = "%Y-%m-%d"  # Log files will be named with a date suffix

console_handler = logging.StreamHandler()

# Set log level for each handler (optional)
file_handler.setLevel(logging.DEBUG)
console_handler.setLevel(logging.DEBUG)

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
if not logger.hasHandlers():  # To prevent adding multiple handlers if reloaded
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def is_direct_message(message):
    """Detect if the message was sent directly to the bot or starts with 'bot' (case insensitive)."""
    words = message.lower().split()
    logging.info(f"is_direct_message: list of words: {words}")
    return "avarc-chatops-bot" in words[0].lower()

def contains_hello_keyword(message):
    """Check if the message contains the word 'hello' (case insensitive)."""
    words = message.lower().split()
    # logging.info(f"contains_hello_keyword: list of words: {words}")
    return any(word == "hello" for word in words)

def contains_help_keyword(message):
    """Check if the message contains the word 'help' (case insensitive)."""
    words = message.lower().split()
    # logging.info(f"contains_help_keyword: list of words: {words}")
    return any(word == "help" for word in words)

def handle_message(driver, post_data):
    """Process a new message."""
    try:
        logger.info("")
        logger.info(f"New message received: {post_data}")
        logger.info("")

        channel_id = post_data['channel_id']
        message = post_data['message']
        user_id = post_data['user_id']

        # Check if the message was sent by the bot itself to avoid an infinite loop
        bot_user = driver.users.get_user('me')
        if user_id == bot_user['id']:
            return

        response = ""

        if is_direct_message(message):
            response = "Are you talking to me? :rocket:"

        if response:
            response += "\n"

        if contains_help_keyword(message):
            response += "Here are the commands I respond to: ..."
        elif contains_hello_keyword(message):
            response += "... again, General Kenobi :crossed_swords:"

        if response:
            send_mattermost_message(driver, channel_id, response)
        else:
            logger.info(f"Message received but not directed at the bot and contains no keywords: '{message}'")

    except RequestException as e:
        logger.error(f"RequestException handling message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error handling message: {e}")

def send_mattermost_message(driver, channel_id, message: str):
    try:
        logger.info(f"send_mattermost_message: '{message}'")

        driver.posts.create_post({
            'channel_id': channel_id,
            'message': message
        })
    except RequestException as e:
        logger.error(f"RequestException handling message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error handling message: {e}")
