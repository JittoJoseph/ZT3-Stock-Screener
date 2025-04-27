import os
from datetime import datetime
import config
from utils.helpers import logging, get_report_filename, manage_reports

def generate_html_report(shortlisted_stocks, filename):
    """
    Generates an HTML report from the list of shortlisted stocks.

    Args:
        shortlisted_stocks (list): A list of dictionaries, where each dict
                                   represents a stock that passed screening.
                                   Expected keys: 'symbol', 'isin', 'close',
                                   'breakout_level', 'volume_surge_pct', 'ema_20',
                                   'timestamp'.
        filename (str): The full path to save the HTML report file.
    """
    if not shortlisted_stocks:
        logging.info("No stocks passed screening. HTML report will not be generated.")
        # Optionally, generate an empty report or just skip
        # For now, we skip generation if the list is empty.
        return

    # Ensure the report directory exists
    report_dir = os.path.dirname(filename)
    os.makedirs(report_dir, exist_ok=True)

    # Get screening date from the first stock's timestamp (assuming all are from the same day)
    screening_date_str = "N/A"
    if shortlisted_stocks and 'timestamp' in shortlisted_stocks[0]:
         # Format the date part only
         screening_date_str = shortlisted_stocks[0]['timestamp'].strftime('%Y-%m-%d')

    # Start HTML content
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Breakout Screener Report - {screening_date_str}</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        h1 {{ text-align: center; color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #e2e2e2; }}
        .footer {{ margin-top: 20px; font-size: 0.8em; text-align: center; color: #777; }}
    </style>
</head>
<body>
    <h1>Daily Breakout Screener Report</h1>
    <p style="text-align: center;">Screening Date: {screening_date_str}</p>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Symbol</th>
                <th>ISIN</th>
                <th>Close Price (₹)</th>
                <th>Breakout Level (₹)</th>
                <th>Volume Surge (%)</th>
                <th>EMA(20) (₹)</th>
            </tr>
        </thead>
        <tbody>
"""

    # Add rows for each shortlisted stock
    for i, stock in enumerate(shortlisted_stocks):
        # Add 'isin' if available, otherwise use placeholder
        isin_val = stock.get('isin', 'N/A')
        html_content += f"""
            <tr>
                <td>{i+1}</td>
                <td>{stock.get('symbol', 'N/A')}</td>
                <td>{isin_val}</td>
                <td>{stock.get('close', 'N/A'):.2f}</td>
                <td>{stock.get('breakout_level', 'N/A'):.2f}</td>
                <td>{stock.get('volume_surge_pct', 'N/A'):.2f}%</td>
                <td>{stock.get('ema_20', 'N/A'):.2f}</td>
            </tr>
"""

    # Close HTML content
    html_content += """
        </tbody>
    </table>
    <div class="footer">
        Generated on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
    </div>
</body>
</html>
"""

    # Write to file
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"HTML report generated successfully: {filename}")
    except IOError as e:
        logging.error(f"Error writing HTML report to {filename}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during HTML report generation: {e}")


# Example usage (for testing later)
if __name__ == '__main__':
    logging.info("Testing report_generator module...")

    # Dummy data matching the expected output of screener_logic
    dummy_stocks = [
        {'symbol': 'RELIANCE', 'isin': 'INE002A01018', 'close': 2880.50, 'breakout_level': 2850.00, 'volume_surge_pct': 75.5, 'ema_20': 2800.10, 'timestamp': datetime.now()},
        {'symbol': 'TCS', 'isin': 'INE467B01029', 'close': 3465.20, 'breakout_level': 3400.00, 'volume_surge_pct': 55.1, 'ema_20': 3350.50, 'timestamp': datetime.now()},
        {'symbol': 'HDFCBANK', 'isin': 'INE040A01034', 'close': 1622.80, 'breakout_level': 1600.00, 'volume_surge_pct': 110.0, 'ema_20': 1580.90, 'timestamp': datetime.now()},
    ]

    # Get filename using the helper function
    report_file = get_report_filename()

    # Generate the report
    generate_html_report(dummy_stocks, report_file)

    # Test report management (should delete older reports if > MAX_REPORTS exist)
    logging.info("Running report management after generation...")
    manage_reports()

    logging.info("Report_generator module test finished.")
    # Check the outputs/reports directory for the generated HTML file.
