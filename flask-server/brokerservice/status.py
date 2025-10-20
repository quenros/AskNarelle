from enum import Enum

class Status(Enum):
    IN_PROGRESS = "PENDING"
    ERROR = "FAILED"
    COMPLETED = "COMPLETED"