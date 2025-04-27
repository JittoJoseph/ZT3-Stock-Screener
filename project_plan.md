# Daily Breakout Screener – Project Plan

## Overview

The Daily Breakout Screener is a Python-based application designed to screen Indian stocks daily based on strict breakout and volume surge conditions. The project will fetch historical stock data using the Upstox API, apply technical screening criteria, generate a local HTML report, and send shortlisted stock alerts to a Discord channel via a webhook.

---

## Project Structure

```
daily_breakout_screener/
│
├── stock_list.csv             # Stock symbols and ISINs to scan
├── config.py                  # API keys, Discord webhook URL, and settings
├── data_fetcher.py             # Fetch historical daily candles via Upstox API
├── screener_logic.py           # Apply breakout and volume screening logic
├── report_generator.py         # Generate local HTML report
├── discord_notifier.py         # Send shortlisted stocks to Discord webhook
├── utils.py                    # Utility functions (report management, logging)
├── main.py                     # Entry point script
├── outputs/
│    └── reports/               # Stores HTML reports (only latest 2 retained)
└── requirements.txt            # Python dependencies
```

---

## Screening Conditions

1. **Breakout Condition**:  
   Today's close price must be greater than the highest close price of the last 20 trading days.

2. **Volume Condition**:  
   Today's volume must be greater than 1.5 times the average daily volume of the last 20 trading days.

3. **Price Range Condition**:  
   Today's close price must be between ₹20 and ₹1000.

4. **Trend Condition**:  
   Today's close price must be greater than the 20-day EMA (Exponential Moving Average).

All four conditions are mandatory. A stock must pass all conditions to be shortlisted.

---

## Stock List

- File: `stock_list.csv`
- Format:
  ```
  symbol,isin
  RELIANCE,INE002A01018
  TCS,INE467B01029
  ICICIBANK,INE090A01021
  ...
  ```
- This file is manually maintained. Only stocks listed in this file will be scanned.

---

## Output

### 1. HTML Report

- Location: `outputs/reports/`
- Contents:
  - Stock Symbol
  - ISIN
  - Close Price
  - Breakout Level
  - Volume Surge (in %)
  - EMA(20) Value
  - Screening Date
- Only the latest two HTML reports are retained. Older reports are automatically deleted.

### 2. Discord Webhook Notification

- A simple embedded message is sent to a designated Discord channel using a webhook.
- Message Content:
  - Date of screening
  - List of shortlisted stocks with their symbol and close price
  - Quick summary of conditions passed (breakout, volume, EMA)

Example Discord Message (in embedded format):

```
**Daily Breakout Screener — 27-Apr-2025**

Shortlisted Stocks:
- RELIANCE (₹2880.5)
- TCS (₹3465.2)
- HDFCBANK (₹1622.8)
```

No HTML report is sent via Discord. Only embedded text.

---

## Technology Stack

| Component       | Technology                                                    |
| :-------------- | :------------------------------------------------------------ |
| Data Fetching   | Upstox API (Python SDK)                                       |
| Data Processing | pandas, numpy                                                 |
| Reporting       | Manual HTML generation via Python                             |
| Notification    | Discord Webhook (HTTP POST)                                   |
| Miscellaneous   | os, shutil, glob, dotenv (optional for environment variables) |

---

## Detailed Testing Plan

| Stage                | Test Objective                                   | Method                                            |
| :------------------- | :----------------------------------------------- | :------------------------------------------------ |
| Stock List Loading   | Ensure stock_list.csv loads correctly.           | Validate loaded symbols and ISINs.                |
| API Connection       | Ensure stable Upstox connection and data fetch.  | Fetch known stock candles, check sample output.   |
| Data Accuracy        | Verify correct candle data is used.              | Compare fetched data against public charts.       |
| Breakout Condition   | Correctly identify breakouts.                    | Backtest manually known breakout cases.           |
| Volume Condition     | Validate volume surge calculations.              | Compare against manually calculated averages.     |
| EMA Calculation      | Ensure correct EMA(20) values.                   | Cross-verify against TradingView/ChartIQ data.    |
| Report Management    | Ensure old reports deletion after 2 reports.     | Run multiple times, check outputs/reports folder. |
| Discord Notification | Validate webhook sending and message formatting. | Use a test webhook URL first.                     |

---

## Development Milestones

| Milestone                     |
| :---------------------------- |
| Project Structure Setup       |
| Upstox API Integration        |
| Data Fetcher Module           |
| Screener Logic Module         |
| Report Generator Module       |
| Discord Notification Module   |
| Integration and Final Testing |

---

## Daily Execution Flow

1. Run `python main.py`.
2. Fetch latest daily candles for listed stocks.
3. Apply the four strict screening conditions.
4. Generate and save an HTML report.
5. Send shortlisted stock list to Discord channel.

---

## Final Deliverables

- Fully functional Python project directory with modular, clean code.
- Ability to screen manually selected stocks daily.
- Local HTML report generation with automated old report management.
- Real-time Discord alerts via webhook without HTML attachment.

---
