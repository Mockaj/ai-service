import logging
from logging.handlers import RotatingFileHandler

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log_file = 'app/logs/app.log'  # Use a proper path for log files in production /www/logs/app/app.log

# Set up a specific file handler with rotation
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=10)  # 10 MB per file, keep 10 backups
file_handler.setFormatter(log_formatter)

# Configure the root logger
logging.basicConfig(level=logging.INFO, handlers=[file_handler])

logger = logging.getLogger(__name__)
