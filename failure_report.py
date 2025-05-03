import os
from datetime import datetime
import pandas as pd
from utils.helpers import logging, get_report_filename
import config

# --- Constants from config.settings ---
screener_config = config.settings['screener'] # Get the screener sub-dictionary

# Get constants for headers from config
EMA_PERIOD_LONG = screener_config.get('ema_period_long', 50)
EMA_PERIOD_SHORT = screener_config.get('ema_period_short', 20)
LOOKBACK_PERIOD = screener_config.get('lookback_period', 50)
AVG_VOLUME_LOOKBACK = screener_config.get('avg_volume_lookback', 50)
PRICE_DROP_FROM_HIGH_PERCENT_MIN = screener_config.get('price_drop_percent_min', 0.0)
PRICE_DROP_FROM_HIGH_PERCENT_MAX = screener_config.get('price_drop_percent_max', 10.0)
VOLUME_SURGE_MULTIPLIER_MIN = screener_config.get('volume_surge_min', 2.0)
VOLUME_SURGE_MULTIPLIER_MAX = screener_config.get('volume_surge_max', 2.5)
MIN_CLOSE_PRICE = screener_config.get('min_price', 25.0)
MAX_PRICE = screener_config.get('max_price', 1500.0)
ENABLE_MAX_PRICE_LIMIT = screener_config.get('enable_max_price_limit', True)

# Updated to 4 rules (removed Liquidity Filter rule)
TOTAL_RULES = 4

