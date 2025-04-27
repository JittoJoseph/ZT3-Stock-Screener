#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validate Instrument Keys from stock_list.csv using Upstox API.

This script reads the stock list, constructs the Upstox instrument key
(assuming NSE Equity), and attempts to fetch minimal historical data
to verify if the key is valid on the Upstox platform.
"""

import sys
import os
# Add project root to path to allow importing config, data_fetcher etc.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import requests # Ensure requests is imported
from datetime import datetime, timedelta, timezone # Import timezone
import time
import json # Import json for discord payload
import pytz # Import pytz for IST conversion
import csv # Import csv module

# Import necessary functions from our modules
import config
from data_fetcher import get_api_headers, API_VERSION # Import necessary items
from utils.helpers import load_stock_list, logging # Import from helpers

# --- Configuration ---
# Assume NSE Equity for constructing the key. Modify if needed.
EXCHANGE = "NSE"
INSTRUMENT_TYPE = "EQ"
VALIDATION_INTERVAL = "1minute" # Use a small interval for quick check
VALIDATION_DAYS_BACK = 2 # Check data for the last couple of days

# --- Helper Functions ---

def validate_instrument_key(instrument_key, headers):
    """
    Attempts to fetch minimal historical data to validate an instrument key.

    Args:
        instrument_key (str): The Upstox instrument key (e.g., 'NSE_EQ|INE002A01018').
        headers (dict): The authentication headers for the API request.

    Returns:
        bool: True if the key seems valid (API returns success), False otherwise.
    """
    # Use a very small date range for validation
    to_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d') # Yesterday
    from_date = (datetime.now() - timedelta(days=VALIDATION_DAYS_BACK)).strftime('%Y-%m-%d')

    # URL Encode the instrument key for safety
    encoded_instrument_key = requests.utils.quote(instrument_key)

    # Construct URL based on historical data endpoint structure
    # Using the documented path: /historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
    url = f"https://api.upstox.com/{API_VERSION}/historical-candle/{encoded_instrument_key}/{VALIDATION_INTERVAL}/{to_date}/{from_date}"
    logging.debug(f"Validation URL: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10) # Add timeout

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                # Even if 'candles' is empty, a 'success' status means the key is recognized
                logging.debug(f"Validation success for {instrument_key} (Status: {data.get('status')})")
                return True
            else:
                # API returned 200 OK but status was not 'success'
                logging.warning(f"Validation failed for {instrument_key}. API Status: {data.get('status')}, Message: {data.get('message', 'N/A')}")
                return False
        elif response.status_code == 404:
             # Not Found likely means invalid instrument key
             logging.warning(f"Validation failed for {instrument_key}. HTTP Status: 404 (Not Found)")
             return False
        elif response.status_code == 400:
             # Bad Request often indicates an invalid format or unrecognized key by the API logic
             try:
                 error_data = response.json()
                 error_msg = error_data.get('errors', [{}])[0].get('message', response.text[:100])
                 logging.warning(f"Validation failed for {instrument_key}. HTTP Status: 400 (Bad Request). Reason: {error_msg}")
             except json.JSONDecodeError:
                 logging.warning(f"Validation failed for {instrument_key}. HTTP Status: 400 (Bad Request). Response: {response.text[:200]}")
             return False
        else:
            # Other HTTP errors
            logging.error(f"Validation HTTP error for {instrument_key}. Status: {response.status_code}, Response: {response.text[:200]}")
            return False

    except requests.exceptions.Timeout:
        logging.error(f"Validation timeout for {instrument_key}")
        return False # Treat timeout as failure
    except requests.exceptions.RequestException as e:
        logging.error(f"Validation request error for {instrument_key}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during validation for {instrument_key}: {e}")
        return False

def send_stocklist_to_discord(valid_stocks, invalid_stocks, total_checked, duration_seconds, webhook_url):
    """Sends validation results (valid & invalid lists) to Discord using embeds."""
    if not webhook_url:
        logging.warning("Discord stocklist webhook URL not configured. Skipping notification.")
        return

    # --- Common Info ---
    # Format duration
    duration_str = f"{duration_seconds:.2f} seconds"
    if duration_seconds > 60:
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        duration_str = f"{minutes}m {seconds}s"

    # Get current time in IST and format conditionally
    try:
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
        today_ist_date = now_ist.date()
        if now_ist.date() == today_ist_date:
            now_formatted_str = now_ist.strftime('Today at %I:%M %p')
        else:
            now_formatted_str = now_ist.strftime('%d %b %Y, %I:%M %p')
    except Exception as e:
        logging.error(f"Error getting/formatting IST time: {e}")
        now_formatted_str = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')

    username = "Stocklist Validator"
    embeds_to_send = [] # Initialize list to hold all embeds

    # --- Footer Text (Common for first embed of each type) ---
    footer_text_common = f"Took {duration_str}\n{now_formatted_str}"

    # --- Embed Generation ---

    # 1. Valid Stocks Embed(s)
    if valid_stocks:
        logging.info(f"Generating embed(s) for {len(valid_stocks)} valid stocks...")
        color_valid = 0x00FF00 # Green
        max_chars = 4000
        max_lines = 50
        current_desc_valid = ""
        part_num_valid = 1
        lines_needed_valid = len(valid_stocks)
        total_parts_valid = (lines_needed_valid + max_lines - 1) // max_lines
        footer_valid = footer_text_common # Use common footer for the first valid embed

        for i, stock in enumerate(valid_stocks):
            line = f"{i+1}. {stock['symbol']} ({stock['isin']})\n"
            if len(current_desc_valid) + len(line) > max_chars or \
               current_desc_valid.count('\n') >= max_lines:
                embed = {
                    "title": f"Valid Stock List ({len(valid_stocks)} Total)" + (f" - Part {part_num_valid}/{total_parts_valid}" if total_parts_valid > 1 else ""),
                    "description": current_desc_valid,
                    "color": color_valid,
                    "footer": {"text": footer_valid},
                }
                embeds_to_send.append(embed)
                current_desc_valid = line
                part_num_valid += 1
                footer_valid = None # No footer for subsequent parts
            else:
                current_desc_valid += line

        if current_desc_valid:
             embed = {
                "title": f"Valid Stock List ({len(valid_stocks)} Total)" + (f" - Part {part_num_valid}/{total_parts_valid}" if total_parts_valid > 1 else ""),
                "description": current_desc_valid,
                "color": color_valid,
             }
             if footer_valid:
                  embed["footer"] = {"text": footer_valid}
             embeds_to_send.append(embed)
    else:
        # If no valid stocks, add a placeholder message embed
        logging.info("No valid stocks found.")
        embed = {
            "title": f"Stock List Validation Results",
            "description": f"Checked {total_checked} stocks. No valid ISINs found.",
            "color": 0xFFA500, # Orange
            "footer": {"text": footer_text_common}, # Still show footer
        }
        embeds_to_send.append(embed)


    # 2. Invalid Stocks Embed(s)
    if invalid_stocks:
        logging.info(f"Generating embed(s) for {len(invalid_stocks)} invalid stocks...")
        color_invalid = 0xFF0000 # Red
        max_chars = 4000
        max_lines = 50
        current_desc_invalid = ""
        part_num_invalid = 1
        lines_needed_invalid = len(invalid_stocks)
        total_parts_invalid = (lines_needed_invalid + max_lines - 1) // max_lines
        # Use common footer only if no valid stock embeds were added OR if valid embeds exist but had no footer space
        footer_invalid = footer_text_common if not embeds_to_send or "footer" not in embeds_to_send[0] else None

        for i, stock in enumerate(invalid_stocks):
            line = f"{i+1}. {stock['symbol']} ({stock['isin']})\n" # Assuming same structure
            if len(current_desc_invalid) + len(line) > max_chars or \
               current_desc_invalid.count('\n') >= max_lines:
                embed = {
                    "title": f"Invalid Stock List ({len(invalid_stocks)} Total)" + (f" - Part {part_num_invalid}/{total_parts_invalid}" if total_parts_invalid > 1 else ""),
                    "description": current_desc_invalid,
                    "color": color_invalid,
                    "footer": {"text": footer_invalid} if footer_invalid else None, # Add footer only if applicable
                }
                # Remove footer key entirely if None to avoid errors
                if not footer_invalid: del embed["footer"]
                embeds_to_send.append(embed)
                current_desc_invalid = line
                part_num_invalid += 1
                footer_invalid = None # No footer for subsequent parts
            else:
                current_desc_invalid += line

        if current_desc_invalid:
             embed = {
                "title": f"Invalid Stock List ({len(invalid_stocks)} Total)" + (f" - Part {part_num_invalid}/{total_parts_invalid}" if total_parts_invalid > 1 else ""),
                "description": current_desc_invalid,
                "color": color_invalid,
             }
             if footer_invalid:
                  embed["footer"] = {"text": footer_invalid}
             embeds_to_send.append(embed)


    # --- Send the embed message(s) ---
    if not embeds_to_send:
        logging.warning("No embeds generated to send.")
        return

    logging.info(f"Sending {len(embeds_to_send)} embed(s) to Discord...")
    max_embeds_per_message = 10
    num_messages = (len(embeds_to_send) + max_embeds_per_message - 1) // max_embeds_per_message
    for i in range(num_messages):
        start_index = i * max_embeds_per_message
        end_index = start_index + max_embeds_per_message
        embed_chunk = embeds_to_send[start_index:end_index]
        if not embed_chunk: continue
        payload = {"username": username, "embeds": embed_chunk}
        try:
            response = requests.post(webhook_url, json=payload, timeout=15)
            response.raise_for_status()
            logging.info(f"Discord embed notification sent successfully (Message {i+1}/{num_messages}).")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Discord embed notification (Message {i+1}/{num_messages}): {e}")
            if e.response is not None: logging.error(f"Discord Response: {e.response.text}")
        except Exception as e:
             logging.error(f"Unexpected error sending Discord embed notification (Message {i+1}/{num_messages}): {e}")
        if num_messages > 1 and i < num_messages - 1: time.sleep(1)

# --- Main Validation Logic ---

def run_validation():
    """Loads stocks, validates keys, sends results, and saves valid list."""
    start_time = time.time() # Record start time
    logging.info("Starting ISIN validation process...")

    # 1. Get API Headers (includes getting/checking token)
    headers = get_api_headers()
    if not headers:
        logging.error("Cannot run validation. Failed to get API headers (check token).")
        # Instructions on how to get token are printed by get_access_token()
        return

    # 2. Load Stock List (Load from the original list for validation)
    original_stock_list_file = config.settings['paths']['stock_list_file']
    stocks = load_stock_list(original_stock_list_file) # Pass the specific file
    if not stocks:
        logging.error(f"Cannot run validation. Failed to load stock list '{original_stock_list_file}' or list is empty.")
        return

    logging.info(f"Found {len(stocks)} stocks to validate.")
    valid_count = 0
    invalid_count = 0
    results = {'valid': [], 'invalid': []}

    # 3. Iterate and Validate
    validation_loop_start_time = time.time() # Time just the loop if preferred
    for i, stock in enumerate(stocks):
        symbol = stock['symbol']
        isin = stock['isin']
        instrument_key = f"{EXCHANGE}_{INSTRUMENT_TYPE}|{isin}"

        is_valid = validate_instrument_key(instrument_key, headers)

        if is_valid:
            # Log in the desired format: Index. [STATUS] SYMBOL (ISIN)
            logging.info(f"{i+1}. [VALID] {symbol} ({isin})")
            valid_count += 1
            results['valid'].append({'symbol': symbol, 'isin': isin, 'instrument_key': instrument_key})
        else:
            # Log in the desired format: Index. [STATUS] SYMBOL (ISIN)
            logging.warning(f"{i+1}. [INVALID] {symbol} ({isin})") # Simplified status
            invalid_count += 1
            results['invalid'].append({'symbol': symbol, 'isin': isin, 'instrument_key': instrument_key})

        # Optional: Add a small delay between requests to avoid rate limiting
        time.sleep(0.2) # 200ms delay
    validation_loop_end_time = time.time() # End time for the loop

    # Calculate duration
    total_duration_seconds = validation_loop_end_time - validation_loop_start_time

    # 4. Print Summary & Log Invalid
    logging.info("-" * 50)
    logging.info("Validation Summary:")
    logging.info(f"Total Stocks Checked: {len(stocks)}")
    logging.info(f"Valid Instrument Keys: {valid_count}")
    logging.info(f"Invalid/Error Keys: {invalid_count}")
    logging.info(f"Validation Duration: {total_duration_seconds:.2f} seconds") # Log duration
    logging.info("-" * 50)

    if results['invalid']:
        logging.warning("Invalid ISINs/Symbols found:")
        for item in results['invalid']:
            logging.warning(f"  - {item['symbol']} ({item['isin']})")
        logging.warning("Please check these entries in your stock_list.csv")

    # 5. Save Valid List to File
    valid_stock_list_file = config.settings['paths']['valid_stock_list_file']
    if results['valid']:
        try:
            with open(valid_stock_list_file, mode='w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['symbol', 'isin']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                # Write only symbol and isin from the valid results
                writer.writerows([{'symbol': s['symbol'], 'isin': s['isin']} for s in results['valid']])
            logging.info(f"Saved {len(results['valid'])} valid stocks to '{valid_stock_list_file}'.")
        except IOError as e:
            logging.error(f"Failed to save valid stock list to '{valid_stock_list_file}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error saving valid stock list: {e}")
    else:
        logging.warning(f"No valid stocks found. '{valid_stock_list_file}' will not be created/updated.")
        # Optionally delete the file if it exists and no valid stocks are found
        if os.path.exists(valid_stock_list_file):
            try:
                os.remove(valid_stock_list_file)
                logging.info(f"Removed existing '{valid_stock_list_file}' as no valid stocks were found.")
            except OSError as e:
                logging.warning(f"Could not remove existing '{valid_stock_list_file}': {e}")


    # 6. Send Validation Results to Discord
    stocklist_webhook_url = config.get_discord_stocklist_webhook_url()
    send_stocklist_to_discord(
        results['valid'],
        results['invalid'],
        len(stocks),
        total_duration_seconds,
        stocklist_webhook_url
    )

    # Optionally save results to a file
    # output_file = os.path.join(config.settings['paths']['output_dir'], 'isin_validation_results.json')
    # try:
    #     with open(output_file, 'w') as f:
    #         json.dump(results, f, indent=2)
    #     logging.info(f"Validation results saved to {output_file}")
    # except Exception as e:
    #     logging.error(f"Failed to save validation results: {e}")


if __name__ == "__main__":
    # Ensure logging is set up via helpers
    try:
        # This ensures the logging config in helpers runs
        import utils.helpers
    except ImportError as e:
         print(f"Error importing utils.helpers: {e}. Ensure script is run from project root or PYTHONPATH is set.")
         sys.exit(1)

    run_validation()
