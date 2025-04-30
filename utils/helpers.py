import os
import glob
import csv
import config
import logging
from datetime import datetime

# Basic Logging Setup
# Ensure output dir exists before setting up logging
os.makedirs(config.settings['paths']['output_dir'], exist_ok=True)
log_file_path = os.path.join(config.settings['paths']['output_dir'], 'screener.log')

# Keep the file handler format detailed for debugging purposes
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
# Make the console handler format simpler
console_formatter = logging.Formatter('%(message)s')

# Create handlers
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    # Remove default handlers added by basicConfig if any
    handlers=[]
)

# Add our custom handlers to the root logger
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ... rest of the existing code from the old utils.py ...

def load_stock_list(filename=None):
    """
    Loads stock symbols and ISINs from a specified CSV file.

    Args:
        filename (str, optional): The path to the CSV file.
                                  Defaults to config.settings['paths']['stock_list_file'].

    Returns:
        list: A list of dictionaries, each containing 'symbol' and 'isin',
              or an empty list if the file is not found or empty.
    """
    if filename is None:
        filename = config.settings['paths']['stock_list_file'] # Default to original list

    stocks = []
    try:
        # Ensure the file exists before trying to open it
        if not os.path.exists(filename):
            logging.error(f"Stock list file not found: {filename}")
            return []

        with open(filename, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            # Check if header exists and has the required columns
            if not reader.fieldnames or 'symbol' not in reader.fieldnames or 'isin' not in reader.fieldnames:
                logging.error(f"Stock list file '{filename}' is missing header or required columns ('symbol', 'isin').")
                return []

            for row in reader:
                # Basic validation: ensure symbol and isin are present and not empty
                symbol = row.get('symbol', '').strip()
                isin = row.get('isin', '').strip()
                if symbol and isin:
                    stocks.append({'symbol': symbol, 'isin': isin})
                else:
                    logging.warning(f"Skipping row in '{filename}' due to missing symbol or ISIN: {row}")

        if not stocks:
            logging.warning(f"No valid stock entries found in {filename}.")

    except FileNotFoundError:
        # This case is already handled by os.path.exists, but kept for robustness
        logging.error(f"Stock list file not found: {filename}")
    except Exception as e:
        logging.error(f"Error reading stock list file {filename}: {e}")
        return [] # Return empty list on error

    return stocks

def manage_reports():
    report_dir = config.settings['paths']['report_dir']
    # max_reports = config.settings['reporting']['max_reports'] # No longer used directly

    if not os.path.isdir(report_dir):
        logging.info(f"Report directory '{report_dir}' does not exist. No reports to manage.")
        return

    try:
        all_files = [os.path.join(report_dir, f) for f in os.listdir(report_dir) if f.endswith('.html')]

        success_reports = [f for f in all_files if os.path.basename(f).startswith('success_report_')]
        failure_reports = [f for f in all_files if os.path.basename(f).startswith('failure_analysis_')]

        files_to_delete = []

        # Process success reports
        if success_reports:
            success_reports.sort(key=os.path.getmtime, reverse=True) # Sort newest first
            files_to_delete.extend(success_reports[1:]) # Add all except the newest one to delete list

        # Process failure reports
        if failure_reports:
            failure_reports.sort(key=os.path.getmtime, reverse=True) # Sort newest first
            files_to_delete.extend(failure_reports[1:]) # Add all except the newest one to delete list

        if not files_to_delete:
            logging.info("No old reports found to delete.")
            return

        logging.info(f"Found {len(files_to_delete)} old report(s) to delete.")
        deleted_count = 0
        for f_path in files_to_delete:
            try:
                os.remove(f_path)
                logging.info(f"Deleted old report: {os.path.basename(f_path)}")
                deleted_count += 1
            except OSError as e:
                logging.error(f"Error deleting report file {f_path}: {e}")

        logging.info(f"Report cleanup complete. Deleted {deleted_count} old report(s).")

    except Exception as e:
        logging.error(f"An error occurred during report management: {e}")

def get_report_filename(prefix="report_", use_date_only=False, report_date=None):
    """
    Returns a full path filename for a report.
    If use_date_only is True, includes only the date (YYYYMMDD) in the filename;
    otherwise, includes date and time (YYYYMMDD_HHMMSS).
    If report_date (a datetime object) is provided, it is used instead of datetime.now().
    For example, if prefix is "success_report_":
       use_date_only True -> success_report_20250430.html
       use_date_only False -> success_report_20250430_211959.html
    """
    now = report_date if report_date is not None else datetime.now()
    if use_date_only:
        date_str = now.strftime("%Y%m%d")
    else:
        date_str = now.strftime("%Y%m%d_%H%M%S")
    report_dir = config.settings['paths']['report_dir']
    # Ensure report directory exists
    os.makedirs(report_dir, exist_ok=True)
    return os.path.join(report_dir, f"{prefix}{date_str}.html")


# Example usage (for testing later)
if __name__ == '__main__':
    logging.info("Testing utils.helpers module...")

    # Test loading stock list
    stocks = load_stock_list()
    if stocks:
        logging.info(f"First few loaded stocks: {stocks[:3]}")
    else:
        logging.warning("Stock list loading test returned no stocks.")

    manage_reports()
    logging.info(f"Report filename for run: {get_report_filename()}")
    logging.info("Utils.helpers module test finished.")
