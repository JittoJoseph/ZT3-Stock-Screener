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

def load_stock_list():
    """Loads the stock list from the CSV file specified in config."""
    stock_file = config.settings['paths']['stock_list_file']
    stocks = []
    try:
        with open(stock_file, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if 'symbol' not in reader.fieldnames or 'isin' not in reader.fieldnames:
                 logging.error(f"CSV file '{stock_file}' must contain 'symbol' and 'isin' columns.")
                 return []
            for row in reader:
                # Basic validation: ensure symbol and isin are present
                if row.get('symbol') and row.get('isin'):
                    # Standardize: Uppercase symbol, ensure no leading/trailing spaces
                    symbol = row['symbol'].strip().upper()
                    isin = row['isin'].strip()
                    stocks.append({'symbol': symbol, 'isin': isin})
                else:
                    logging.warning(f"Skipping row due to missing symbol or isin: {row}")
        logging.info(f"Loaded {len(stocks)} stocks from {stock_file}")
        return stocks
    except FileNotFoundError:
        logging.error(f"Stock list file not found: {stock_file}")
        return []
    except Exception as e:
        logging.error(f"Error reading stock list file {stock_file}: {e}")
        return []

def manage_reports():
    """Ensures only the latest MAX_REPORTS HTML files are kept in the report directory."""
    report_dir = config.settings['paths']['report_dir']
    max_reports = config.settings['reporting']['max_reports']

    # Ensure report directory exists
    os.makedirs(report_dir, exist_ok=True)

    try:
        # Find all HTML files in the report directory
        # Use pattern matching the generated report filenames
        report_pattern = os.path.join(report_dir, 'breakout_report_*.html')
        report_files = glob.glob(report_pattern)

        if len(report_files) <= max_reports:
            logging.info(f"Report count ({len(report_files)}) is within the limit ({max_reports}). No cleanup needed.")
            return

        # Sort files by modification time (oldest first)
        report_files.sort(key=os.path.getmtime)

        # Calculate how many files to delete
        files_to_delete_count = len(report_files) - max_reports
        files_to_delete = report_files[:files_to_delete_count]

        # Delete the oldest files
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                logging.info(f"Deleted old report: {os.path.basename(file_path)}")
            except OSError as e:
                logging.error(f"Error deleting report file {file_path}: {e}")

    except Exception as e:
        logging.error(f"Error managing report files in {report_dir}: {e}")

def get_report_filename():
    """Generates a filename for the HTML report based on the current date."""
    report_dir = config.settings['paths']['report_dir']
    today_str = datetime.now().strftime('%Y-%m-%d_%H%M%S') # Add time to avoid overwrite if run multiple times a day
    return os.path.join(report_dir, f"breakout_report_{today_str}.html")


# Example usage (for testing later)
if __name__ == '__main__':
    logging.info("Testing utils.helpers module...")

    # Test loading stock list
    stocks = load_stock_list()
    if stocks:
        logging.info(f"First few loaded stocks: {stocks[:3]}")
    else:
        logging.warning("Stock list loading test returned no stocks.")

    # Test report management (create some dummy files first if needed)
    logging.info("Testing report management...")
    # Example: Create dummy files for testing
    # report_dir = config.settings['paths']['report_dir']
    # os.makedirs(report_dir, exist_ok=True)
    # from datetime import timedelta
    # for i in range(config.settings['reporting']['max_reports'] + 2):
    #     # Use the actual filename pattern
    #     dummy_time = datetime.now() - timedelta(days=i)
    #     dummy_file = os.path.join(report_dir, f'breakout_report_{dummy_time.strftime("%Y-%m-%d_%H%M%S")}.html')
    #     try:
    #         with open(dummy_file, 'w') as f:
    #             f.write('test')
    #         # Adjust modification time slightly to ensure order if needed (utime might be better)
    #         mod_time = datetime.now() - timedelta(days=i)
    #         os.utime(dummy_file, (mod_time.timestamp(), mod_time.timestamp()))
    #         logging.info(f"Created dummy file: {dummy_file}")
    #     except Exception as e:
    #         logging.error(f"Failed to create dummy file {dummy_file}: {e}")


    manage_reports()
    logging.info(f"Report filename for run: {get_report_filename()}")
    logging.info("Utils.helpers module test finished.")
