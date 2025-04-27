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

import requests
from datetime import datetime, timedelta
import time

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

# --- Helper Function ---

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

# --- Main Validation Logic ---

def run_validation():
    """Loads stocks and validates their instrument keys."""
    logging.info("Starting ISIN validation process...")

    # 1. Get API Headers (includes getting/checking token)
    headers = get_api_headers()
    if not headers:
        logging.error("Cannot run validation. Failed to get API headers (check token).")
        # Instructions on how to get token are printed by get_access_token()
        return

    # 2. Load Stock List
    stocks = load_stock_list()
    if not stocks:
        logging.error("Cannot run validation. Failed to load stock list or list is empty.")
        return

    logging.info(f"Found {len(stocks)} stocks to validate.")
    valid_count = 0
    invalid_count = 0
    results = {'valid': [], 'invalid': []}

    # 3. Iterate and Validate
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

    # 4. Print Summary
    logging.info("-" * 50)
    logging.info("Validation Summary:")
    logging.info(f"Total Stocks Checked: {len(stocks)}")
    logging.info(f"Valid Instrument Keys: {valid_count}")
    logging.info(f"Invalid/Error Keys: {invalid_count}")
    logging.info("-" * 50)

    if results['invalid']:
        logging.warning("Invalid ISINs/Symbols found:")
        for item in results['invalid']:
            logging.warning(f"  - {item['symbol']} ({item['isin']})")
        logging.warning("Please check these entries in your stock_list.csv")

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
