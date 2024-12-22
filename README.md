# clab-io-draw

The `clab-io-draw` project unifies two tools, `clab2drawio` and `drawio2clab`. These tools facilitate the conversion between [Containerlab](https://github.com/srl-labs/containerlab) YAML files and Draw.io diagrams, making it easier for network engineers and architects to visualize, document, and share their network topologies.

<div style="text-align: center;">
  <img src="./docs/img/st.clab.drawio.svg" alt="Drawio Example">
</div>



## Overview

|  Tool         |  Description                                                                                       |
| :-----------: | :------------------------------------------------------------------------------------------------: |
| **clab2drawio** | Converts Containerlab YAML files into Draw.io diagrams (with optional [Grafana](docs/grafana.md) support).  |
| **drawio2clab** | Converts Draw.io diagrams back into Containerlab-compatible YAML files, supporting quick lab setup.|


> [!NOTE]
> For detailed information on `clab2drawio`, options, and usage instructions, please refer to the [clab2drawio.md](docs/clab2drawio.md)

> [!NOTE]
> For more details on `drawio2clab`, including features, constraints for drawing, and how to run the tool, please see the [drawio2clab.md](docs/drawio2clab.md) 


## Quick Usage

### Running with Containerlab
```bash
containerlab graph --drawio -t topo.clab.yml
containerlab graph --drawio -t topo.clab.drawio
```

> [!TIP]  
> The `containerlab graph --drawio` command simplifies your workflow by automatically detecting the input file type (`.yml` or `.drawio`) and running the appropriate script internally (`clab2drawio` or `drawio2clab`).  
> 
> You can also enhance your output by passing additional arguments. For example:  
> ~~~bash
> sudo containerlab graph --drawio -t topo.clab.yml --drawio-args "--theme nokia_modern"
> ~~~  
> This example applies the "nokia_modern" theme to your generated diagram. 


### Running with Docker

You can also use a Docker container for a quick start without installing Python and other dependencies locally.


#### Pulling from Container registry

```bash
docker pull ghcr.io/srl-labs/clab-io-draw:latest
```

#### Running the Tools

Run drawio2clab or clab2drawio within a Docker container by mounting the directory containing your .drawio/.yaml files as a volume. Specify the input and output file paths relative to the mounted volume:

```bash
docker run -it -v "$(pwd)":/data ghcr.io/srl-labs/clab-io-draw -i lab-examples/br01.clab.yml
```
> [!NOTE]
> The `-it` option is used for interactive mode (`-I`). 
> If you do not need interactive prompts, you can omit `-it`.

```bash
docker run -v "$(pwd)":/data ghcr.io/srl-labs/clab-io-draw -i output.drawio
```

Replace `your_input_file.drawio` or `your_output_file.yaml` with the 
actual file names in your environment.

## Running locally

> [!IMPORTANT]  
> Python 3.6+ is required if you prefer running these tools locally.

### Installation

#### Virtual Environment Setup

> [!TIP]
> Using a virtual environment is recommended to avoid version conflicts 
> with global Python packages.

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

- `-i, --input`: path to your `.drawio` file.
- `-o, --output`: path to your output `.yaml` file (optional).

> [!NOTE]
> For more details on node-label constraints, usage examples, and additional 
> command-line options, refer to 
> [drawio2clab.md](docs/drawio2clab.md#usage).

## clab2drawio

```bash
python clab2drawio.py -i <input_file.yaml>
```

- `-i, --input`: path to your Containerlab YAML file.
- `-o, --output`: path to your output `.drawio` file (optional).

> [!NOTE]
> For advanced functionality—like 
> [Grafana Dashboard](docs/grafana.md) generation (`-g, --gf_dashboard`),interactive mode (`-I`), layout customizations, or theming (`--theme`) refer to [clab2drawio.md](docs/clab2drawio.md#usage).
