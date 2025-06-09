import logging
from django.core.files.storage import default_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_csv(csv_filepath):
    
    try:
        csv_file_path = csv_filepath.name
        default_storage.delete(csv_file_path)
    except Exception as e:
        logger.error(f"Error deleting CSV file {csv_file_path}: {e}")
        return False
