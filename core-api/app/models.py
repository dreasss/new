# Importing required modules
from datetime import datetime, timezone as UTC

# Example model definitions (update with actual models)

class ExampleModel:
    def __init__(self):
        # Using lambda to set default datetime value using UTC
        self.created_at = (lambda: datetime.now(UTC))()

class AnotherModel:
    def __init__(self):
        self.updated_at = (lambda: datetime.now(UTC))()  
