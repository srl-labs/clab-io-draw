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
Usage: docker run -v "$(pwd)":/data ghcr.io/srl-labs/clab-io-draw -i INPUT_FILE

This tool automatically converts between .drawio and .yaml file formats for Container Lab diagrams.

Options:
  -i, --input    Specify the path to the input file. This can be either a .drawio or .yaml/.yml file.
  -o, --output   Specify the path for the output file. The output format is determined by the input file type.

Examples:
  Convert .drawio to .yaml: docker run -v "\$(pwd)":/data ghcr.io/srl-labs/clab-io-draw -i input.drawio -o output.yaml
  Convert .yaml to .drawio: docker run -v "\$(pwd)":/data ghcr.io/srl-labs/clab-io-draw -i input.yaml -o output.drawio

clab2drawio.py help:
$(python -u "/app/clab2drawio.py" -h)

drawio2clab.py help:
$(python -u "/app/drawio2clab.py" -h)
EOF
}

# Check if no arguments were provided or if help option is specified
if [ $# -eq 0 ] || [[ " $@ " =~ " -h " ]] || [[ " $@ " =~ " --help " ]]; then
  show_help
  exit 0
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
uv run python -u "/app/${script_name}" "$@"