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

def delete_old_reports_in_directory(directory):
    """
    Deletes report files in the given directory that are older than the last 5 trading days.
    Expected filename patterns: success_report_YYYYMMDD.html or failure_report_YYYYMMDD.html.
    """
    if not os.path.isdir(directory):
        logging.info(f"Directory '{directory}' does not exist. No reports to delete.")
        return
    try:
        # Process Success Reports
        success_files = [f for f in os.listdir(directory) if f.startswith('success_report_') and f.endswith('.html')]
        success_by_date = {}
        for filename in success_files:
            try:
                date_str = filename.split('_')[2].split('.')[0]  # e.g. "20250430"
                success_by_date.setdefault(date_str, []).append(filename)
            except Exception as e:
                logging.warning(f"Could not parse trading date from success report file {filename}: {e}")
        sorted_success_dates = sorted(success_by_date.keys(), reverse=True)
        keep_success = set(sorted_success_dates[:5])
        files_to_delete = []
        for date_str, files in success_by_date.items():
            if date_str not in keep_success:
                for f in files:
                    files_to_delete.append(os.path.join(directory, f))
        
        # Process Failure Reports
        failure_files = [f for f in os.listdir(directory) if f.startswith('failure_report_') and f.endswith('.html')]
        failure_by_date = {}
        for filename in failure_files:
            try:
                date_str = filename.split('_')[2].split('.')[0]
                failure_by_date.setdefault(date_str, []).append(filename)
            except Exception as e:
                logging.warning(f"Could not parse trading date from failure report file {filename}: {e}")
        sorted_failure_dates = sorted(failure_by_date.keys(), reverse=True)
        keep_failure = set(sorted_failure_dates[:5])
        for date_str, files in failure_by_date.items():
            if date_str not in keep_failure:
                for f in files:
                    files_to_delete.append(os.path.join(directory, f))
        
        if files_to_delete:
            logging.info(f"Found {len(files_to_delete)} report file(s) in '{directory}' older than the last 5 trading days. Deleting them.")
            for f_path in files_to_delete:
                try:
                    os.remove(f_path)
                    logging.info(f"Deleted old report: {f_path}")
                except OSError as e:
                    logging.error(f"Error deleting report file {f_path}: {e}")
        else:
            logging.info(f"No old report files to delete in '{directory}' beyond the last 5 trading days.")
    except Exception as e:
        logging.error(f"An error occurred during deletion of reports in '{directory}': {e}")

def manage_reports():
    report_dir = config.settings['paths']['report_dir']
    # Delete old reports in the reports folder
    delete_old_reports_in_directory(report_dir)
    # Also, delete old reports in the docs folder
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    delete_old_reports_in_directory(docs_dir)

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
