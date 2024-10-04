import logging
from logging.handlers import TimedRotatingFileHandler
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

def handle_message(driver, post_data):
    """Process a new message."""
    try:
        logger.info(f"New message received: {post_data}")

        channel_id = post_data['channel_id']
        message_text = post_data['message']
        user_id = post_data['user_id']

        # Check if the message was sent by the bot itself to avoid an infinite loop
        bot_user = driver.users.get_user('me')
        if user_id == bot_user['id']:
            return

        # If the message contains "hello", respond with "General Kenobi"
        if "hello" in message_text.lower():
            driver.posts.create_post({
                'channel_id': channel_id,
                'message': "General Kenobi"
            })

    except RequestException as e:
        logger.error(f"RequestException handling message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error handling message: {e}")
