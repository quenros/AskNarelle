import logging

class Logger:
    """
    Singleton Logger class.
    Logs messages to both a file and console.
    """
    _instance = None

    def __new__(cls):
        """
        Ensures Singleton pattern.

        Returns:
            Logger: Singleton Logger instance
        """
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Initialises the logger instance with file and stream handler.
        Logs are written to 'message.log' file.
        Logs are displayed in console
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler("message.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(message)s'))

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(message)s'))

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message):
        """
        Logs a message at the INFO level.

        Args:
            message (str): Message to be logged.
        """
        self.logger.info(message)

logger = Logger()
