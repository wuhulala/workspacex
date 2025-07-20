import asyncio
import logging
import threading
from typing import Optional


# Custom formatter to include thread name and coroutine task id
class ThreadTaskFormatter(logging.Formatter):
    """
    Custom formatter that includes thread name and coroutine task id in log messages.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with thread name and coroutine task id.
        
        Args:
            record (logging.LogRecord): The log record to format.
            
        Returns:
            str: Formatted log message with thread and task information.
        """
        # Get current thread name
        thread_name = threading.current_thread().name
        
        # Get current coroutine task id if in async context
        task_id = "Sync"
        try:
            current_task = asyncio.current_task()
            if current_task:
                task_id = f"Task-{id(current_task)}"
        except RuntimeError:
            # Not in async context
            pass
        
        # Create the formatted message
        formatted = super().format(record)
        
        # Insert thread and task info before the message
        thread_task_info = f"[{thread_name}:{task_id}]"
        return formatted.replace(record.getMessage(), f"{thread_task_info} {record.getMessage()}")

# Create logger
logger = logging.getLogger("workspacex")

# Create custom formatter
formatter = ThreadTaskFormatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create console handler with custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Configure logger
logger.addHandler(console_handler)

# Remove any existing handlers to avoid duplication
for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler) and handler != console_handler:
        logger.removeHandler(handler)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name (Optional[str]): Logger name. If None, returns the main workspacex logger.
        
    Returns:
        logging.Logger: Logger instance with thread and task information.
    """
    if name is None:
        return logger
    
    # Create a new logger with the same configuration
    new_logger = logging.getLogger(f"workspacex.{name}")

    # Add the same formatter
    if not new_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        new_logger.addHandler(handler)
    
    return new_logger
