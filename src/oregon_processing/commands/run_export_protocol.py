

from oregon_processing.util.export_protocol import ExportProtocol
from oregon_processing.util.oregon_config import NoConfigError


def run_export_protocol():

    try:
        with ExportProtocol() as export_protocol:
            export_protocol.run_export_protocol()
    except (NoConfigError, ConnectionError) as e:
        print(f"\n\n"+str(e))

if __name__ == "__main__":
    run_export_protocol()