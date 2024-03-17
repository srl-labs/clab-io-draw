#!/bin/bash

# Navigate to the script directory
cd /app

# Execute the Python script based on the SCRIPT_NAME environment variable
# Pass all arguments to the script
python -u "./${SCRIPT_NAME}" "$@"
