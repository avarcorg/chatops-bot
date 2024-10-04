import os
import json
import logging
import time
import asyncio
import traceback  # Added for traceback handling
from mattermostdriver import Driver
from requests.exceptions import RequestException
from websocket import WebSocketConnectionClosedException
from message_handler import handle_message  # Import the handle_message function
from channel_notification import send_initial_channel_notification  # Import the notification function

# Set up application-level logging
app_debug_mode = os.getenv("APP_DEBUG", "false").lower() == "true"  # Read APP_DEBUG from env (default: false)
network_debug_mode = os.getenv("NETWORK_DEBUG", "false").lower() == "true"  # Read NETWORK_DEBUG from env (default: false)

app_log_level = logging.DEBUG if app_debug_mode else logging.INFO
logging.basicConfig(level=app_log_level)

# Configure dedicated loggers for message_handler and channel_notification
logging.getLogger('message_handler').setLevel(logging.DEBUG)
logging.getLogger('channel_notification').setLevel(app_log_level)

class MattermostBot:
    def __init__(self):
        self.host = os.getenv("MATTERMOST_HOST")
        self.scheme = os.getenv("MATTERMOST_SCHEME", "https")
        self.token = os.getenv("MATTERMOST_TOKEN")
        self.team_name = os.getenv("MATTERMOST_TEAM")
        self.port = int(os.getenv("MATTERMOST_PORT", 443))  # Default to 443, but allow override
        self.poll_interval = 10  # Time to wait between polling for new messages (in seconds)
        self.reconnect_delay = 15 * 60  # Time to wait (15 minutes) before retrying WebSocket after polling

        # Initialize the Mattermost driver with network debugging based on the NETWORK_DEBUG flag
        self.driver = Driver({
            'url': self.host,
            'token': self.token,
            'scheme': self.scheme,
            'port': self.port,
            'verify': True,  # SSL verification
            'debug': network_debug_mode  # Enable or disable network debug mode based on the NETWORK_DEBUG flag
        })

    async def run(self):
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
                # Get all channel names and send the notification using the external function
                channel_names = self.get_channel_names(bot_user_id, team_id)
                send_initial_channel_notification(self.driver, private_channel_id, channel_names)
            else:
                logging.error("Failed to find or create a private channel for the bot.")

            # Attempt WebSocket connection first, with a fallback to polling
            await self.connect_websocket_or_fallback(bot_user_id, team_id)

        except RequestException as e:
            logging.error(f"RequestException during login or API call: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            logging.error(traceback.format_exc())  # Print full traceback

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
            logging.error(traceback.format_exc())  # Print full traceback
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
            logging.error(traceback.format_exc())  # Print full traceback
            return "No channels found."

    async def connect_websocket_or_fallback(self, bot_user_id, team_id):
        """Attempt to connect to WebSocket, and fall back to polling if it fails."""
        try:
            logging.info("Attempting WebSocket connection...")

            # Await WebSocket connection if it's async
            await self.driver.init_websocket(self.on_message)  # WebSocket message handler

        except WebSocketConnectionClosedException as e:
            logging.error(f"WebSocket connection failed: {e}. Switching to polling mode.")
            await self.poll_messages(bot_user_id, team_id)
        except Exception as e:
            logging.error(f"Error establishing WebSocket connection: {e}")
            logging.error(traceback.format_exc())  # Print full traceback
            await self.poll_messages(bot_user_id, team_id)

    async def on_message(self, message):
        """Handle incoming messages from WebSocket."""
        try:
            logging.info(f"New message received: {message}")

            # Ensure the message is parsed as JSON
            if isinstance(message, str):
                message = json.loads(message)

            # Extract the post data from the message
            if 'event' in message and message['event'] == 'posted':
                post_data = json.loads(message['data']['post'])
                handle_message(self.driver, post_data)  # Use the imported handle_message

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON message: {e}")
            logging.error(traceback.format_exc())  # Print full traceback
        except KeyError as e:
            logging.error(f"KeyError: Missing key {e} in message: {message}")
            logging.error(traceback.format_exc())  # Print full traceback
        except RequestException as e:
            logging.error(f"RequestException handling WebSocket message: {e}")
            logging.error(traceback.format_exc())  # Print full traceback
        except Exception as e:
            logging.error(f"Unexpected error handling WebSocket message: {e}")
            logging.error(traceback.format_exc())  # Print full traceback

    async def poll_messages(self, bot_user_id, team_id):
        """Poll the channels for new messages and handle them."""
        last_checked = int(time.time())  # Start polling from the current time
        polling_start_time = time.time()  # Track the time when polling starts

        while True:
            try:
                logging.debug("Polling for new messages...")
                channels = self.driver.channels.get_channels_for_user(bot_user_id, team_id)

                for channel in channels:
                    posts = self.driver.posts.get_posts_for_channel(channel['id'], params={'since': last_checked * 1000})
                    if 'posts' in posts:
                        for post_id, post_data in posts['posts'].items():
                            handle_message(self.driver, post_data)  # Use the imported handle_message

                last_checked = int(time.time())

                # Check if 15 minutes have passed to retry WebSocket
                if time.time() - polling_start_time >= self.reconnect_delay:
                    logging.info("15 minutes of polling passed. Retrying WebSocket connection.")
                    try:
                        await self.connect_websocket_or_fallback(bot_user_id, team_id)
                        break  # Exit polling loop if WebSocket succeeds
                    except WebSocketConnectionClosedException as e:
                        logging.error(f"WebSocket reconnection failed: {e}. Continuing polling.")
                        polling_start_time = time.time()  # Reset polling start time after WebSocket failure

            except RequestException as e:
                logging.error(f"RequestException while polling for messages: {e}")
                logging.error(traceback.format_exc())  # Print full traceback
            except Exception as e:
                logging.error(f"Unexpected error while polling for messages: {e}")
                logging.error(traceback.format_exc())  # Print full traceback

            logging.debug(f"Sleeping for {self.poll_interval} seconds before next poll...")
            await asyncio.sleep(self.poll_interval)

if __name__ == "__main__":
    bot = MattermostBot()

    async def run_bot():
        while True:
            try:
                await bot.run()  # Run the bot asynchronously
            except Exception as e:
                logging.error(f"Bot crashed with error: {e}")
                logging.error(traceback.format_exc())  # Print full traceback
                logging.info(f"Restarting bot in {bot.poll_interval} seconds...")
                await asyncio.sleep(bot.poll_interval)  # Use asyncio.sleep in async code

    # Check if the event loop is already running
    try:
        loop = asyncio.get_running_loop()
        logging.info("Event loop is already running. Creating task for the bot.")
        loop.create_task(run_bot())
    except RuntimeError:  # No loop is running
        logging.info("No event loop running. Starting new event loop.")
        asyncio.run(run_bot())
