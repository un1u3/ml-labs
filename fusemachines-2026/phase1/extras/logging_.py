# logging is the way of recording messages 
# logging means keeping logs 


# BAD: Using print()
print("Model trained")
print("Error occurred")
print("Processing file...")

# GOOD: Using logging

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Now use it
logging.debug("This is a debug message")
logging.info("Model training started")
logging.warning("Learning rate is very high")
logging.error("File not found")
logging.critical("System failure")