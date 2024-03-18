#!/bin/bash

# Function to extract file extension
get_extension() {
  filename=$(basename -- "$1")
  extension="${filename##*.}"
  echo $extension
}

# Function to show help message
show_help() {
cat << EOF
Usage: docker run [DOCKER_OPTIONS] flosch62/clab-io-draw -i INPUT_FILE -o OUTPUT_FILE

This tool automatically converts between .drawio and .yaml file formats for Container Lab diagrams.

Options:
  -i, --input    Specify the path to the input file. This can be either a .drawio or .yaml/.yml file.
  -o, --output   Specify the path for the output file. The output format is determined by the input file type.

Examples:
  Convert .drawio to .yaml: docker run -v "\$(pwd)":/data flosch62/clab-io-draw -i input.drawio -o output.yaml
  Convert .yaml to .drawio: docker run -v "\$(pwd)":/data flosch62/clab-io-draw -i input.yaml -o output.drawio
EOF
}

# Check if no arguments were provided
if [ $# -eq 0 ]; then
  show_help
  exit 1
fi

script_name=""
input_file=""
prev_arg=""

# Loop through all arguments
for arg in "$@"; do
  if [[ "$prev_arg" == "-i" || "$prev_arg" == "--input" ]]; then
    input_file="$arg"
  fi
  prev_arg="$arg"
done

# Check for help option
if [[ " $@ " =~ " -h " ]] || [[ " $@ " =~ " --help " ]]; then
  show_help
  exit 0
fi

# Determine the script based on file extension
if [ ! -z "$input_file" ]; then
  case $(get_extension "$input_file") in
    yml|yaml)
      script_name="clab2drawio.py"
      ;;
    drawio)
      script_name="drawio2clab.py"
      ;;
    *)
      echo "Unsupported file type: $input_file"
      exit 1
      ;;
  esac
else
  echo "No input file specified."
  exit 1
fi

# Execute the determined script with all passed arguments
python -u "/app/${script_name}" "$@"
