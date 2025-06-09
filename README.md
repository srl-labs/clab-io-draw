# clab-io-draw

The `clab-io-draw` project unifies two tools, `clab2drawio` and `drawio2clab`. These tools facilitate the conversion between [Containerlab](https://github.com/srl-labs/containerlab) YAML files and Draw.io diagrams, making it easier for network engineers and architects to visualize, document, and share their network topologies.

<p align="center">
  <img src="./docs/img/st.clab.drawio.svg" alt="Drawio Example">
</p>



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

You can also use a Docker container for a quick start without installing Python and other dependencies locally. The image already includes the draw.io AppImage, so no additional downloads are needed at runtime.


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
> Python 3.11+ is required if you prefer running these tools locally.

### Installation

> [!TIP]
> **Why uv?**
> [uv](https://docs.astral.sh/uv) is a single, ultra-fast tool that can replace `pip`, `pipx`, `virtualenv`, `pip-tools`, `poetry`, and more. It automatically manages Python versions, handles ephemeral or persistent virtual environments (`uv venv`), lockfiles, and often runs **10–100× faster** than pip installs.

1. **Install uv** (no Python or Rust needed):
    ```
    # On macOS and Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2. **Run the tool** (uv automatically installs dependencies in a venv from `pyproject.toml`):
    ```
    uv run python clab2drawio.py --help
    ```

## Alternative: Using pip

If you’d rather use pip or can’t install uv:

1. **(Optional) Create & Activate a Virtual Environment**:
    ```
    python -m venv venv
    source venv/bin/activate
    ```

2. **Installing Dependencies**

    After activating the virtual environment, install the required packages from the requirements.txt file:

    ```bash
    pip install -r requirements.txt
    ```
> [!NOTE]
> If you installed dependencies using pip instead of uv, simply run the commands using `python` directly instead of `uv run python`


# Usage

This section provides a brief overview on how to use the `drawio2clab` and `clab2drawio` tools. For detailed instructions, including command-line options and examples, please refer to the dedicated usage sections in their respective documentation files.

Detailed Usages: [drawio2clab.md](docs/drawio2clab.md#usage) and [clab2drawio.md](docs/clab2drawio.md#usage)

## drawio2clab

```bash
uv run python drawio2clab.py -i <input_file.drawio>
```

- `-i, --input`: path to your `.drawio` file.
- `-o, --output`: path to your output `.yaml` file (optional).

> [!NOTE]
> For more details on node-label constraints, usage examples, and additional 
> command-line options, refer to 
> [drawio2clab.md](docs/drawio2clab.md#usage).

## clab2drawio

```bash
uv run python clab2drawio.py -i <input_file.yaml>
```

- `-i, --input`: path to your Containerlab YAML file.
- `-o, --output`: path to your output `.drawio` file (optional).

> [!NOTE]
> For advanced functionality—like 
> [Grafana Dashboard](docs/grafana.md) generation (`-g, --gf_dashboard`),interactive mode (`-I`), layout customizations, or theming (`--theme`) refer to [clab2drawio.md](docs/clab2drawio.md#usage).

## Contributions & Feedback

All feedback and contributions are welcome! If you have suggestions, please open an issue or pull request on the GitHub repository.

---