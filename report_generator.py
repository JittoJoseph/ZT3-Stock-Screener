import os
from datetime import datetime
import math
import numpy as np # Import numpy to check its types
import config
from utils.helpers import logging, get_report_filename, manage_reports

def _format_volume(volume_val):
    """Helper to format volume consistently."""
    if isinstance(volume_val, (int, float, np.integer, np.floating)) and not math.isnan(volume_val):
        try:
            return f"{int(volume_val):,}"
        except (ValueError, TypeError):
            return 'N/A'
    elif isinstance(volume_val, str) and volume_val.isdigit():
        try:
            return f"{int(volume_val):,}"
        except (ValueError, TypeError):
            return 'N/A'
    return 'N/A'

# --- Constants from config.settings ---
screener_config = config.settings['screener'] # Get the screener sub-dictionary

# Get constants for headers from config
AVG_VOLUME_LOOKBACK_REPORT = screener_config.get('avg_volume_lookback', 50) # Use avg_volume_lookback
EMA_PERIOD_LONG_REPORT = screener_config.get('ema_period_long', 50)
EMA_PERIOD_SHORT_REPORT = screener_config.get('ema_period_short', 20)

def generate_html_report(shortlisted_stocks, filename):
    # Always create a report, even when no stocks are shortlisted
    report_dir = os.path.dirname(filename)
    os.makedirs(report_dir, exist_ok=True)

    screening_date_str = "N/A"
    if shortlisted_stocks:
        dates = [s.get('timestamp') for s in shortlisted_stocks if s.get('timestamp')]
        screening_date_str = max(dates).strftime('%Y-%m-%d') if dates else datetime.now().strftime('%Y-%m-%d')
    else:
         screening_date_str = datetime.now().strftime('%Y-%m-%d')

    # If no stocks passed, craft a minimal content with a clear message and failure report link.
    if not shortlisted_stocks:
         # Use day-specific filename for failure report link
         date_for_link = screening_date_str.replace("-", "")  # e.g. "20250430"
         failure_report_link = f"failure_report_{date_for_link}.html"
         html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Screener Report - {screening_date_str}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; color: #212529; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Daily Screener Report</h1>
        <p class="subtitle">Screening Date: {screening_date_str}</p>
        <p>No stocks passed the screening criteria today.</p>
        <p>Please review the <a href="{failure_report_link}" target="_blank">Failure Analysis Report</a> for further details.</p>
        <div class="footer">
            Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
         """
    else:
         # Compute day-specific failure report link using screening_date_str
         date_for_link = screening_date_str.replace("-", "")
         html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Screener Report - {screening_date_str}</title>
    <style>
        /* ... existing styles ... */
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            color: #212529;
            font-size: 14px;
        }}
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
            min-width: 800px; /* Adjusted min-width for more columns */
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            border: 1px solid #dee2e6;
            padding: 12px 15px;
            text-align: left;
            vertical-align: middle;
            white-space: nowrap;
            font-size: 1.5em; /* Mobile font size */
        }}
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

        /* Adjust alignment for new columns */
        td:nth-child(4), /* Close Price */
        td:nth-child(5), /* EMA(20) */
        td:nth-child(6), /* EMA(50) */
        td:nth-child(7), /* Period High */
        td:nth-child(8), /* Period Low */
        td:nth-child(9), /* Volume */
        td:nth-child(10), /* Avg Vol */
        td:nth-child(11)  /* Vol Ratio */
        {{
            text-align: right;
        }}

        .footer {{
            margin-top: 20px;
            font-size: 0.8em;
            text-align: center;
            color: #6c757d;
            padding: 10px 15px;
        }}

        /* Desktop Styles */
        @media (min-width: 768px) {{
            body {{
                padding: 20px;
                font-size: 16px;
            }}
            .container {{
                max-width: 1400px; /* Wider container for more columns */
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
            .table-container {{
                 margin: 0;
                 padding: 0;
            }}
            table {{
                min-width: auto;
            }}
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
        <h1>Daily Screener Report</h1>
        <p style="text-align:center; margin-bottom:20px;"><a href="failure_report_{date_for_link}.html" target="_blank">View Failure Analysis Report</a></p>
        <p class="subtitle">Screening Date: {screening_date_str}</p>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Symbol</th>
                        <th>ISIN</th>
                        <th>Close (₹)</th>
                        <th>EMA({EMA_PERIOD_SHORT_REPORT}) (₹)</th>
                        <th>EMA({EMA_PERIOD_LONG_REPORT}) (₹)</th>
                        <th>Period High (₹)</th>
                        <th>Period Low (₹)</th>
                        <th>Volume</th>
                        <th>Avg Vol ({AVG_VOLUME_LOOKBACK_REPORT}d)</th>
                        <th>Vol Ratio</th>
                    </tr>
                </thead>
                <tbody>
"""

         for i, stock in enumerate(shortlisted_stocks):
             # Access metrics dictionary
             metrics = stock.get('metrics', {})
             # Use the helper for current and average volume
             volume_str = _format_volume(stock.get('volume'))
             avg_volume_str = _format_volume(stock.get('avg_volume_50d')) # Use updated key name
             isin_val = stock.get('isin', 'N/A')
             # Access volume_ratio from the metrics dictionary
             volume_ratio_val = metrics.get('volume_ratio', 0.0) # Corrected access
             ema_20_val = metrics.get('ema_20', 0.0) # Get EMA(20)
             ema_50_val = metrics.get('ema_50', 0.0) # Get EMA(50)
             
             # Get symbol and create TradingView URL
             symbol = stock.get('symbol', 'N/A')
             tradingview_url = f"https://www.tradingview.com/chart/?symbol=NSE%3A{symbol}"

             # Add price drop percentage to display
             price_drop_pct = metrics.get('price_drop_pct', 0.0)

             # Construct the table row string explicitly
             row_html = "<tr>"
             row_html += f"<td>{i+1}</td>"
             row_html += f"<td><a href=\"{tradingview_url}\" target=\"_blank\">{symbol}</a></td>"
             row_html += f"<td>{isin_val}</td>"
             row_html += f"<td style='text-align: right;'>{stock.get('close', 0.0):.2f}</td>"
             row_html += f"<td style='text-align: right;'>{ema_20_val:.2f}</td>" # Add EMA(20) value
             row_html += f"<td style='text-align: right;'>{ema_50_val:.2f}</td>" # Add EMA(50) value
             row_html += f"<td style='text-align: right;'>{stock.get('period_high', 0.0):.2f}</td>" # Use period_high
             row_html += f"<td style='text-align: right;'>{price_drop_pct:.2f}%</td>" # Show price drop %
             row_html += f"<td style='text-align: right;'>{volume_str}</td>"
             row_html += f"<td style='text-align: right;'>{avg_volume_str}</td>" # Add avg volume (50d)
             row_html += f"<td style='text-align: right;'>{volume_ratio_val:.2f}x</td>" # Add volume ratio (Corrected)
             row_html += "</tr>\n"

             html_content += row_html # Append the constructed row

         html_content += """
            </tbody>
          </table>
        </div>
        <div class="footer">
          Generated on: """ + datetime.now().strftime('%Y-%m-%d %I:%M %p') + """
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

    # Dummy data matching the new output of screener_logic (including metrics dict)
    dummy_stocks = [
        {'symbol': 'RELIANCE', 'isin': 'INE002A01018', 'close': 2880.50, 'period_high': 2900.00, 'period_low': 1400.00, 'volume': 1234567, 'avg_volume_50d': 800000, 'timestamp': datetime.now(), 'metrics': {'volume_ratio': 1.54, 'price_drop_pct': 0.67, 'ema_50': 2850.10, 'ema_20': 2865.50}}, # Added ema_20
        {'symbol': 'TCS', 'isin': 'INE467B01029', 'close': 3465.20, 'period_high': 3500.00, 'period_low': 1700.00, 'volume': 890123.0, 'avg_volume_50d': 500000, 'timestamp': datetime.now(), 'metrics': {'volume_ratio': 1.78, 'price_drop_pct': 0.99, 'ema_50': 3400.50, 'ema_20': 3420.00}}, # Added ema_20
        {'symbol': 'HDFCBANK', 'isin': 'INE040A01034', 'close': 1622.80, 'period_high': 1650.00, 'period_low': 800.00, 'volume': 2500000, 'avg_volume_50d': 1500000, 'timestamp': datetime.now(), 'metrics': {'volume_ratio': 1.67, 'price_drop_pct': 1.65, 'ema_50': 1605.20, 'ema_20': 1615.80}}, # Added ema_20
        {'symbol': 'INFY', 'isin': 'INE009A01021', 'close': 1500.00, 'period_high': 1510.00, 'period_low': 700.00, 'volume': 1800000, 'avg_volume_50d': 1000000, 'timestamp': datetime.now(), 'metrics': {'volume_ratio': 1.80, 'price_drop_pct': 0.66, 'ema_50': 1480.90, 'ema_20': 1495.10}}, # Added ema_20
    ]

    report_file = get_report_filename()
    generate_html_report(dummy_stocks, report_file)
    logging.info("Running report management after generation...")
    manage_reports()
    logging.info("Report_generator module test finished.")
