import requests
import json
from datetime import datetime, timezone
import time
import pytz # Import pytz for IST conversion
import os # Import os for basename

import config
from utils.helpers import logging

def send_discord_notification(
    shortlisted_stocks,
    report_filename=None,
    failure_report_filename=None, # Add failure report filename parameter
    duration_seconds=None
):
    """
    Sends a notification to the main Discord webhook.
    If stocks are found, lists them and attaches the success report.
    If no stocks are found, sends a 'No Results' message and attaches the failure report if available.

    Args:
        shortlisted_stocks (list): List of stocks passing all criteria.
        report_filename (str, optional): Path to the success HTML report.
        failure_report_filename (str, optional): Path to the failure analysis HTML report.
        duration_seconds (float, optional): Time taken for screening.
    """
    webhook_url = config.get_discord_webhook_url()
    if not webhook_url:
        logging.warning("Main Discord webhook URL (DISCORD_WEBHOOK_URL) not configured. Skipping notification.")
        return

    # ... existing date/time formatting ...
    screening_date = datetime.now(timezone.utc)
    screening_date_str = screening_date.strftime('%d %B %Y')
    username = "ZT-3 Screener"
    duration_str = ""
    if duration_seconds is not None:
        if duration_seconds > 60:
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{duration_seconds:.2f}s"
    try:
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
        if now_ist.date() == datetime.now(ist_tz).date():
            now_formatted_str = now_ist.strftime('Today at %I:%M %p IST') # Added IST
        else:
            now_formatted_str = now_ist.strftime('%d %b %Y, %I:%M %p IST') # Added IST
    except Exception as e:
        logging.error(f"Error getting/formatting IST time: {e}")
        now_formatted_str = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')


    # Determine which file to attach (only one)
    file_to_attach = None
    report_type = "success" # Default
    if shortlisted_stocks and report_filename and os.path.exists(report_filename):
        file_to_attach = report_filename
        logging.info(f"Will attach success report: {file_to_attach}")
    elif not shortlisted_stocks and failure_report_filename and os.path.exists(failure_report_filename):
        file_to_attach = failure_report_filename
        report_type = "failure analysis"
        logging.info(f"Will attach failure analysis report: {file_to_attach}")
    elif report_filename and not os.path.exists(report_filename):
         logging.warning(f"Success report file '{report_filename}' not found. Sending notification without attachment.")
    elif failure_report_filename and not os.path.exists(failure_report_filename):
         logging.warning(f"Failure report file '{failure_report_filename}' not found. Sending notification without attachment.")


    # --- Handle No Results Case ---
    if not shortlisted_stocks:
        logging.info("No stocks passed screening. Sending 'No Results' notification.")
        description = "No stocks met the screening criteria today."
        if file_to_attach and report_type == "failure analysis":
            description += "\n\nFailure analysis report attached (showing stocks that nearly passed)."
        elif failure_report_filename and not file_to_attach: # File was specified but not found/attached
             description += "\n\nFailure analysis report was generated but could not be attached."
        else: # No failure report generated or specified
             description += "\n\nNo failure analysis report was generated."


        footer_text = "Scan completed"
        if duration_str:
            footer_text = f"Took {duration_str}"
        footer_text += f"\n{now_formatted_str}"

        payload = {
            "username": username,
            "embeds": [{
                "title": f"📉 ZT-3 Daily Scan - {screening_date_str}",
                "description": description, # Updated description
                "color": 0xFFA500, # Orange color
                "footer": {"text": footer_text},
            }]
        }

        # Prepare file data if attaching failure report
        files_data = None
        report_basename = None
        if file_to_attach:
            report_basename = os.path.basename(file_to_attach)
            try:
                files_data = {'file': (report_basename, None, 'text/html')} # Placeholder
            except Exception as e:
                logging.error(f"Error preparing file data for {file_to_attach}: {e}")
                files_data = None

        # Send the 'No Results' message (potentially with attachment)
        try:
            if files_data:
                with open(file_to_attach, 'rb') as f_handle:
                    current_files_data = {'file': (report_basename, f_handle, 'text/html')}
                    response = requests.post(
                        webhook_url,
                        files=current_files_data,
                        data={'payload_json': json.dumps(payload)},
                        timeout=30
                    )
            else:
                response = requests.post(webhook_url, json=payload, timeout=15)

            response.raise_for_status()
            logging.info("Discord 'No Results' notification sent.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Discord 'No Results' notification: {e}")
            if e.response is not None: logging.error(f"Discord Response: {e.response.text}")
        except Exception as e:
             logging.error(f"Unexpected error sending Discord 'No Results' notification: {e}")
        return # Exit after sending no results message


    # --- Stocks were found ---
    logging.info(f"Sending {len(shortlisted_stocks)} shortlisted stocks to Discord...")

    # ... existing logic for creating embeds for shortlisted stocks ...
    embeds_to_send = []
    max_chars_per_description = 4000
    max_lines_per_description = 40
    current_description = ""
    part_num = 1
    lines_needed = len(shortlisted_stocks)
    total_parts = (lines_needed + max_lines_per_description - 1) // max_lines_per_description
    footer_text_main = "Potential Breakouts Found"
    if duration_str:
        footer_text_main = f"Took {duration_str}"
    footer_text_main += f"\n{now_formatted_str}"

    for i, stock in enumerate(shortlisted_stocks):
        line = f"**{stock.get('symbol', 'N/A')}** - ₹{stock.get('close', 0.00):.2f}\n"
        if len(current_description) + len(line) > max_chars_per_description or \
           current_description.count('\n') >= max_lines_per_description:
            embed = {
                "title": f"🚀 ZT-3 Breakout Alert - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else ""),
                "description": current_description,
                "color": 0x2ECC71,
                "footer": {"text": footer_text_main},
            }
            embeds_to_send.append(embed)
            current_description = line
            part_num += 1
            footer_text_main = None
        else:
            current_description += line
    if current_description:
         embed = {
            "title": f"🚀 ZT-3 Breakout Alert - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else ""),
            "description": current_description,
            "color": 0x2ECC71,
         }
         if footer_text_main:
              embed["footer"] = {"text": footer_text_main}
         embeds_to_send.append(embed)


    # --- Send the message(s) with potential success report attachment ---
    max_embeds_per_message = 10
    num_messages = (len(embeds_to_send) + max_embeds_per_message - 1) // max_embeds_per_message

    # Prepare file data only if attaching success report
    files_data = None
    report_basename = None
    if file_to_attach and report_type == "success": # Check report type here
        report_basename = os.path.basename(file_to_attach)
        try:
            files_data = {'file': (report_basename, None, 'text/html')} # Placeholder
            logging.info(f"Prepared success report file '{report_basename}' for attachment.")
        except Exception as e:
            logging.error(f"Error preparing file data for {file_to_attach}: {e}")
            files_data = None

    for i in range(num_messages):
        # ... existing chunking logic ...
        start_index = i * max_embeds_per_message
        end_index = start_index + max_embeds_per_message
        embed_chunk = embeds_to_send[start_index:end_index]
        if not embed_chunk: continue

        payload = { "username": username, "embeds": embed_chunk }

        # Attach success report file only to the first message
        current_files_data = None
        if i == 0 and files_data: # files_data is only prepared for success reports now
            try:
                file_handle = open(file_to_attach, 'rb')
                current_files_data = {'file': (report_basename, file_handle, 'text/html')}
            except Exception as e:
                logging.error(f"Error opening success report file {file_to_attach} for sending: {e}")
                current_files_data = None

        try:
            # ... existing sending logic (with or without file) ...
            if current_files_data:
                response = requests.post(
                    webhook_url,
                    files=current_files_data,
                    data={'payload_json': json.dumps(payload)},
                    timeout=30
                )
            else:
                response = requests.post(webhook_url, json=payload, timeout=15)
            response.raise_for_status()
            logging.info(f"Discord notification sent successfully (Message {i+1}/{num_messages}).")

        except requests.exceptions.RequestException as e:
            # ... existing error handling ...
            logging.error(f"Error sending Discord notification (Message {i+1}/{num_messages}): {e}")
            if e.response is not None: logging.error(f"Discord Response: {e.response.text}")
        except Exception as e:
             logging.error(f"Unexpected error sending Discord notification (Message {i+1}/{num_messages}): {e}")
        finally:
            # ... existing file closing logic ...
            if current_files_data and 'file' in current_files_data and current_files_data['file'][1]:
                try: current_files_data['file'][1].close()
                except Exception as e: logging.error(f"Error closing report file handle: {e}")

        if num_messages > 1 and i < num_messages - 1:
            time.sleep(1)

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

    logging.info("\n--- Testing Stocks Found Notification (with duration and success attachment) ---")
    if not config.get_discord_webhook_url():
         logging.warning("Skipping test: DISCORD_WEBHOOK_URL not set in .env")
    elif dummy_success_report_file:
        send_discord_notification(dummy_stocks_notify, dummy_success_report_file, None, dummy_duration) # Pass success file
        logging.info("Test notification sent (check Discord).")
    else:
        logging.warning("Skipping success attachment test: dummy file not created.")


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
