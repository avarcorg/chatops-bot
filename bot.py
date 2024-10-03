import os
import json
import logging
import time
from mattermostdriver import Driver
from requests.exceptions import RequestException

# Set up application-level logging
app_debug_mode = os.getenv("APP_DEBUG", "false").lower() == "true"  # Read APP_DEBUG from env (default: false)
app_log_level = logging.DEBUG if app_debug_mode else logging.INFO
logging.basicConfig(level=app_log_level)

# Set up network-level debugging for Mattermost API calls
network_debug_mode = os.getenv("NETWORK_DEBUG", "false").lower() == "true"  # Read NETWORK_DEBUG from env (default: false)

class MattermostBot:
    def __init__(self):
        self.url = os.getenv("MATTERMOST_URL")  # Domain without scheme
        self.token = os.getenv("MATTERMOST_TOKEN")
        self.team_name = os.getenv("MATTERMOST_TEAM")
        self.port = int(os.getenv("MATTERMOST_PORT", 443))  # Default to 443, but allow override
        self.reconnect_delay = 10  # Time to wait before attempting reconnection

        # Initialize the Mattermost driver with network debugging based on the NETWORK_DEBUG flag
        self.driver = Driver({
            'url': self.url,
            'token': self.token,
            'scheme': 'https',  # Use https for port 443
            'port': self.port,  # Default to port 443, or custom port via env
            'verify': True,  # SSL verification
            'debug': network_debug_mode  # Enable or disable network debug mode based on the NETWORK_DEBUG flag
        })

    def run(self):
        try:
            logging.info("Logging in to Mattermost...")
            self.driver.login()
            logging.info("Login successful!")

            # Get team info
            team = self.driver.teams.get_team_by_name(self.team_name)
            if not team:
                logging.error(f"Team '{self.team_name}' not found.")
                return
            team_id = team['id']

            # Get current user information (for the bot user)
            bot_user = self.driver.users.get_user('me')
            bot_user_id = bot_user['id']
            logging.info(f"Bot user ID: {bot_user_id}")

            # Find or create a direct message (DM) channel with the bot user
            private_channel_id = self.get_private_channel(bot_user_id)
            if private_channel_id:
                # Get all channel names and send the announcement to the private DM channel
                channel_names = self.get_channel_names(bot_user_id, team_id)
                assist_message = f"Bot is now active and ready to assist. Here are the channels you have access to:\n{channel_names}"
                logging.info("Sending announcement to bot's private channel.")
                self.driver.posts.create_post({
                    'channel_id': private_channel_id,
                    'message': assist_message
                })
            else:
                logging.error("Failed to find or create a private channel for the bot.")

            # Start WebSocket connection
            self.connect_websocket()

        except RequestException as e:
            logging.error(f"RequestException during login or API call: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")

    def get_private_channel(self, bot_user_id):
        """Find or create a private DM channel for the bot."""
        try:
            logging.info("Retrieving bot's private channel...")

            # Find or create the direct message channel with the bot user
            direct_channel = self.driver.channels.create_direct_message_channel([bot_user_id, bot_user_id])

            if direct_channel and 'id' in direct_channel:
                logging.info(f"Private DM channel created/found with ID: {direct_channel['id']}")
                return direct_channel['id']
            else:
                logging.error("Failed to create/find a direct message channel.")
                return None
        except Exception as e:
            logging.error(f"Error getting private channel: {e}")
            return None

    def get_channel_names(self, bot_user_id, team_id):
        """Get a list of channel names the bot has access to in the team."""
        try:
            logging.info("Retrieving channel names...")
            channels = self.driver.channels.get_channels_for_user(bot_user_id, team_id)
            channel_names = [channel['display_name'] for channel in channels if 'display_name' in channel]
            logging.debug(f"Channel names: {channel_names}")
            return '\n'.join(channel_names)  # Return channel names as a newline-separated string
        except Exception as e:
            logging.error(f"Error retrieving channel names: {e}")
            return "No channels found."

    def connect_websocket(self):
        """Attempt to connect to the WebSocket and handle messages."""
        while True:
            try:
                logging.info("Initializing WebSocket connection...")
                self.driver.init_websocket(self.on_message)
            except WebSocketConnectionClosedException as e:
                logging.error(f"WebSocket connection closed: {e}")
            except Exception as e:
                logging.error(f"Error with WebSocket connection: {e}")
            
            logging.info(f"Reconnecting in {self.reconnect_delay} seconds...")
            time.sleep(self.reconnect_delay)  # Wait before trying to reconnect

    def on_message(self, message):
        """Handle incoming messages via WebSocket."""
        try:
            logging.info(f"New message received: {message}")

            # Respond to the message (extract channel ID and post a message)
            if 'event' in message and message['event'] == 'posted':
                post_data = json.loads(message['data']['post'])
                channel_id = post_data['channel_id']
                message_text = post_data['message']
                user_id = post_data['user_id']

                # Check if the message was sent by the bot itself to avoid an infinite loop
                bot_user = self.driver.users.get_user('me')
                if user_id == bot_user['id']:
                    return

                # If the message contains "hello", respond with "General Kenobi"
                if "hello" in message_text.lower():
                    self.driver.posts.create_post({
                        'channel_id': channel_id,
                        'message': "General Kenobi"
                    })

        except RequestException as e:
            logging.error(f"RequestException handling message: {e}")
        except Exception as e:
            logging.error(f"Unexpected error handling message: {e}")

if __name__ == "__main__":
    bot = MattermostBot()
    while True:
        try:
            bot.run()
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}")
            logging.info(f"Restarting bot in {bot.reconnect_delay} seconds...")
            time.sleep(bot.reconnect_delay)
