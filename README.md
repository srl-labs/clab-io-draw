# clab-io-draw

The `clab-io-draw` project unifies two tools, `clab2drawio` and `drawio2clab`. These tools facilitate the conversion between [Containerlab](https://github.com/srl-labs/containerlab) YAML files and Draw.io diagrams, making it easier for network engineers and architects to visualize, document, and share their network topologies.

![Drawio Example](docs/img/drawio1.png)

## clab2drawio

`clab2drawio` is a Python script that automatically generates Draw.io diagrams from Containerlab YAML configurations. It aims to simplify the visualization of network designs by providing a graphical representation of container-based network topologies.

For detailed information on `clab2drawio`, including features, options, and usage instructions, please refer to the [clab2drawio.md](docs/clab2drawio.md) file located in the same directory as this README.

## drawio2clab

`drawio2clab` is a Python script that converts Draw.io diagrams into Containerlab-compatible YAML files. This tool is designed to assist in the setup of container-based networking labs by parsing .drawio XML files and generating structured YAML representations of the network.

For more details on `drawio2clab`, including features, constraints for drawing, and how to run the tool, please see the [drawio2clab.md](docs/drawio2clab.md) file in this directory.

## Quick Usage

### Running with Docker

To simplify dependency management and execution, the tools can be run inside a Docker container. Follow these instructions to build and run the tool using Docker.

#### Pulling from dockerhub

```bash
docker pull ghcr.io/srl-labs/clab-io-draw:latest
```

#### Running the Tools

Run drawio2clab or clab2drawio within a Docker container by mounting the directory containing your .drawio/.yaml files as a volume. Specify the input and output file paths relative to the mounted volume:

```bash
docker run -v "$(pwd)":/data ghcr.io/srl-labs/clab-io-draw -i lab-examples/clos03/cfg-clos.clab.yml
```

```bash
docker run -v "$(pwd)":/data ghcr.io/srl-labs/clab-io-draw -i output.drawio
```

Replace your_input_file.drawio and your_output_file.yaml with the names of your actual files. This command mounts your current directory to /data inside the container.

## Running locally

### Requirements

- Python 3.6+

### Installation

#### Virtual Environment Setup

It's recommended to use a virtual environment for Python projects. This isolates your project dependencies from the global Python environment. To set up and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  
```

#### Installing Dependencies

After activating the virtual environment, install the required packages from the requirements.txt file:

```bash
pip install -r requirements.txt
```

# Usage

This section provides a brief overview on how to use the `drawio2clab` and `clab2drawio` tools. For detailed instructions, including command-line options and examples, please refer to the dedicated usage sections in their respective documentation files.

Detailed Usages: [drawio2clab.md](docs/drawio2clab.md#usage) and [clab2drawio.md](docs/clab2drawio.md#usage)

## drawio2clab

```bash
python drawio2clab.py -i <input_file.drawio>
```

`-i, --input`: Specifies the path to your input .drawio file.
Make sure to replace `<input_file.drawio>` with the path to your .drawio file

For more comprehensive guidance, including additional command-line options, please see the Usage section in [drawio2clab.md](docs/drawio2clab.md#usage)

## clab2drawio

```bash
python clab2drawio.py -i <input_file.yaml>
```

`-i, --input`: Specifies the path to your input YAML file.
`-o, --output`: Specifies the path for the output drawio file.
Make sure to replace `<input_file.yaml>` with the path to your .drawio file 

For more comprehensive guidance, including additional command-line options, please see the Usage section in [clab2drawio.md](docs/clab2drawio.md#usage)
