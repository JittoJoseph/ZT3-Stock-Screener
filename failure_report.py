import os
import pandas as pd
from datetime import datetime
import math
import numpy as np
from collections import Counter

from utils.helpers import logging, get_report_filename # Assuming get_report_filename exists
import config

# Constants from screener_logic for context in report
LOOKBACK_PERIOD = config.settings['screener']['lookback_period'] # Now 50 from config
MIN_CLOSE_PRICE = 10.0
PRICE_DROP_FROM_HIGH_PERCENT_MAX = 10.0
PRICE_DROP_FROM_HIGH_PERCENT_MIN = 0.0
EMA_PERIOD = 50 # Updated EMA Period to 50
AVG_VOLUME_LOOKBACK = 50 # Updated Avg Vol Lookback to 50
VOLUME_SURGE_MULTIPLIER = 2.0

# Define rule names for clarity in the report (5 rules) - Updated Rules 3 & 5
RULE_NAMES = {
    'passed_rule1': f'Drop% < {PRICE_DROP_FROM_HIGH_PERCENT_MAX}% ({LOOKBACK_PERIOD}d High)', # Added period
    'passed_rule2': f'Drop% > {PRICE_DROP_FROM_HIGH_PERCENT_MIN}% ({LOOKBACK_PERIOD}d High)', # Added period
    'passed_rule3': f'Close > EMA({EMA_PERIOD})', # Updated EMA period
    'passed_rule4': f'Close > ₹{MIN_CLOSE_PRICE}',
    'passed_rule5': f'Vol > {VOLUME_SURGE_MULTIPLIER}x Avg({AVG_VOLUME_LOOKBACK}d)' # Updated Avg Vol period
}

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

