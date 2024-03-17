#!/bin/bash

# Execute the Python script based on the SCRIPT_NAME environment variable
# Pass all arguments to the script
python -u "/app/${SCRIPT_NAME}" "$@"
