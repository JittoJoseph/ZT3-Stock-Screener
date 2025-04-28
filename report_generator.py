import os
from datetime import datetime
import math
import numpy as np # Import numpy to check its types
import config
from utils.helpers import logging, get_report_filename, manage_reports

def generate_html_report(shortlisted_stocks, filename):
    if not shortlisted_stocks:
        logging.info("No stocks passed screening. HTML report will not be generated.")
        return

    report_dir = os.path.dirname(filename)
    os.makedirs(report_dir, exist_ok=True)

    screening_date_str = "N/A"
    if shortlisted_stocks and 'timestamp' in shortlisted_stocks[0]:
         screening_date_str = shortlisted_stocks[0]['timestamp'].strftime('%Y-%m-%d')

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Breakout Screener Report - {screening_date_str}</title>
    <style>
        /* Mobile First Styles */
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            color: #212529;
            font-size: 14px;
        }}
        /* ... existing container, h1, p.subtitle styles ... */
        .container {{
            width: 100%;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 15px;
            box-sizing: border-box;
            box-shadow: none;
            border-radius: 0;
        }}
        h1 {{
            text-align: center;
            color: #007bff;
            margin-bottom: 5px;
            font-size: 1.5em;
        }}
        p.subtitle {{
            text-align: center;
            color: #6c757d;
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 1em;
        }}
        .table-container {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin: 0 -15px;
            padding: 0 15px;
        }}
        table {{
            width: 100%;
            min-width: 600px;
            border-collapse: collapse;
            margin-top: 15px;
            /* font-size is now controlled by th, td */
        }}
        th, td {{
            border: 1px solid #dee2e6;
            padding: 12px 15px; /* Slightly larger padding */
            text-align: left;
            vertical-align: middle;
            white-space: nowrap;
            font-size: 1.5em; /* Significantly larger font size for table cells on mobile */
        }}
        /* ... existing th, tr:nth-child(even) styles ... */
        th {{
            background-color: #e9ecef;
            color: #495057;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: sticky;
            top: 0;
            z-index: 1;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}

        /* ... existing td alignment styles ... */
        td:nth-child(4),
        td:nth-child(5),
        td:nth-child(7),
        td:nth-child(8)
        {{
            text-align: right;
        }}
        td:nth-child(6)
        {{
             text-align: right;
        }}
        /* ... existing footer styles ... */
        .footer {{
            margin-top: 20px;
            font-size: 0.8em;
            text-align: center;
            color: #6c757d;
            padding: 10px 15px;
        }}

        /* Desktop Styles (apply overrides for larger screens) */
        @media (min-width: 768px) {{
            /* ... existing desktop body, container, h1, p.subtitle styles ... */
            body {{
                padding: 20px;
                font-size: 16px;
            }}
            .container {{
                max-width: 1200px;
                margin: 20px auto;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                font-size: 2em;
                margin-bottom: 10px;
            }}
            p.subtitle {{
                font-size: 1.1em;
                margin-bottom: 30px;
            }}
            /* ... existing desktop table-container styles ... */
            .table-container {{
                 margin: 0;
                 padding: 0;
            }}
            table {{
                /* font-size is now controlled by th, td */
                min-width: auto;
            }}
            /* ... existing desktop th, td, tr:hover, footer styles ... */
            th, td {{
                padding: 12px 15px;
                white-space: normal;
                font-size: 0.95em; /* Restore desktop table font size */
            }}
            tr:hover {{
                background-color: #e2e6ea;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 0.9em;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Daily Breakout Screener Report</h1>
        <p class="subtitle">Screening Date: {screening_date_str}</p>

        <div class="table-container">
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
                        <th>Volume</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, stock in enumerate(shortlisted_stocks):
        volume_val = stock.get('volume')

        isin_val = stock.get('isin', 'N/A')

        # Refined volume formatting with explicit numpy type check
        volume_str = 'N/A'
        # Check for standard int/float AND numpy int/float types
        if isinstance(volume_val, (int, float, np.integer, np.floating)) and not math.isnan(volume_val):
            try:
                # Convert to standard Python int first to ensure comma formatting works
                volume_int = int(volume_val)
                volume_str = f"{volume_int:,}"
            except (ValueError, TypeError) as fmt_err:
                logging.error(f"  Error formatting numeric volume '{volume_val}': {fmt_err}")
                volume_str = 'N/A' # Fallback if conversion/formatting fails
        elif isinstance(volume_val, str) and volume_val.isdigit():
             try:
                 volume_str = f"{int(volume_val):,}"
             except (ValueError, TypeError) as fmt_err:
                 logging.error(f"  Error formatting string digit volume '{volume_val}': {fmt_err}")
                 volume_str = 'N/A'
        else:
            # Log if the value is neither a recognized number nor a string digit
            logging.debug(f"  Volume value '{volume_val}' is not a recognized number or string digit. Displaying N/A.")

        # Construct the table row string explicitly
        row_html = "<tr>"
        row_html += f"<td>{i+1}</td>"
        row_html += f"<td>{stock.get('symbol', 'N/A')}</td>"
        row_html += f"<td>{isin_val}</td>"
        row_html += f"<td>{stock.get('close', 0.0):.2f}</td>"
        row_html += f"<td>{stock.get('breakout_level', 0.0):.2f}</td>"
        row_html += f"<td>{stock.get('volume_surge_pct', 0.0):.2f}%</td>"
        row_html += f"<td>{stock.get('ema_20', 0.0):.2f}</td>"
        row_html += f"<td>{volume_str}</td>" # Use the formatted string
        row_html += "</tr>\n"

        html_content += row_html # Append the constructed row

    html_content += """
                </tbody>
            </table>
        </div>
        <div class="footer">
            Generated on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </div>
    </div>
</body>
</html>
"""

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"HTML report generated successfully: {filename}")
    except IOError as e:
        logging.error(f"Error writing HTML report to {filename}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during HTML report generation: {e}")

if __name__ == '__main__':
    logging.info("Testing report_generator module...")

    dummy_stocks = [
        {'symbol': 'RELIANCE', 'isin': 'INE002A01018', 'close': 2880.50, 'breakout_level': 2850.00, 'volume_surge_pct': 75.5, 'ema_20': 2800.10, 'timestamp': datetime.now(), 'volume': 1234567},
        {'symbol': 'TCS', 'isin': 'INE467B01029', 'close': 3465.20, 'breakout_level': 3400.00, 'volume_surge_pct': 55.1, 'ema_20': 3350.50, 'timestamp': datetime.now(), 'volume': 890123.0}, # Test float volume
        {'symbol': 'HDFCBANK', 'isin': 'INE040A01034', 'close': 1622.80, 'breakout_level': 1600.00, 'volume_surge_pct': 110.0, 'ema_20': 1580.90, 'timestamp': datetime.now(), 'volume': 2500000},
        {'symbol': 'INFY', 'isin': 'INE009A01021', 'close': 1500.00, 'breakout_level': 1480.00, 'volume_surge_pct': 90.0, 'ema_20': 1450.00, 'timestamp': datetime.now(), 'volume': None}, # Test None volume
        {'symbol': 'WIPRO', 'isin': 'INE075A01022', 'close': 450.00, 'breakout_level': 440.00, 'volume_surge_pct': 120.0, 'ema_20': 430.00, 'timestamp': datetime.now(), 'volume': float('nan')}, # Test NaN volume
        {'symbol': 'TEST', 'isin': 'INE123X01011', 'close': 100.00, 'breakout_level': 95.00, 'volume_surge_pct': 50.0, 'ema_20': 98.00, 'timestamp': datetime.now(), 'volume': 'Invalid'}, # Test invalid string volume
    ]

    report_file = get_report_filename()
    generate_html_report(dummy_stocks, report_file)
    logging.info("Running report management after generation...")
    manage_reports()
    logging.info("Report_generator module test finished.")
