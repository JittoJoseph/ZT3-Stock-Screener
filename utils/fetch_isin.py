import csv
import os
from nseinfopackage import nseinfo
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define file paths relative to the script location
script_dir = os.path.dirname(__file__)
project_root = os.path.dirname(script_dir)
input_csv_path = os.path.join(project_root, 'symbols_only.csv')
output_csv_path = os.path.join(project_root, 'stock_list.csv')
missing_csv_path = os.path.join(project_root, 'missing_symbols.csv') # Path for missing symbols

def read_symbols(filepath):
    """Reads symbols from the input CSV file."""
    symbols = []
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            try:
                header = next(reader) # Skip header row
                if header != ['symbol']:
                     logging.warning(f"Input CSV header is not ['symbol']: {header}")
            except StopIteration:
                logging.error(f"Input CSV file {filepath} is empty or has no header.")
                return []
            for row in reader:
                if row: # Ensure row is not empty
                    symbols.append(row[0].strip())
        logging.info(f"Read {len(symbols)} symbols from {filepath}")
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at {filepath}")
    except Exception as e:
        logging.error(f"Error reading symbols from {filepath}: {e}")
    return symbols

def write_stock_list(filepath, data):
    """Writes symbol-ISIN pairs from a dictionary to the output CSV file and returns symbols written."""
    # Expect data to be a dictionary {symbol: isin}
    if not isinstance(data, dict):
        logging.error(f"Expected a dictionary for writing, but got {type(data)}. Cannot write to CSV.")
        return set() # Return empty set on error

    written_symbols = set()
    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['symbol', 'isin']) # Write header
            valid_entries = 0
            # Iterate through the dictionary items
            for symbol, isin in data.items():
                # Check if ISIN is valid (already checked in main, but double-check)
                if symbol and isin and isin != '-':
                    writer.writerow([symbol, isin])
                    written_symbols.add(symbol)
                    valid_entries += 1
                else:
                    # This case should ideally not happen if filtering is done in main
                    logging.warning(f"Skipping entry with invalid symbol/ISIN: Symbol='{symbol}', ISIN='{isin}'")

            logging.info(f"Wrote {valid_entries} symbol-ISIN pairs to {filepath}")
    except Exception as e:
        logging.error(f"Error writing to {filepath}: {e}")

    return written_symbols # Return the set of symbols that were successfully written

def write_missing_symbols(filepath, missing_symbols):
    """Writes missing symbols to a CSV file."""
    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['symbol']) # Write header
            for symbol in sorted(list(missing_symbols)): # Write sorted list
                 writer.writerow([symbol])
            logging.info(f"Wrote {len(missing_symbols)} missing symbols to {filepath}")
    except Exception as e:
        logging.error(f"Error writing missing symbols to {filepath}: {e}")

def main():
    """Main function to fetch ISINs and update the stock list."""
    logging.info("Starting ISIN fetch process...")
    original_symbols = read_symbols(input_csv_path)
    symbols_set = set(original_symbols) # Use a set for efficient lookup

    if not original_symbols:
        logging.error("No symbols read from input file. Exiting.")
        return

    logging.info(f"Fetching ISIN numbers for {len(original_symbols)} symbols...")
    isin_list = [] # Initialize as empty list
    try:
        # Fetch ISINs. Assume it returns a list of ISIN strings.
        # The library might print "Error! Some input values are incorrect or not found!"
        isin_list = nseinfo.getISINNumbers(original_symbols)

        # Check if the returned data is actually a list
        if isinstance(isin_list, list):
            logging.info(f"nseinfo.getISINNumbers returned a list with {len(isin_list)} items.")
            # Check if length matches input symbols length
            if len(isin_list) != len(original_symbols):
                 logging.warning(f"Mismatch in length: Input symbols ({len(original_symbols)}), Received ISINs ({len(isin_list)}). Some symbols might not have ISINs or failed.")
        else:
            logging.error(f"nseinfo.getISINNumbers returned an unexpected type: {type(isin_list)}. Value: {isin_list}")
            isin_list = [] # Reset to empty list if type is wrong

    except Exception as e:
        logging.error(f"Error calling nseinfo.getISINNumbers: {e}")
        # isin_list remains an empty list

    # Create a dictionary mapping symbols to ISINs
    symbol_isin_map = {}
    found_symbols = set()
    # Iterate through the original symbols list and map to the received ISIN list
    # Use the minimum length to avoid index errors if lists differ in size
    num_pairs_to_process = min(len(original_symbols), len(isin_list))
    for i in range(num_pairs_to_process):
        symbol = original_symbols[i]
        isin = isin_list[i]
        # Validate the fetched ISIN before adding to the map
        if isinstance(isin, str) and isin and isin != '-':
            symbol_isin_map[symbol] = isin
            found_symbols.add(symbol) # Track symbols for which we got a valid ISIN
        else:
            logging.warning(f"Invalid or missing ISIN ('{isin}') received for symbol: {symbol}")

    # Write the found ISINs
    written_symbols = set()
    if symbol_isin_map:
        written_symbols = write_stock_list(output_csv_path, symbol_isin_map)
    else:
        logging.warning("No valid symbol-ISIN pairs were constructed. Output file might be empty or incomplete.")
        # Ensure the output file exists with headers even if no data
        write_stock_list(output_csv_path, {})

    # Determine missing symbols
    # Missing = All original symbols - symbols successfully written to stock_list.csv
    missing_symbols = symbols_set - written_symbols
    logging.info(f"Identified {len(missing_symbols)} symbols missing ISINs.")

    # Write missing symbols to a separate file
    if missing_symbols:
        write_missing_symbols(missing_csv_path, missing_symbols)
    else:
        logging.info("No missing symbols found. All symbols processed successfully.")
        # If the missing file exists from a previous run, remove it or clear it
        if os.path.exists(missing_csv_path):
             write_missing_symbols(missing_csv_path, set()) # Write empty file

    logging.info("ISIN fetch process finished.")

if __name__ == "__main__":
    main()
