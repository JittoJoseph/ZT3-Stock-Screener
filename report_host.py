import os
import shutil
import subprocess
from datetime import datetime
from utils.helpers import logging  # Uses existing logging setup
import glob
import config

# Define project root as the directory that contains this file.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

TARGET_FILENAME = "index.html"
TARGET_FILEPATH = os.path.join(DOCS_DIR, TARGET_FILENAME)
TARGET_FAILURE_FILENAME = "failure-report.html"
TARGET_FAILURE_FILEPATH = os.path.join(DOCS_DIR, TARGET_FAILURE_FILENAME)

def run_git_command(command_list, cwd=PROJECT_ROOT):
    """Run a git command using subprocess and log the output."""
    try:
        logging.info(f"Running command: {' '.join(command_list)}")
        result = subprocess.run(command_list, cwd=cwd, capture_output=True, text=True, check=True)
        logging.info(result.stdout)
        if result.stderr:
            logging.warning(result.stderr)
        return True
    except Exception as e:
        logging.error(f"Git command failed: {e}")
        return False

def publish_both_reports(success_filepath, failure_filepath):
    """
    Copies the success report to docs/index.html and the failure report to 
    docs/failure-report.html (if they exist), then commits and pushes both changes
    as a single commit.
    """
    files_to_commit = []
    
    if success_filepath and os.path.exists(success_filepath):
        try:
            shutil.copyfile(success_filepath, TARGET_FILEPATH)
            logging.info(f"Copied '{success_filepath}' to '{TARGET_FILEPATH}'")
            files_to_commit.append(os.path.relpath(TARGET_FILEPATH, PROJECT_ROOT))
        except Exception as e:
            logging.error(f"Error copying success report: {e}")
    else:
        logging.warning("Success report file not found or not provided.")
    
    if failure_filepath and os.path.exists(failure_filepath):
        try:
            shutil.copyfile(failure_filepath, TARGET_FAILURE_FILEPATH)
            logging.info(f"Copied '{failure_filepath}' to '{TARGET_FAILURE_FILEPATH}'")
            files_to_commit.append(os.path.relpath(TARGET_FAILURE_FILEPATH, PROJECT_ROOT))
        except Exception as e:
            logging.error(f"Error copying failure report: {e}")
    else:
        logging.warning("Failure report file not found or not provided.")
    
    if not files_to_commit:
        logging.error("No report files to commit.")
        return

    commit_message = f"Update GitHub Pages reports: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if run_git_command(["git", "add"] + files_to_commit):
        if run_git_command(["git", "commit", "-m", commit_message]):
            if run_git_command(["git", "push"]):
                logging.info("Reports published successfully via GitHub Pages in a single commit.")
            else:
                logging.error("Git push failed for reports.")
        else:
            logging.error("Git commit failed for reports.")
    else:
        logging.error("Git add failed for reports.")

    update_landing_page()

def update_landing_page():
    """
    Creates/updates index.html as a minimalist landing page.
    It scans for success report files generated daily that include the trading date (last candle date)
    in their filename (format: success_report_YYYYMMDD_HHMMSS.html).
    It groups reports by trading day, picks the latest report per day,
    and then displays links for the last 5 trading days.
    Any report older than 5 days is dropped.
    """
    report_dir = config.settings['paths']['report_dir']
    # Get list of success report files (assume naming: success_report_YYYYMMDD_*.html)
    success_files = glob.glob(os.path.join(report_dir, "success_report_*.html"))
    
    # Build a dict keyed by trading date (YYYYMMDD) and value the latest file for that day
    daily_reports = {}
    for filepath in success_files:
        # Example filename: success_report_20250430_211959.html
        basename = os.path.basename(filepath)
        try:
            parts = basename.split('_')
            trading_date = parts[2]  # e.g. "20250430"
            # Use trading_date as key and compare filenames (or modification times) to select latest
            if trading_date not in daily_reports:
                daily_reports[trading_date] = filepath
            else:
                # Optionally, select the file with the highest timestamp (or latest mod time)
                if os.path.getmtime(filepath) > os.path.getmtime(daily_reports[trading_date]):
                    daily_reports[trading_date] = filepath
        except Exception as e:
            logging.warning(f"Could not parse trading date from filename {basename}: {e}")
            continue

    # Sort trading days descending and keep last 5 (if available)
    sorted_days = sorted(daily_reports.keys(), reverse=True)[:5]
    links_html = ""
    for day in sorted_days:
        report_file = os.path.basename(daily_reports[day])
        # Format link text as trading date in a friendly format
        trading_date_obj = datetime.strptime(day, "%Y%m%d")
        link_text = trading_date_obj.strftime("%d %b %Y")
        links_html += f'<li><a href="{report_file}">{link_text} Success Report</a></li>\n'

    # Also include today's failure report if available (assume file named failure_report_YYYYMMDD.html)
    failure_files = glob.glob(os.path.join(report_dir, "failure_report_*.html"))
    latest_failure = None
    if failure_files:
        latest_failure = max(failure_files, key=os.path.getmtime)
    failure_link = ""
    if latest_failure:
        failure_link = f'<p><a href="{os.path.basename(latest_failure)}">Today\'s Failure Analysis</a></p>'

    # Build landing page HTML
    landing_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ZT-3 Stock Screener Reports</title>
  <style>
      body {{ font-family: 'Segoe UI', sans-serif; background-color: #f8f9fa; color: #212529; padding: 20px; }}
      .container {{ max-width: 800px; margin: auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
      h1 {{ text-align: center; }}
      ul {{ list-style: none; padding: 0; }}
      li {{ margin: 10px 0; }}
      a {{ color: #007bff; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>ZT-3 Stock Screener Reports</h1>
    <p>Latest 5 Trading Days Success Reports:</p>
    <ul>
      {links_html}
    </ul>
    {failure_link}
  </div>
</body>
</html>"""

    index_filepath = os.path.join(report_dir, "index.html")
    with open(index_filepath, "w", encoding="utf-8") as f:
        f.write(landing_html)
    logging.info(f"Landing page updated at: {index_filepath}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logging.error("Usage: python report_host.py path/to/success_report.html [path/to/failure_report.html]")
    else:
        success_report = sys.argv[1]
        failure_report = sys.argv[2] if len(sys.argv) >= 3 else None
        publish_both_reports(success_report, failure_report)