def generate_failure_report(failed_stocks, filename, min_rules_passed=0):
    """
    Generates an HTML report detailing stocks that failed screening and why.
    
    Args:
        failed_stocks (list): List of dictionaries with stock information and failure reasons.
        filename (str): Path where the HTML report should be saved.
        min_rules_passed (int, optional): Minimum number of rules that must be passed to include in report. Defaults to 0.
    """
    report_dir = os.path.dirname(filename)
    os.makedirs(report_dir, exist_ok=True)
    
    # Handle None value for min_rules_passed
    if min_rules_passed is None:
        min_rules_passed = 0
        
    # Filter stocks based on min_rules_passed if specified
    if min_rules_passed > 0:
        failed_stocks = [s for s in failed_stocks if s.get('rules_passed_count', 0) >= min_rules_passed]
    
    screening_date = datetime.now().strftime("%Y-%m-%d")
    if failed_stocks and 'timestamp' in failed_stocks[0]:
        dates = [s.get('timestamp') for s in failed_stocks if s.get('timestamp')]
        if dates:
            screening_date = max(dates).strftime("%Y-%m-%d")
    
    # Read data and perform basic analysis
    total_failed = len(failed_stocks)
    
    # Create rule-specific failure counts
    rule_failures = {
        'rule1': 0,  # Trend Alignment: Close > EMA(20) > EMA(50) 
        'rule2': 0,  # Proximity to 50-Day High: 0% < Drop < 10%
        'rule3': 0,  # Volume Ratio: 2.0x < Ratio < 2.5x
        'rule4': 0   # Price Range: 25 < Close < 1500
    }
    
    # Count failures by rule
    for stock in failed_stocks:
        if not stock.get('passed_rule1', True):
            rule_failures['rule1'] += 1
        if not stock.get('passed_rule2', True):
            rule_failures['rule2'] += 1
        if not stock.get('passed_rule3', True):
            rule_failures['rule3'] += 1
        if not stock.get('passed_rule4', True):
            rule_failures['rule4'] += 1
    
    # Calculate statistics
    almost_passed = len([s for s in failed_stocks if s.get('rules_passed_count', 0) == TOTAL_RULES - 1])
    
    # Create HTML content
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Failure Analysis Report - {screening_date}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #212529;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #007bff;
            margin-top: 0;
        }}
        .stats-box {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #007bff;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-card {{
            background-color: #ffffff;
            border-radius: 6px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-card h3 {{
            margin-top: 0;
            color: #6c757d;
            font-size: 1em;
            font-weight: normal;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #343a40;
            margin: 10px 0;
        }}
        .stat-percent {{
            font-size: 0.9em;
            color: #6c757d;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 0.9em;
        }}
        th, td {{
            border: 1px solid #dee2e6;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #e9ecef;
            color: #495057;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e2e6ea;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }}
        .rule-desc {{
            font-size: 0.9em;
            color: #6c757d;
            margin-top: 5px;
        }}
        .almost-passed {{
            background-color: #fff3cd;
        }}
        .rule-indicator {{
            width: 15px;
            height: 15px;
            display: inline-block;
            margin-right: 5px;
            border-radius: 50%;
        }}
        .pass {{
            background-color: #28a745;
        }}
        .fail {{
            background-color: #dc3545;
        }}
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            .container {{
                padding: 15px;
            }}
            table {{
                display: block;
                overflow-x: auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Failure Analysis Report</h1>
        <p>Screening Date: {screening_date}</p>
        
        <div class="stats-box">
            <h2>Failure Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Stocks Failed</h3>
                    <div class="stat-value">{total_failed}</div>
                </div>
                <div class="stat-card">
                    <h3>Almost Passed (Failed 1 Rule)</h3>
                    <div class="stat-value">{almost_passed}</div>
                    <div class="stat-percent">{almost_passed/total_failed*100:.1f}% of failures</div>
                </div>
                <div class="stat-card">
                    <h3>Rule 1 Failures (Trend)</h3>
                    <div class="stat-value">{rule_failures['rule1']}</div>
                    <div class="stat-percent">{rule_failures['rule1']/total_failed*100:.1f}% of failures</div>
                </div>
                <div class="stat-card">
                    <h3>Rule 2 Failures (Drop%)</h3>
                    <div class="stat-value">{rule_failures['rule2']}</div>
                    <div class="stat-percent">{rule_failures['rule2']/total_failed*100:.1f}% of failures</div>
                </div>
                <div class="stat-card">
                    <h3>Rule 3 Failures (Vol Ratio)</h3>
                    <div class="stat-value">{rule_failures['rule3']}</div>
                    <div class="stat-percent">{rule_failures['rule3']/total_failed*100:.1f}% of failures</div>
                </div>
                <div class="stat-card">
                    <h3>Rule 4 Failures (Price Range)</h3>
                    <div class="stat-value">{rule_failures['rule4']}</div>
                    <div class="stat-percent">{rule_failures['rule4']/total_failed*100:.1f}% of failures</div>
                </div>
            </div>
            
            <div class="rule-desc">
                <p><strong>Rule 1:</strong> Trend Alignment - Close > EMA({EMA_PERIOD_SHORT}) > EMA({EMA_PERIOD_LONG})</p>
                <p><strong>Rule 2:</strong> Proximity to {LOOKBACK_PERIOD}-Day High - {PRICE_DROP_FROM_HIGH_PERCENT_MIN}% < Price Drop < {PRICE_DROP_FROM_HIGH_PERCENT_MAX}%</p>
                <p><strong>Rule 3:</strong> Volume Ratio - {VOLUME_SURGE_MULTIPLIER_MIN}x < Vol/{AVG_VOLUME_LOOKBACK}d Avg < {VOLUME_SURGE_MULTIPLIER_MAX}x</p>
                <p><strong>Rule 4:</strong> Price Range - ₹{MIN_CLOSE_PRICE} < Close < ₹{MAX_PRICE}</p>
            </div>
        </div>

        <h2>Detailed Analysis</h2>
        <p>The following stocks failed the screening criteria:</p>
        
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Close (₹)</th>
                    <th>Drop %</th>
                    <th>Vol Ratio</th>
                    <th>Rules Passed</th>
                    <th>Rule 1<br>(Trend)</th>
                    <th>Rule 2<br>(Drop%)</th>
                    <th>Rule 3<br>(Vol)</th>
                    <th>Rule 4<br>(Price)</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Sort by number of rules passed (descending)
    sorted_stocks = sorted(failed_stocks, key=lambda x: x.get('rules_passed_count', 0), reverse=True)
    
    for stock in sorted_stocks:
        symbol = stock.get('symbol', 'N/A')
        close = stock.get('close', 0)
        metrics = stock.get('metrics', {})
        price_drop_pct = metrics.get('price_drop_pct', 0)
        volume_ratio = metrics.get('volume_ratio', 0)
        rules_passed = stock.get('rules_passed_count', 0)
        reason = stock.get('reason', 'Unknown')
        
        # Check if this stock almost passed (failed just one rule)
        row_class = "almost-passed" if rules_passed == TOTAL_RULES - 1 else ""
        
        # Create indicators for each rule
        rule1_class = "pass" if stock.get('passed_rule1', False) else "fail"
        rule2_class = "pass" if stock.get('passed_rule2', False) else "fail"
        rule3_class = "pass" if stock.get('passed_rule3', False) else "fail"
        rule4_class = "pass" if stock.get('passed_rule4', False) else "fail"
        
        # Safe formatting - handle None and other invalid values
        close_str = f"{close:.2f}" if isinstance(close, (int, float)) and not pd.isna(close) else "N/A"
        drop_str = f"{price_drop_pct:.2f}%" if isinstance(price_drop_pct, (int, float)) and not pd.isna(price_drop_pct) else "N/A"
        ratio_str = f"{volume_ratio:.2f}x" if isinstance(volume_ratio, (int, float)) and not pd.isna(volume_ratio) else "N/A"
        
        # Create the row
        html_content += f"""
                <tr class="{row_class}">
                    <td>{symbol}</td>
                    <td>{close_str}</td>
                    <td>{drop_str}</td>
                    <td>{ratio_str}</td>
                    <td>{rules_passed}/{TOTAL_RULES}</td>
                    <td><span class="rule-indicator {rule1_class}"></span></td>
                    <td><span class="rule-indicator {rule2_class}"></span></td>
                    <td><span class="rule-indicator {rule3_class}"></span></td>
                    <td><span class="rule-indicator {rule4_class}"></span></td>
                    <td>{reason}</td>
                </tr>"""
    
    # Close the HTML
    html_content += """
            </tbody>
        </table>
        
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
        logging.info(f"Failure analysis report generated: {filename}")
    except Exception as e:
        logging.error(f"Error generating failure report: {e}")

if __name__ == "__main__":
    # Test code for the failure report generator
    from datetime import datetime
    
    # Sample failed stocks for testing
    test_failed_stocks = [
        {
            'symbol': 'SBIN', 
            'close': 750.50, 
            'timestamp': datetime.now(),
            'passed_rule1': True, 'passed_rule2': False, 'passed_rule3': True, 'passed_rule4': True,
            'rules_passed_count': 3,
            'metrics': {'price_drop_pct': 12.5, 'volume_ratio': 2.2},
            'reason': "Failed: Rule2(Drop%)"
        },
        {
            'symbol': 'INFY', 
            'close': 1650.75, 
            'timestamp': datetime.now(),
            'passed_rule1': False, 'passed_rule2': False, 'passed_rule3': True, 'passed_rule4': False,
            'rules_passed_count': 1,
            'metrics': {'price_drop_pct': 15.0, 'volume_ratio': 2.1},
            'reason': "Failed: Rule1(Trend), Rule2(Drop%), Rule4(PriceRange)"
        }
    ]
    
    test_filename = "test_failure_report.html"
    generate_failure_report(test_failed_stocks, test_filename)
    print(f"Test failure report generated: {test_filename}")
