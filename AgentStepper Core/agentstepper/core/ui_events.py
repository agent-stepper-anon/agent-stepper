from enum import Enum

class UIEventTypes(Enum):
    STEP = 'step'
    CONTINUE = 'continue'
    HALT = 'halt'
    RENAME_RUN = 'rename_run'
    DOWNLOAD_REQUEST = 'download_run_request'
    IMPORT_RUN = 'import_run'
    UPDATE_MSG_CONTENT = 'update_msg_content'
    DELETE_RUN = 'delete_run'