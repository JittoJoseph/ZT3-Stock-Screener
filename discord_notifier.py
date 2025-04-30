import requests
import json
from datetime import datetime, timezone
import time
import pytz # Import pytz for IST conversion
import os # Import os for basename

import config
from utils.helpers import logging

# New constants for report URLs (update these if the page URL changes)
SUCCESS_REPORT_URL = "https://jittojoseph.github.io/ZT3-Stock-Screener/"
FAILURE_REPORT_URL = "https://jittojoseph.github.io/ZT3-Stock-Screener/failure-report.html"

def send_discord_notification(
    shortlisted_stocks,
    duration_seconds=None
):
    """
    Sends a notification to the main Discord webhook.
    Instead of sending file attachments, includes hyperlinks to the success and failure reports.
    
    Args:
        shortlisted_stocks (list): List of stocks passing all criteria.
        report_filename (str, optional): Path to the success HTML report.
        failure_report_filename (str, optional): Path to the failure analysis HTML report.
        duration_seconds (float, optional): Time taken for screening.
    """
    webhook_url = config.get_discord_webhook_url()
    if not webhook_url:
        logging.warning("Discord webhook URL not configured. Skipping notification.")
        return

    screening_date = datetime.now(timezone.utc)
    screening_date_str = screening_date.strftime('%d %B %Y')
    username = "ZT-3 Screener"
    duration_str = f"{duration_seconds:.2f}s" if duration_seconds is not None and duration_seconds <= 60 else (
                   f"{int(duration_seconds//60)}m {int(duration_seconds%60)}s" if duration_seconds is not None else "")
    try:
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
        now_formatted_str = now_ist.strftime('Today at %I:%M %p IST') if now_ist.date() == datetime.now(ist_tz).date() else now_ist.strftime('%d %b %Y, %I:%M %p IST')
    except Exception as e:
        logging.error(f"Error formatting IST time: {e}")
        now_formatted_str = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')

    # Build common report links text
    report_links = (f"[Success Report]({SUCCESS_REPORT_URL}) | "
                    f"[Failure Analysis Report]({FAILURE_REPORT_URL})")

    if not shortlisted_stocks:
        logging.info("No stocks passed screening. Sending 'No Results' notification.")
        description = ("No stocks met the screening criteria today.\n\n"
                       f"You can view the reports here: {report_links}")
        footer_text = f"Took {duration_str}\n{now_formatted_str}" if duration_str else now_formatted_str
        payload = {
            "username": username,
            "embeds": [{
                "title": f"📉 ZT-3 Daily Scan - {screening_date_str}",
                "description": description,
                "color": 0xFFA500,
                "footer": {"text": footer_text},
            }]
        }
        try:
            response = requests.post(webhook_url, json=payload, timeout=15)
            response.raise_for_status()
            logging.info("Discord 'No Results' notification sent.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Discord 'No Results' notification: {e}")
            if e.response is not None:
                logging.error(f"Discord Response: {e.response.text}")
        except Exception as e:
            logging.error(f"Unexpected error sending Discord 'No Results' notification: {e}")
        return

    # For stocks found: create embeds with links added to the description.
    logging.info(f"Sending {len(shortlisted_stocks)} shortlisted stocks to Discord...")
    stock_count = len(shortlisted_stocks)
    embeds_to_send = []
    max_lines = 40
    max_chars = 4000
    current_desc = ""
    part_num = 1
    total_parts = (len(shortlisted_stocks) + max_lines - 1) // max_lines
    footer_text_main = f"Took {duration_str}\n{now_formatted_str}" if duration_str else now_formatted_str

    # Prepend the report links note in the first embed
    note = f"You can view the reports here: {report_links}\n\n"
    first_embed = True

    for i, stock in enumerate(shortlisted_stocks):
        line = f"**{stock.get('symbol', 'N/A')}** - ₹{stock.get('close', 0.00):.2f}\n"
        if len(current_desc) + len(line) > max_chars or current_desc.count('\n') >= max_lines:
            if first_embed:
                current_desc = note + current_desc
                first_embed = False
            embed_title = f"🚀 ZT-3 Breakout Alert ({stock_count} Stocks) - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else "")
            embeds_to_send.append({
                "title": embed_title,
                "description": current_desc,
                "color": 0x2ECC71,
                "footer": {"text": footer_text_main} if part_num == 1 else {}
            })
            current_desc = line
            part_num += 1
        else:
            current_desc += line

    if current_desc:
        if first_embed:
            current_desc = note + current_desc
        embed_title = f"🚀 ZT-3 Breakout Alert ({stock_count} Stocks) - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else "")
        embeds_to_send.append({
            "title": embed_title,
            "description": current_desc,
            "color": 0x2ECC71,
            "footer": {"text": footer_text_main} if part_num == 1 else {}
        })

    payload = {
        "username": username,
        "embeds": embeds_to_send
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        logging.info("Discord notification sent successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Discord notification: {e}")
        if e.response is not None:
            logging.error(f"Discord Response: {e.response.text}")
    except Exception as e:
        logging.error(f"Unexpected error sending Discord notification: {e}")

# Example usage (for testing later)
if __name__ == '__main__':
    # ... (Keep existing test setup but add failure report testing) ...
    logging.info("Testing discord_notifier module...")

    dummy_stocks_notify = [
        {'symbol': 'RELIANCE', 'close': 2880.50, 'timestamp': datetime.now()},
        {'symbol': 'TCS', 'close': 3465.20, 'timestamp': datetime.now()},
    ]
    dummy_duration = 125.67

    # Create dummy success and failure report files
    dummy_report_dir = config.settings['paths']['report_dir']
    os.makedirs(dummy_report_dir, exist_ok=True)
    dummy_success_report_file = os.path.join(dummy_report_dir, "dummy_success_report_test.html")
    dummy_failure_report_file = os.path.join(dummy_report_dir, "dummy_failure_report_test.html")

    try:
        with open(dummy_success_report_file, "w") as f: f.write("<html><body><h1>Success Report</h1></body></html>")
        with open(dummy_failure_report_file, "w") as f: f.write("<html><body><h1>Failure Analysis</h1></body></html>")
        logging.info("Created dummy report files.")
    except Exception as e:
        logging.error(f"Failed to create dummy report files: {e}")
        dummy_success_report_file = None
        dummy_failure_report_file = None

    logging.info("\n--- Testing Stocks Found Notification (with duration and BOTH attachments) ---") # Updated test description
    if not config.get_discord_webhook_url():
         logging.warning("Skipping test: DISCORD_WEBHOOK_URL not set in .env")
    elif dummy_success_report_file and dummy_failure_report_file: # Check both files exist
        send_discord_notification(dummy_stocks_notify, dummy_success_report_file, dummy_failure_report_file, dummy_duration) # Pass both files
        logging.info("Test notification sent (check Discord).")
    else:
        logging.warning("Skipping dual attachment test: one or both dummy files not created.")


    # Test case with no stocks (with failure attachment)
    logging.info("\n--- Testing No Stocks Notification (with duration and failure attachment) ---")
    if not config.get_discord_webhook_url():
         logging.warning("Skipping test: DISCORD_WEBHOOK_URL not set in .env")
    elif dummy_failure_report_file:
        send_discord_notification([], None, dummy_failure_report_file, dummy_duration) # Pass failure file
        logging.info("Test 'No Results' notification sent (check Discord).")
    else:
        logging.warning("Skipping failure attachment test: dummy file not created.")


    # Clean up dummy files
    for f in [dummy_success_report_file, dummy_failure_report_file]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
                logging.info(f"Removed dummy report file: {f}")
            except Exception as e:
                logging.error(f"Failed to remove dummy report file {f}: {e}")

    logging.info("\nDiscord_notifier module test finished.")