def generate_failure_report(all_stocks_details, filename, min_rules_passed=4): # Changed default to 4
    """
    Generates an HTML report analyzing stocks that failed the main screening
    but passed at least `min_rules_passed` rules (out of 5).

    Args:
        all_stocks_details (list): List of dictionaries returned by apply_screening
                                   for ALL processed stocks.
        filename (str): Path to save the HTML report.
        min_rules_passed (int): Minimum number of rules a stock must have passed
                                to be included in this report (default 4). # Updated comment
    """
    # Filter stocks that failed overall but passed at least min_rules_passed
    # Also exclude stocks skipped due to data issues or errors
    nearly_passed_stocks = [
        s for s in all_stocks_details
        if s.get('failed_overall', True) and
           s.get('rules_passed_count', 0) >= min_rules_passed and # Logic uses min_rules_passed
           s.get('reason') not in ["No data", "Insufficient data", "NaN/Zero in critical data"] and
           not str(s.get('reason', '')).startswith("Error:")
    ]

    if not nearly_passed_stocks:
        logging.info(f"No stocks passed at least {min_rules_passed}/5 rules. Failure analysis report will not be generated.") # Updated log message
        return False # Indicate report was not generated

    report_dir = os.path.dirname(filename)
    os.makedirs(report_dir, exist_ok=True)

    screening_date_str = "N/A"
    for stock in nearly_passed_stocks:
        if stock.get('timestamp'):
            screening_date_str = stock['timestamp'].strftime('%Y-%m-%d')
            break

    # --- Analyze Failure Reasons ---
    failure_counts = Counter()
    total_valid_processed = len([s for s in all_stocks_details if s.get('reason') not in ["No data", "Insufficient data", "NaN/Zero in critical data"] and not str(s.get('reason','')).startswith('Error:')])
    total_passed_all = len([s for s in all_stocks_details if not s.get('failed_overall', True)])

    for stock in nearly_passed_stocks:
        failed_rules_list = []
        for rule_key, rule_desc in RULE_NAMES.items():
            if not stock.get(rule_key, False):
                failure_counts[rule_desc] += 1
                # Extract a shorter name for the table display
                short_name = rule_desc.split('(')[0].strip() # General short name
                if rule_key == 'passed_rule1': short_name = "Drop%<10"
                elif rule_key == 'passed_rule2': short_name = "Drop%>0"
                elif rule_key == 'passed_rule3': short_name = f"Close>EMA{EMA_PERIOD}" # Updated short name
                elif rule_key == 'passed_rule4': short_name = "Price>10"
                elif rule_key == 'passed_rule5': short_name = f"Vol>{VOLUME_SURGE_MULTIPLIER}x"
                failed_rules_list.append(short_name)
        stock['failed_rules_display'] = ', '.join(failed_rules_list) if failed_rules_list else "None"

    # --- Generate HTML ---
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Failure Analysis Report - {screening_date_str}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #212529; font-size: 16px; }}
        .container {{ max-width: 1400px; margin: 20px auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #dc3545; margin-bottom: 10px; font-size: 2em; }} /* Red for failure */
        p.subtitle {{ text-align: center; color: #6c757d; margin-top: 0; margin-bottom: 30px; font-size: 1.1em; }}
        .summary {{ background-color: #fdfdfe; border: 1px solid #dee2e6; padding: 15px; margin-bottom: 25px; border-radius: 5px; }}
        .summary h2 {{ margin-top: 0; color: #495057; font-size: 1.3em; }}
        .summary ul {{ list-style: none; padding: 0; }}
        .summary li {{ margin-bottom: 8px; font-size: 1em; }}
        .table-container {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.95em; }}
        th, td {{ border: 1px solid #dee2e6; padding: 10px 12px; text-align: left; vertical-align: middle; }}
        th {{ background-color: #e9ecef; color: #495057; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        td.numeric {{ text-align: right; }}
        td.center {{ text-align: center; }}
        td.fail {{ color: #dc3545; font-weight: bold; }} /* Highlight failures */
        td.pass {{ color: #28a745; }} /* Green for pass count */
        .footer {{ margin-top: 30px; font-size: 0.9em; text-align: center; color: #6c757d; }}

        /* Mobile adjustments */
        @media (max-width: 767px) {{
            body {{ padding: 10px; font-size: 14px; }}
            .container {{ padding: 15px; }}
            h1 {{ font-size: 1.6em; }}
            p.subtitle {{ font-size: 1em; margin-bottom: 20px; }}
            .summary h2 {{ font-size: 1.2em; }}
            .summary li {{ font-size: 0.95em; }}
            th, td {{ padding: 8px 10px; font-size: 0.9em; white-space: nowrap; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Failure Analysis Report</h1>
        <p class="subtitle">Screening Date: {screening_date_str} (Showing stocks passing ≥ {min_rules_passed}/5 rules)</p> <!-- Updated subtitle text -->

        <div class="summary">
            <h2>Failure Summary</h2>
            <p>Total stocks processed (with valid data): {total_valid_processed}</p>
            <p>Stocks passing all 5 criteria: {total_passed_all}</p>
            <p>Stocks included in this report (passed ≥ {min_rules_passed}/5 rules): {len(nearly_passed_stocks)}</p> <!-- Updated summary text -->
            <p>Most common failure reasons for stocks in this report:</p>
            <ul>
    """
    # Add failure counts to summary
    if failure_counts:
        for reason, count in failure_counts.most_common():
            html_content += f"<li>{reason}: {count} stock(s)</li>"
    else:
        html_content += "<li>No specific failure reasons identified for this subset.</li>"

    html_content += """
            </ul>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Symbol</th>
                        <th>Close (₹)</th>
                        <th>EMA({EMA_PERIOD}) (₹)</th> <!-- Updated EMA column header -->
                        <th>Period High (₹)</th>
                        <th>Period Low (₹)</th>
                        <th>Volume</th>
                        <th>Avg Vol ({AVG_VOLUME_LOOKBACK}d)</th> <!-- Updated Avg Vol column header -->
                        <th>Vol Ratio</th>
                        <th>Rules Passed</th>
                        <th>Failed Rule(s)</th>
                        <th>Drop %</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Populate table rows
    for i, stock in enumerate(nearly_passed_stocks):
        metrics = stock.get('metrics', {})
        html_content += f"""
                    <tr>
                        <td>{i+1}</td>
                        <td>{stock.get('symbol', 'N/A')}</td>
                        <td class="numeric">{stock.get('close', 0.0):.2f}</td>
                        <td class="numeric">{metrics.get('ema_50', 0.0):.2f}</td>
                        <td class="numeric">{stock.get('period_high', 0.0):.2f}</td>
                        <td class="numeric">{stock.get('period_low', 0.0):.2f}</td>
                        <td class="numeric">{_format_volume(stock.get('volume'))}</td>
                        <td class="numeric">{_format_volume(stock.get('avg_volume_50d'))}
                        <td class="numeric">{metrics.get('volume_ratio', 0.0):.2f}x</td>
                        <td class="center pass">{stock.get('rules_passed_count', 0)}/5</td>
                        <td class="fail">{stock.get('failed_rules_display', 'N/A')}</td>
                        <td class="numeric">{metrics.get('price_drop_pct', 0.0):.2f}%</td>
                    </tr>
"""

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
        logging.info(f"Failure analysis report generated successfully: {filename}")
        return True # Indicate success
    except IOError as e:
        logging.error(f"Error writing failure analysis report to {filename}: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during failure analysis report generation: {e}")
        return False

# Optional: Add __main__ block for testing if desired
# if __name__ == '__main__':
#     # Create dummy data similar to screener_logic output
#     # Call generate_failure_report with dummy data and test filename
#     pass
