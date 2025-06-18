import logging
from django.core.files.storage import default_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def delete_csv(csv_filepath):
    try:
        csv_file_path = csv_filepath.name
        # Only delete if it exists
        if default_storage.exists(csv_file_path):
            default_storage.delete(csv_file_path)
    except Exception as e:
        logger.error(f"Error deleting CSV file {csv_file_path}: {e}")
        return False

def delete_norm_csv(norm_csv_filepath):
    try:
        norm_csv_file_path = norm_csv_filepath.name
        default_storage.delete(norm_csv_file_path)
    except Exception as e:
        logger.error(f"Error deleting normalized CSV file {norm_csv_file_path}: {e}")
        return False