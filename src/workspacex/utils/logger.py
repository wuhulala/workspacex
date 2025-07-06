import logging

import coloredlogs

logger = logging.getLogger("workspacex")
logger.setLevel(logging.DEBUG)

coloredlogs.install(
    level='DEBUG',
    logger=logger,
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
