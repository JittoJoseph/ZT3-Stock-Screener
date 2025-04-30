import sys
import os
from datetime import datetime, timedelta
import time

# Ensure project root is in path (if running main.py directly from root)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import project modules
import config
from utils.helpers import logging, load_stock_list, get_report_filename, manage_reports
from data_fetcher import fetch_historical_data, get_access_token
from screener_logic import apply_screening, TOTAL_RULES # Import TOTAL_RULES
from report_generator import generate_html_report
from failure_report import generate_failure_report # Import the new function
from discord_notifier import send_discord_notification # Ensure this import is correct

# Constants for data fetching
FETCH_INTERVAL = 'day' # Daily candles
# Calculate date range needed (lookback + buffer for calculations)
# Ensure buffer is sufficient for 50-day EMA/Avg Vol
LOOKBACK_DAYS = config.settings['screener']['lookback_period'] + 40 # Keep buffer, lookback_period is now 50

# Constants for instrument key construction (assuming NSE Equity)
EXCHANGE = "NSE"
INSTRUMENT_TYPE = "EQ"

def run_screener():
    """Main function to run the daily breakout screener."""
    overall_start_time = time.time() # Start time for the whole process
    logging.info("="*50)
    logging.info("Starting ZT-3 Daily Breakout Screener")
    logging.info("="*50)

    # 0. Initial Checks & Setup
    # Ensure token exists before starting loop (get_access_token handles instructions if missing)
    if not get_access_token():
        logging.error("Screener cannot run without a valid access token. Exiting.")
        return

    # Clean up old reports before starting
    manage_reports()

    # 1. Load VALIDATED Stock List
    valid_stock_list_file = config.settings['paths']['valid_stock_list_file']
    logging.info(f"Attempting to load validated stock list from: {valid_stock_list_file}")

    if not os.path.exists(valid_stock_list_file):
        logging.error(f"Validated stock list '{valid_stock_list_file}' not found.")
        logging.error("Please run the validation script (utils/validate_isins.py) first to generate the list.")
        return # Exit if the validated list doesn't exist

    stocks_to_scan = load_stock_list(valid_stock_list_file) # Load the validated list
    if not stocks_to_scan:
        logging.error(f"No stocks loaded from '{valid_stock_list_file}'. Exiting.")
        # This might happen if the file exists but is empty or malformed.
        return
    logging.info(f"Loaded {len(stocks_to_scan)} stocks from validated list for screening.")

    # 2. Define Date Range for Data Fetching
    to_date_str = datetime.now().strftime('%Y-%m-%d')
    from_date_str = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')

    # 3. Iterate, Fetch, Screen
    logging.info("--- Starting Data Fetching and Screening ---")
    screening_start_time = time.time() # Start time for the screening loop
    all_screening_results = [] # Store results for ALL stocks
    fetch_errors = 0
    total_stocks = len(stocks_to_scan)

    for i, stock in enumerate(stocks_to_scan):
        symbol = stock['symbol']
        isin = stock['isin']
        instrument_key = f"{EXCHANGE}_{INSTRUMENT_TYPE}|{isin}"
        logging.info(f"--- Processing [{i+1}/{total_stocks}]: {symbol} ({instrument_key}) ---")

        # Fetch data
        try:
            historical_df = fetch_historical_data(
                instrument_key=instrument_key,
                interval=FETCH_INTERVAL,
                to_date=to_date_str,
                from_date=from_date_str
            )
        except Exception as e:
            logging.error(f"[{symbol}] Unhandled exception during data fetch: {e}")
            historical_df = None
            fetch_errors += 1

        # Apply screening logic (even if data fetch failed, apply_screening handles None)
        try:
            # apply_screening now returns a detailed dict for every stock processed
            result_details = apply_screening(historical_df, symbol)
            if result_details: # Ensure apply_screening didn't return None due to internal error
                 # Add ISIN back to the result dictionary
                 result_details['isin'] = isin
                 all_screening_results.append(result_details)
            else:
                 # Log if apply_screening itself failed unexpectedly, though it should return a dict
                 logging.error(f"[{symbol}] apply_screening returned None unexpectedly.")

        except Exception as e:
            logging.error(f"[{symbol}] Unhandled exception during screening: {e}")
            # Optionally add a placeholder result indicating screening error
            all_screening_results.append({
                'symbol': symbol,
                'isin': isin,
                'failed_overall': True,
                'reason': f'Screening Error: {e}',
                'rules_passed_count': 0
            })


        # Add a small delay between API calls to avoid rate limiting
        time.sleep(0.3) # 300ms delay

    screening_end_time = time.time() # End time for the screening loop
    screening_duration_seconds = screening_end_time - screening_start_time

    # Filter successful stocks from all results
    shortlisted_stocks = [res for res in all_screening_results if not res.get('failed_overall', True)]

    logging.info("="*50)
    logging.info("Screening Complete")
    logging.info(f"Total Stocks Processed: {total_stocks}")
    logging.info(f"Stocks Passing Criteria ({TOTAL_RULES} rules): {len(shortlisted_stocks)}") # Use TOTAL_RULES
    if fetch_errors > 0:
        logging.warning(f"Data Fetching Errors Encountered: {fetch_errors}")
    logging.info(f"Screening Duration: {screening_duration_seconds:.2f} seconds")
    logging.info("="*50)

    # 4. Generate Reports
    report_filename = None
    failure_report_filename = None

    if shortlisted_stocks:
        report_filename = get_report_filename(prefix="success_report_")
        generate_html_report(shortlisted_stocks, report_filename)
        logging.info(f"Success report generated: {report_filename}")
    else:
        logging.info("No stocks passed screening. Skipping success report generation.")

    # Generate failure analysis report (shows stocks passing >= TOTAL_RULES - 1 rules by default)
    logging.info("Attempting to generate failure analysis report...")
    temp_failure_filename = get_report_filename(prefix="failure_analysis_")
    # Pass None for min_rules_passed to use the default (TOTAL_RULES - 1)
    failure_report_generated = generate_failure_report(
        all_screening_results,
        temp_failure_filename,
        min_rules_passed=None # Use default logic within the function
    )
    if failure_report_generated:
        failure_report_filename = temp_failure_filename
        logging.info(f"Failure analysis report generated: {failure_report_filename}")
    else:
        failure_report_filename = None

    # 5. Send Discord Notification
    send_discord_notification(
        shortlisted_stocks,
        report_filename=report_filename, # Will be None if no stocks passed
        failure_report_filename=failure_report_filename, # Will be None if generation failed
        duration_seconds=screening_duration_seconds
        # Consider passing TOTAL_RULES if needed in the notification text
    )

    overall_end_time = time.time() # End time for the whole process
    overall_duration_seconds = overall_end_time - overall_start_time
    logging.info(f"Total Execution Time: {overall_duration_seconds:.2f} seconds")
    logging.info("Screener finished.")
    logging.info("="*50)


if __name__ == "__main__":
    run_screener()
