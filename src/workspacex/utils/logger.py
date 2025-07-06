import logging

import coloredlogs

# Configure colored logging with custom format
coloredlogs.install(
    level=logging.DEBUG,
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level_styles={
        'debug': {'color': 'cyan'},
        'info': {'color': 'green'},
        'warning': {'color': 'yellow'},
        'error': {'color': 'red'},
        'critical': {'color': 'red', 'bold': True}
    },
    field_styles={
        'asctime': {'color': 'blue'},
        'name': {'color': 'magenta'},
        'levelname': {'color': 'white', 'bold': True}
    }
)

# Create a custom logger for this module
logger = logging.getLogger("workspacex")
