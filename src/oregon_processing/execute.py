from oregon_processing.commands import setup_config, open_terminal, run_export_protocol, get_database_status
import argparse
import sys

def main():
    commands = {
        "setup_config": setup_config,
        "open_terminal": open_terminal,
        "run_export_protocol": run_export_protocol,
        "get_database_status": get_database_status
    }
    parser = argparse.ArgumentParser(description="Execute a Oregon-Processing command.")
    parser.add_argument(
        "command",
        choices=commands.keys(),
        help="The name of the command to execute. Choices: %(choices)s"
    )
    args = parser.parse_args()

    command = args.command
    if command not in commands:
        print(f"Invalid command: {command}")
        parser.print_help()
        return 1

    command_func = commands[command]
    result = command_func()
    return result if isinstance(result, int) else 0

if __name__ == "__main__":
    sys.exit(main())