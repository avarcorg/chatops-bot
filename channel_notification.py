import logging

def send_initial_channel_notification(driver, private_channel_id, channel_names):
    """Send a notification to the bot's private channel listing all available channels."""
    try:
        assist_message = (
            f"Bot is now active and ready to assist. "
            f"Here are the channels you have access to:\n{channel_names}"
        )
        logging.info("Sending initial notification to bot's private channel.")
        driver.posts.create_post({
            'channel_id': private_channel_id,
            'message': assist_message
        })
    except Exception as e:
        logging.error(f"Failed to send initial channel join notification: {e}")
