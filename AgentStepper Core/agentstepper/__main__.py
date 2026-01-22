import os
import logging
import colorlog
import threading
from agentstepper.debugger_core import AgentStepperCore
from agentstepper.core.cli_utils import parse_arguments, load_runs

# Configure logger
logger = logging.getLogger('DebuggerServer')
logger.setLevel(logging.DEBUG)

# Console handler with color
console_handler = colorlog.StreamHandler()
console_handler.setFormatter(
    colorlog.ColoredFormatter(
        '[%(asctime)s]%(log_color)s[%(levelname)s]%(reset)s %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
)
logger.addHandler(console_handler)

# File handler
log_filename = 'logs/debugger_server.log'
os.makedirs(os.path.dirname(log_filename), exist_ok=True)
file_handler = logging.FileHandler(log_filename, mode="w", delay=False)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
)
logger.addHandler(file_handler)

def main():
    """
    Main entry point for the Debugger Server application.
    """
    args = parse_arguments(logger)
    server = AgentStepperCore(host=args.host, client_port=args.client_port, ui_port=args.ui_port, model=args.model, logger=logger)
    
    if args.runs:
        load_runs(logger, server, args.runs)
        
    logger.info('Starting debugger server...')
    server.start()
    
    logger.info('Press Ctrl+C to stop...')
    stop_event = threading.Event()
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        logger.info('Shutdown signal received...')
        server.stop()

if __name__ == '__main__':
    main()