import argparse
import configparser
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from agentstepper.core.types import Run
from agentstepper.core.server_version import DEBUGGER_SERVER_VERSION

def parse_arguments(logger, argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parses command line arguments for the Debugger Server.

    Precedence: CLI args > config file values > built-in defaults.

    :return: Parsed command line arguments.
    :rtype: argparse.Namespace
    """
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument('-c', '--config', type=str,
                      help='Path to a .conf file (INI-style). CLI flags take precedence over this file.')

    known, remaining = base.parse_known_args(argv)

    config_defaults: Dict[str, Any] = {}
    if known.config:
        try:
            config_defaults = load_config_file(known.config)
            logger.info(f"Loaded configuration from {known.config}")
        except Exception as e:
            logger.warning(f"Failed to load config file '{known.config}': {e}")

    parser = argparse.ArgumentParser(
        description='Debugger Server Command Line Interface',
        parents=[base]
    )

    def_cfg_host = config_defaults.get('host', 'localhost')
    def_cfg_client_port = int(config_defaults.get('client_port', 8765))
    def_cfg_ui_port = int(config_defaults.get('ui_port', 4567))
    def_cfg_runs = config_defaults.get('runs', [])  # list[str]
    def_cfg_model = config_defaults.get('model', 'gpt-5-nano')

    parser.add_argument('--host', type=str, default=def_cfg_host,
                        help=f'Hostname for the debugger server (default: {def_cfg_host})')
    parser.add_argument('--client-port', type=int, default=def_cfg_client_port,
                        help=f'Port for debugger client connection (default: {def_cfg_client_port})')
    parser.add_argument('--ui-port', type=int, default=def_cfg_ui_port,
                        help=f'Port for UI component connection (default: {def_cfg_ui_port})')
    parser.add_argument('-r', '--runs', type=str, nargs='*', default=def_cfg_runs,
                        help='Run files to load on startup')
    parser.add_argument('--model', type=str, default=def_cfg_model,
                        help=f'LLM model to use for prompt summarization (default: {def_cfg_model}")')

    args = parser.parse_args(remaining)

    if isinstance(args.runs, str):
        args.runs = _parse_runs_value(args.runs)

    return args


def load_config_file(path: str) -> Dict[str, Any]:
    """
    Load INI-style .conf file and return a dict of defaults.
    Supported keys (in [debugger] section or DEFAULTS): host, client_port, ui_port, runs, model

    - runs: can be comma-separated or whitespace-separated.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {path}")

    config = configparser.ConfigParser()
    read_files = config.read(path)
    if not read_files:
        raise ValueError(f"Unable to read config file: {path}")

    # Merge from possible sections, preferring [debugger] then [server], then DEFAULT
    def getkey(key: str, default: Optional[str] = None) -> Optional[str]:
        for section in ('debugger', 'server'):
            if config.has_option(section, key):
                return config.get(section, key)
        return config['DEFAULT'].get(key, default)

    defaults: Dict[str, Any] = {}

    host = getkey('host')
    if host:
        defaults['host'] = host

    client_port = getkey('client_port')
    if client_port:
        defaults['client_port'] = int(client_port)

    ui_port = getkey('ui_port')
    if ui_port:
        defaults['ui_port'] = int(ui_port)

    runs_val = getkey('runs')
    if runs_val:
        defaults['runs'] = _parse_runs_value(runs_val)

    model = getkey('model')
    if model:
        defaults['model'] = model

    return defaults


def _parse_runs_value(value: str) -> List[str]:
    """
    Accept comma and/or whitespace separated list of run file paths.
    """
    parts = [s for s in re.split(r'[,\s]+', value.strip()) if s]
    return parts


def load_runs(logger, server: 'DebuggerServer', run_files: List[str]) -> None:
    """
    Loads run files into the debugger server's run history.

    :param DebuggerServer server: The debugger server instance to load runs into.
    :param List[str] run_files: List of paths to run files to be loaded.
    """
    for run_path in run_files:
        try:
            file_path = Path(run_path)
            if not file_path.exists():
                logger.warning(f"Run file not found: {run_path}")
                continue
            
            with file_path.open('rb') as file:
                data = file.read()
                run = Run.from_bytes(data, is_base64_encoded=False)
                if run.server_version == DEBUGGER_SERVER_VERSION:
                    server.run_history.append(run)
                    logger.info(f"Successfully loaded run: {run_path}")
                else:
                    raise Exception('Run file incompatible with current server version')
                
        except ValueError as e:
            logger.warning(f"Invalid run file format in {run_path}: {str(e)}")
            continue
        except Exception as e:
            logger.warning(f"Failed to load run file {run_path}: {str(e)}")
            continue