from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    DATA_STEWARD = "data_steward"
    VIEWER = "viewer"


class ActionType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RESTORE = "RESTORE"
