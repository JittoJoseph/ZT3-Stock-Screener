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
    If stocks are found, lists them and attaches both success and failure reports (if available).
    If no stocks are found, sends a 'No Results' message and attaches the failure report (if available).

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


    # Determine which files to attach
    files_to_attach = {} # Use a dictionary for multiple files {form_field_name: (filename, file_handle, content_type)}
    success_report_attached = False
    failure_report_attached = False

    if shortlisted_stocks:
        # Attach success report if it exists
        if report_filename and os.path.exists(report_filename):
            try:
                report_basename = os.path.basename(report_filename)
                files_to_attach['file_success'] = (report_basename, open(report_filename, 'rb'), 'text/html')
                success_report_attached = True
                logging.info(f"Prepared success report for attachment: {report_basename}")
            except Exception as e:
                logging.error(f"Error preparing success report {report_filename} for attachment: {e}")
        elif report_filename:
             logging.warning(f"Success report file '{report_filename}' not found. Cannot attach.")

        # Attach failure report if it exists (even when success report is attached)
        if failure_report_filename and os.path.exists(failure_report_filename):
            try:
                failure_report_basename = os.path.basename(failure_report_filename)
                # Use a different field name if success report is also attached
                field_name = 'file_failure' if success_report_attached else 'file'
                files_to_attach[field_name] = (failure_report_basename, open(failure_report_filename, 'rb'), 'text/html')
                failure_report_attached = True
                logging.info(f"Prepared failure analysis report for attachment: {failure_report_basename}")
            except Exception as e:
                logging.error(f"Error preparing failure report {failure_report_filename} for attachment: {e}")
        elif failure_report_filename:
             logging.warning(f"Failure report file '{failure_report_filename}' not found. Cannot attach.")

    else: # No shortlisted stocks
        # Attach only failure report if it exists
        if failure_report_filename and os.path.exists(failure_report_filename):
            try:
                failure_report_basename = os.path.basename(failure_report_filename)
                files_to_attach['file'] = (failure_report_basename, open(failure_report_filename, 'rb'), 'text/html')
                failure_report_attached = True
                logging.info(f"Prepared failure analysis report for attachment: {failure_report_basename}")
            except Exception as e:
                logging.error(f"Error preparing failure report {failure_report_filename} for attachment: {e}")
        elif failure_report_filename:
             logging.warning(f"Failure report file '{failure_report_filename}' not found. Cannot attach.")


    # --- Handle No Results Case ---
    if not shortlisted_stocks:
        logging.info("No stocks passed screening. Sending 'No Results' notification.")
        description = "No stocks met the screening criteria today."
        if failure_report_attached:
            description += "\n\nFailure analysis report attached (showing stocks that nearly passed)."
        elif failure_report_filename and not failure_report_attached: # File was specified but not found/attached
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

        # Send the 'No Results' message (potentially with failure attachment)
        try:
            if files_to_attach: # Should only contain failure report here
                response = requests.post(
                    webhook_url,
                    files=files_to_attach, # Send the prepared file dictionary
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
        finally:
            # Close any open file handles
            for _, file_tuple in files_to_attach.items():
                if file_tuple and len(file_tuple) > 1 and file_tuple[1]:
                    try: file_tuple[1].close()
                    except Exception as e_close: logging.error(f"Error closing report file handle: {e_close}")
        return # Exit after sending no results message


    # --- Stocks were found ---
    logging.info(f"Sending {len(shortlisted_stocks)} shortlisted stocks to Discord...")
    stock_count = len(shortlisted_stocks) # Get the count

    # --- Create Embeds ---
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

    # Add note about attachments to the first embed's description
    attachment_note = ""
    if success_report_attached and failure_report_attached:
        attachment_note = "\n\nSuccess and Failure Analysis reports attached."
    elif success_report_attached:
        attachment_note = "\n\nSuccess report attached."
    elif failure_report_attached: # Should only happen if success report failed to attach but failure one succeeded
        attachment_note = "\n\nFailure Analysis report attached."

    first_embed = True
    for i, stock in enumerate(shortlisted_stocks):
        line = f"**{stock.get('symbol', 'N/A')}** - ₹{stock.get('close', 0.00):.2f}\n"
        # Check if adding the line (and potentially the attachment note) exceeds limits
        projected_len = len(current_description) + len(line) + (len(attachment_note) if first_embed else 0)
        projected_lines = current_description.count('\n') + 1

        if projected_len > max_chars_per_description or projected_lines >= max_lines_per_description:
            # Finalize current embed
            if first_embed:
                current_description += attachment_note # Add note before finalizing
                first_embed = False # Note added

            # Add stock count to the title here
            embed_title = f"🚀 ZT-3 Breakout Alert ({stock_count} Stocks) - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else "")
            embed = {
                "title": embed_title,
                "description": current_description,
                "color": 0x2ECC71,
                "footer": {"text": footer_text_main},
            }
            embeds_to_send.append(embed)
            # Start new embed
            current_description = line
            part_num += 1
            footer_text_main = None # Footer only on the first part
        else:
            current_description += line

    # Add the last embed
    if current_description:
        if first_embed: # Handle case where all stocks fit in one embed
            current_description += attachment_note
            first_embed = False

        # Add stock count to the title here as well
        embed_title = f"🚀 ZT-3 Breakout Alert ({stock_count} Stocks) - {screening_date_str}" + (f" (Part {part_num}/{total_parts})" if total_parts > 1 else "")
        embed = {
           "title": embed_title,
           "description": current_description,
           "color": 0x2ECC71,
        }
        if footer_text_main: # Add footer if this is the only part
             embed["footer"] = {"text": footer_text_main}
        embeds_to_send.append(embed)


    # --- Send the message(s) with attachments ---
    max_embeds_per_message = 10
    num_messages = (len(embeds_to_send) + max_embeds_per_message - 1) // max_embeds_per_message

    # Attach files only to the first message
    files_for_first_message = files_to_attach if files_to_attach else None

    for i in range(num_messages):
        start_index = i * max_embeds_per_message
        end_index = start_index + max_embeds_per_message
        embed_chunk = embeds_to_send[start_index:end_index]
        if not embed_chunk: continue

        payload = { "username": username, "embeds": embed_chunk }

        current_files = files_for_first_message if i == 0 else None

        try:
            if current_files:
                response = requests.post(
                    webhook_url,
                    files=current_files, # Send the prepared file dictionary
                    data={'payload_json': json.dumps(payload)},
                    timeout=30
                )
            else:
                response = requests.post(webhook_url, json=payload, timeout=15)
            response.raise_for_status()
            logging.info(f"Discord notification sent successfully (Message {i+1}/{num_messages}).")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Discord notification (Message {i+1}/{num_messages}): {e}")
            if e.response is not None: logging.error(f"Discord Response: {e.response.text}")
        except Exception as e:
             logging.error(f"Unexpected error sending Discord notification (Message {i+1}/{num_messages}): {e}")
        finally:
            # Close file handles only after the first message is sent (or attempted)
            if i == 0 and files_for_first_message:
                for _, file_tuple in files_for_first_message.items():
                    if file_tuple and len(file_tuple) > 1 and file_tuple[1]:
                        try: file_tuple[1].close()
                        except Exception as e_close: logging.error(f"Error closing report file handle: {e_close}")

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
