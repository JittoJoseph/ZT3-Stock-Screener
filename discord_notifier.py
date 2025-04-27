import requests
import json
from datetime import datetime, timezone
import time

import config
from utils.helpers import logging

def send_discord_notification(shortlisted_stocks):
    """
    Sends a notification with the list of shortlisted stocks to the main Discord webhook.

    Args:
        shortlisted_stocks (list): A list of dictionaries, where each dict
                                   represents a stock that passed screening.
                                   Expected keys: 'symbol', 'close', 'timestamp'.
    """
    webhook_url = config.get_discord_webhook_url()
    if not webhook_url:
        logging.warning("Main Discord webhook URL (DISCORD_WEBHOOK_URL) not configured. Skipping notification.")
        return

    # Get screening date (use today's date if list is empty)
    screening_date = datetime.now(timezone.utc)
    if shortlisted_stocks and 'timestamp' in shortlisted_stocks[0]:
        # Use the timestamp from the data if available, converting to local timezone might be better if server isn't UTC
        # For simplicity, we'll use the date part of the timestamp from the data (assuming it's daily data)
        screening_date = shortlisted_stocks[0]['timestamp']
    screening_date_str = screening_date.strftime('%d %B %Y') # Format like 27 April 2025

    username = "ZT-3 Screener"

    if not shortlisted_stocks:
        logging.info("No stocks passed screening. Sending 'No Results' notification.")
        payload = {
            "username": username,
            "embeds": [{
                "title": f"📉 ZT-3 Daily Scan - {screening_date_str}",
                "description": "No stocks met the breakout criteria today.",
                "color": 0xFFA500, # Orange color for no results/warning
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }
        try:
            requests.post(webhook_url, json=payload, timeout=10)
            logging.info("Discord 'No Results' notification sent.")
        except Exception as e:
            logging.error(f"Error sending Discord 'No Results' notification: {e}")
        return

    # --- Stocks were found ---
    logging.info(f"Sending {len(shortlisted_stocks)} shortlisted stocks to Discord...")

    embeds_to_send = []
    max_chars_per_description = 4000
    max_lines_per_description = 40 # Adjusted for better readability

    current_description = ""
    part_num = 1
    lines_needed = len(shortlisted_stocks)
    total_parts = (lines_needed + max_lines_per_description - 1) // max_lines_per_description

    timestamp_now = datetime.now(timezone.utc) # Timestamp for the embed footer

    for i, stock in enumerate(shortlisted_stocks):
        # Format: **SYMBOL** - ₹PRICE
        line = f"**{stock.get('symbol', 'N/A')}** - ₹{stock.get('close', 0.00):.2f}\n"

        if len(current_description) + len(line) > max_chars_per_description or \
           current_description.count('\n') >= max_lines_per_description:

            embed = {
                "title": f"🚀 ZT-3 Breakout Alert - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else ""),
                "description": current_description,
                "color": 0x2ECC71, # Green color for success/results
                "footer": {"text": "Potential Breakouts Found"},
                "timestamp": timestamp_now.isoformat()
            }
            embeds_to_send.append(embed)

            current_description = line
            part_num += 1
            timestamp_now = None # Only add timestamp/footer to the first embed
        else:
            current_description += line

    if current_description:
         embed = {
            "title": f"🚀 ZT-3 Breakout Alert - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else ""),
            "description": current_description,
            "color": 0x2ECC71, # Green color
         }
         if timestamp_now: # Add footer/timestamp only if it's the first/only embed
              embed["footer"] = {"text": "Potential Breakouts Found"}
              embed["timestamp"] = timestamp_now.isoformat()
         embeds_to_send.append(embed)

    # --- Send the message(s) ---
    max_embeds_per_message = 10
    num_messages = (len(embeds_to_send) + max_embeds_per_message - 1) // max_embeds_per_message

    for i in range(num_messages):
        start_index = i * max_embeds_per_message
        end_index = start_index + max_embeds_per_message
        embed_chunk = embeds_to_send[start_index:end_index]

        if not embed_chunk:
            continue

        payload = {
            "username": username,
            "avatar_url": avatar_url,
            "embeds": embed_chunk
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=15)
            response.raise_for_status()
            logging.info(f"Discord notification sent successfully (Message {i+1}/{num_messages}).")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Discord notification (Message {i+1}/{num_messages}): {e}")
            if e.response is not None:
                logging.error(f"Discord Response: {e.response.text}")
        except Exception as e:
             logging.error(f"Unexpected error sending Discord notification (Message {i+1}/{num_messages}): {e}")

        if num_messages > 1 and i < num_messages - 1:
            time.sleep(1)


# Example usage (for testing later)
if __name__ == '__main__':
    logging.info("Testing discord_notifier module...")

    # Dummy data matching the expected output of screener_logic
    dummy_stocks_notify = [
        {'symbol': 'RELIANCE', 'close': 2880.50, 'timestamp': datetime.now()},
        {'symbol': 'TCS', 'close': 3465.20, 'timestamp': datetime.now()},
        {'symbol': 'HDFCBANK', 'close': 1622.80, 'timestamp': datetime.now()},
        # Add more stocks to test splitting if needed (e.g., 60 stocks)
        # *[{'symbol': f'STOCK{i}', 'close': 100.00 + i, 'timestamp': datetime.now()} for i in range(60)]
    ]

    if not config.get_discord_webhook_url():
         logging.warning("Skipping test: DISCORD_WEBHOOK_URL not set in .env")
    else:
        send_discord_notification(dummy_stocks_notify)
        logging.info("Test notification sent (check Discord).")

    # Test case with no stocks
    logging.info("\n--- Testing No Stocks Notification ---")
    if not config.get_discord_webhook_url():
         logging.warning("Skipping test: DISCORD_WEBHOOK_URL not set in .env")
    else:
        send_discord_notification([])
        logging.info("Test 'No Results' notification sent (check Discord).")

    logging.info("\nDiscord_notifier module test finished.")
