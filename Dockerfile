# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Copy the Python scripts and the entrypoint script into the container
COPY drawio2clab.py /app/
COPY clab2drawio.py /app/
COPY requirements.txt /app/
COPY entrypoint.sh /app/
COPY styles/ /app/styles/
COPY lib/ /app/lib/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set the working directory in the container
WORKDIR /data

# Use the entrypoint script to handle script execution
ENTRYPOINT ["/app/entrypoint.sh"]
# CMD can be used to specify default arguments or left as it is to pass commands through the docker run command
