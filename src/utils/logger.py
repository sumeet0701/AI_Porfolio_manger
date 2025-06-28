import time
import functools
import logging
import os
import asyncio
import requests
from datetime import datetime
from typing import Optional, Union, Callable, Any
from concurrent.futures import ThreadPoolExecutor

class Logger:
    """
    An enhanced logger class that combines logging, execution timing, and daily log file creation.
    """

    def __init__(self, log_filename: str, log_level: str = "all", log_dir: str = "logs"):
        """
        Initialize the enhanced logger.

        Args:
            log_filename (str): Base name for the log file (without extension)
            log_level (str): Log level filter - 'debug', 'info', 'warning', 'error', 'critical', or 'all'
            log_dir (str): Directory to store log files (default: 'logs')
        """
        self.log_filename = log_filename
        self.log_level = log_level.upper()
        self.log_dir = log_dir
        self.logger = None

        # Create log directory if it doesn't exist
        self._create_log_directory()

        # Setup the logger
        self._setup_logger()

    def _create_log_directory(self):
        """Create the log directory if it doesn't exist."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _get_log_filename_with_timestamp(self) -> str:
        """
        Generate log filename with current date and time.

        Returns:
            str: Formatted filename with timestamp
        """
        current_time = datetime.now().strftime("%Y-%m-%d")
        return f"{self.log_filename}_{current_time}.log"

    def _setup_logger(self):
        """Setup the logger with appropriate handlers and formatters."""
        # Create a unique logger name to avoid conflicts
        logger_name = f"{self.log_filename}_{datetime.now().strftime('%Y%m%d')}"
        self.logger = logging.getLogger(logger_name)

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Set the base logger level to DEBUG to capture all logs
        self.logger.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Create file handler with timestamp
        log_file_path = os.path.join(self.log_dir, self._get_log_filename_with_timestamp())
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)

        # Create console handler for real-time monitoring
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Set log level for handlers based on user input
        if self.log_level == "ALL":
            file_handler.setLevel(logging.DEBUG)
            console_handler.setLevel(logging.DEBUG)
        else:
            level_mapping = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }

            if self.log_level in level_mapping:
                file_handler.setLevel(level_mapping[self.log_level])
                console_handler.setLevel(level_mapping[self.log_level])
            else:
                # Default to INFO if invalid level provided
                file_handler.setLevel(logging.INFO)
                console_handler.setLevel(logging.INFO)
                self.logger.warning(f"Invalid log level '{self.log_level}'. Using INFO level.")

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Log initialization message
        self.logger.info(f"Logger initialized with level: {self.log_level}")
        self.logger.info(f"Log file: {log_file_path}")

    def debug(self, message: str):
        """Log a debug message."""
        self.logger.debug(message)

    def info(self, message: str):
        """Log an info message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message: str):
        """Log an error message."""
        self.logger.error(message)

    def critical(self, message: str):
        """Log a critical message."""
        self.logger.critical(message)

    def log(self, level: str, message: str):
        """
        Log a message with specified level.

        Args:
            level (str): Log level ('debug', 'info', 'warning', 'error', 'critical')
            message (str): Message to log
        """
        level = level.upper()
        level_methods = {
            "DEBUG": self.debug,
            "INFO": self.info,
            "WARNING": self.warning,
            "ERROR": self.error,
            "CRITICAL": self.critical
        }

        if level in level_methods:
            level_methods[level](message)
        else:
            self.warning(f"Invalid log level '{level}'. Message: {message}")

    def time_logger(self, include_args: bool = False, threshold_seconds: Optional[float] = None):
        """
        Decorator to measure execution time of functions.

        Args:
            include_args (bool): Whether to log function arguments
            threshold_seconds (float): Only log if execution time exceeds this threshold
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                func_name = f"{func.__module__}.{func.__name__}" if func.__module__ != '__main__' else func.__name__

                # Log function start
                start_msg = f"🚀 Starting execution: {func_name}"
                if include_args:
                    start_msg += f" | Args: {args} | Kwargs: {kwargs}"

                self.logger.debug(start_msg)

                # Measure execution time
                start_time = time.perf_counter()
                start_timestamp = datetime.now()

                try:
                    result = func(*args, **kwargs)

                    # Calculate execution time
                    end_time = time.perf_counter()
                    execution_time = end_time - start_time

                    # Log successful completion
                    self._log_execution_time(func_name, execution_time, start_timestamp, True)

                    return result

                except Exception as e:
                    # Calculate execution time for failed function
                    end_time = time.perf_counter()
                    execution_time = end_time - start_time

                    # Log failed execution
                    self._log_execution_time(func_name, execution_time, start_timestamp, False, str(e))

                    # Re-raise the exception
                    raise

            return wrapper

        return decorator

    def _log_execution_time(self, func_name: str, execution_time: float,
                          start_timestamp: datetime, success: bool, error_msg: str = None):
        """Log the execution time with detailed information."""
        # Check threshold
        if self.threshold_seconds and execution_time < self.threshold_seconds:
            return

        # Format execution time
        if execution_time < 1:
            time_str = f"{execution_time * 1000:.2f}ms"
        elif execution_time < 60:
            time_str = f"{execution_time:.3f}s"
        else:
            minutes = int(execution_time // 60)
            seconds = execution_time % 60
            time_str = f"{minutes}m {seconds:.3f}s"

        # Create status indicator
        status = "✅ SUCCESS" if success else "❌ FAILED"

        # Build log message
        log_msg = f"{status} | Function: {func_name} | Execution Time: {time_str} | Started: {start_timestamp.strftime('%H:%M:%S')}"

        if not success and error_msg:
            log_msg += f" | Error: {error_msg}"

        # Determine log level based on execution time and success
        if not success:
            log_level = 'error'
        elif execution_time > 10:  # Slow execution
            log_level = 'warning'
        elif execution_time > 5:  # Moderate execution
            log_level = 'info'
        else:
            log_level = self.log_level.lower()

        self.log(log_level, log_msg)

    def measure_api_call(self, url: str, method: str = "GET", **kwargs) -> dict:
        """
        Measure time for API calls using requests.

        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            **kwargs: Additional arguments for requests

        Returns:
            dict: Response data with timing information
        """
        start_time = time.perf_counter()
        start_timestamp = datetime.now()

        try:
            self.logger.info(f"🌐 API Call Started: {method} {url}")

            # Make the API call
            response = requests.request(method, url, **kwargs)

            # Calculate timing
            end_time = time.perf_counter()
            execution_time = end_time - start_time

            # Format time
            if execution_time < 1:
                time_str = f"{execution_time * 1000:.2f}ms"
            else:
                time_str = f"{execution_time:.3f}s"

            # Log result
            status_icon = "✅" if response.status_code < 400 else "❌"
            self.logger.info(f"{status_icon} API Response: {method} {url} | "
                           f"Status: {response.status_code} | "
                           f"Time: {time_str} | "
                           f"Size: {len(response.content)} bytes")

            return {
                'response': response,
                'execution_time': execution_time,
                'status_code': response.status_code,
                'start_time': start_timestamp,
                'end_time': datetime.now()
            }

        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            time_str = f"{execution_time * 1000:.2f}ms" if execution_time < 1 else f"{execution_time:.3f}s"

            self.logger.error(f"❌ API Call Failed: {method} {url} | "
                            f"Time: {time_str} | "
                            f"Error: {str(e)}")

            raise
