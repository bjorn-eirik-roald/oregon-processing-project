from oregon_processing.util.project import OregonProject
from oregon_processing.util.logging_manager import LoggingManager, get_logger
from oregon_processing.util.exceptions import NoFileSelectedError, InvalidProjectDirectoryError, UserCancelledError

def create_project():

    try:
        with LoggingManager(write_to_report_file=False, write_to_console=True):
            logger = get_logger(__name__)
            OregonProject.create_new_project()
            logger.info("Project created successfully.")
    except (FileExistsError, NoFileSelectedError, InvalidProjectDirectoryError, UserCancelledError) as e:
        print(f"\n\nProject creation failed due to an error. Please see the error message below for more details:\n\n{str(e)}")

if __name__ == "__main__":
    create_project()
