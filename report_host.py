import os
import shutil
import subprocess
from datetime import datetime
from utils.helpers import logging  # Uses existing logging setup

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

def publish_report(report_filepath):
    """
    Copies the success HTML report to the docs folder as index.html,
    commits the change, and pushes to GitHub.
    
    Args:
        report_filepath (str): Full path to the success report.
    """
    if not report_filepath or not os.path.exists(report_filepath):
        logging.error(f"Report file not found: {report_filepath}")
        return
    
    try:
        shutil.copyfile(report_filepath, TARGET_FILEPATH)
        logging.info(f"Copied '{report_filepath}' to '{TARGET_FILEPATH}'")
    except Exception as e:
        logging.error(f"Error copying file: {e}")
        return

    commit_message = f"Update GitHub Pages report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if run_git_command(["git", "add", os.path.relpath(TARGET_FILEPATH, PROJECT_ROOT)]):
        if run_git_command(["git", "commit", "-m", commit_message]):
            if run_git_command(["git", "push"]):
                logging.info("Report published successfully via GitHub Pages.")
            else:
                logging.error("Git push failed.")
        else:
            logging.error("Git commit failed.")
    else:
        logging.error("Git add failed.")

def publish_failure_report(failure_filepath):
    """
    Copies the failure HTML report to the docs folder as failure-report.html,
    commits the change, and pushes to GitHub.
    """
    if not failure_filepath or not os.path.exists(failure_filepath):
        logging.error(f"Failure report file not found: {failure_filepath}")
        return
    
    try:
        shutil.copyfile(failure_filepath, TARGET_FAILURE_FILEPATH)
        logging.info(f"Copied '{failure_filepath}' to '{TARGET_FAILURE_FILEPATH}'")
    except Exception as e:
        logging.error(f"Error copying failure report file: {e}")
        return

    commit_message = f"Update GitHub Pages failure report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if run_git_command(["git", "add", os.path.relpath(TARGET_FAILURE_FILEPATH, PROJECT_ROOT)]):
        if run_git_command(["git", "commit", "-m", commit_message]):
            if run_git_command(["git", "push"]):
                logging.info("Failure report published successfully via GitHub Pages.")
            else:
                logging.error("Git push failed for failure report.")
        else:
            logging.error("Git commit failed for failure report.")
    else:
        logging.error("Git add failed for failure report.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logging.error("Usage: python report_host.py path/to/success_report.html [path/to/failure_report.html]")
    else:
        success_report = sys.argv[1]
        publish_report(success_report)
        if len(sys.argv) >= 3:
            failure_report = sys.argv[2]
            publish_failure_report(failure_report)
