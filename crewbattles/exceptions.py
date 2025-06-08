"""
crewbattles/exceptions.py
Custom exceptions for the crew management system
"""


class CrewError(Exception):
    """Base exception for crew-related errors"""
    pass


class CrewNotFoundError(CrewError):
    """Raised when a crew is not found"""
    def __init__(self, crew_name: str):
        self.crew_name = crew_name
        super().__init__(f"Crew '{crew_name}' not found")


class UserAlreadyInCrewError(CrewError):
    """Raised when user tries to join a crew but is already in one"""
    def __init__(self, user_id: int, current_crew: str):
        self.user_id = user_id
        self.current_crew = current_crew
        super().__init__(f"User {user_id} is already in crew '{current_crew}'")


class CrewPermissionError(CrewError):
    """Raised when user lacks permission for an action"""
    def __init__(self, action: str, required_role: str = None):
        self.action = action
        self.required_role = required_role
        message = f"Insufficient permissions for action: {action}"
        if required_role:
            message += f" (requires {required_role} role)"
        super().__init__(message)


class CrewValidationError(CrewError):
    """Raised when crew data validation fails"""
    def __init__(self, crew_name: str, errors: list):
        self.crew_name = crew_name
        self.errors = errors
        super().__init__(f"Validation failed for crew '{crew_name}': {', '.join(errors)}")


class CrewFullError(CrewError):
    """Raised when trying to join a full crew"""
    def __init__(self, crew_name: str, max_size: int):
        self.crew_name = crew_name
        self.max_size = max_size
        super().__init__(f"Crew '{crew_name}' is full (max {max_size} members)")


class InviteExpiredError(CrewError):
    """Raised when trying to use an expired invitation"""
    def __init__(self, invite_id: int):
        self.invite_id = invite_id
        super().__init__(f"Invitation {invite_id} has expired")


class RoleNotFoundError(CrewError):
    """Raised when a required Discord role is not found"""
    def __init__(self, role_type: str, role_id: int = None):
        self.role_type = role_type
        self.role_id = role_id
        message = f"Required {role_type} role not found"
        if role_id:
            message += f" (ID: {role_id})"
        super().__init__(message)


class DataCorruptionError(CrewError):
    """Raised when crew data appears to be corrupted"""
    def __init__(self, details: str):
        super().__init__(f"Data corruption detected: {details}")


class BackupError(CrewError):
    """Raised when backup operations fail"""
    def __init__(self, operation: str, details: str):
        super().__init__(f"Backup {operation} failed: {details}")


class SyncError(CrewError):
    """Raised when data synchronization fails"""
    def __init__(self, crew_name: str, details: str):
        super().__init__(f"Sync failed for crew '{crew_name}': {details}")