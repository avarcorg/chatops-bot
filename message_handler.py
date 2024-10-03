import logging
from requests.exceptions import RequestException

def handle_message(driver, post_data):
    """Process a new message."""
    try:
        logging.info(f"New message received: {post_data}")

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
        logging.error(f"RequestException handling message: {e}")
    except Exception as e:
        logging.error(f"Unexpected error handling message: {e}")
