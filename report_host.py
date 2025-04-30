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

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logging.error("Usage: python report_host.py path/to/success_report.html [path/to/failure_report.html]")
    else:
        success_report = sys.argv[1]
        failure_report = sys.argv[2] if len(sys.argv) >= 3 else None
        publish_both_reports(success_report, failure_report)
