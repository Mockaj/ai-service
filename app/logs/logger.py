import logging
import os
from logging.handlers import RotatingFileHandler

# Define the log file path
log_file = 'logs/app.log'
log_dir = os.path.dirname(log_file)

# Ensure the log directory exists
os.makedirs(log_dir, exist_ok=True)

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set up a specific file handler with rotation
file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024,
                                   backupCount=10)  # 10 MB per file, keep 10 backups
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Configure the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)


def get_logger(name):
    return logging.getLogger(name)


# Initialize logging configuration
get_logger(__name__)
