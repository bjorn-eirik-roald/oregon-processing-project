

from oregon_processing.util.config import check_config_file_exists
from oregon_processing.util.export_protocol import ExportProtocol
from oregon_processing.util.oregon_config import OregonConfig


def run_export_protocol():

    config_exists = check_config_file_exists(OregonConfig)
    if not config_exists:
        return

    with ExportProtocol() as export_protocol:
        export_protocol.run_export_protocol()