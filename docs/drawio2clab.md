# Drawio2Clab

**`drawio2clab`** converts `.drawio` (XML) diagrams back into Containerlab-compatible
YAML files. This allows you to plan and sketch topologies in Draw.io, then easily 
deploy them in a containerized lab environment.

> [!NOTE]
> For best results, ensure that your Draw.io nodes and links are well-labeled and that custom properties (for node kind, management IP, etc.) are used consistently.

## Features

- Converts .drawio diagrams to Containerlab-compatible YAML.
- Supports specifying node details (e.g., `type`, `kind`, `mgmt-ipv4`, `labels`) 
  directly in Draw.io.
- Allows selection of a specific diagram within a multi-page `.drawio` file.
- Output can be in `block` or `flow` style YAML.



## Drawing Constraints

> [!IMPORTANT]
> Label your nodes and links properly. Node attributes can be added in Draw.io 
> as custom properties (`<property>=<value>`), which `drawio2clab` will parse.

- **Node Labeling**: Click on a node and start typing to label it.
- **Link Labeling**: Double-click on a link to add a label (closest labels to 
  each endpoint are used).
- **Node Data**: Provide extra data (like `type`, `kind`, or `labels`) in 
  the `custom properties` panel in Draw.io.
  
- **Adding Node Data**
In addition to labeling, nodes can contain additional data to further define the network configuration. The following attributes can be added to a node:

  - `type`: Specify the type of the node. E.g., "ixrd2", "ixrd3".
  - `kind`: Specify the kind of the node, by default nokia_srlinux
  - `mgmt-ipv4`: Assign a management IPv4 address to the node.
  - `group`: Define a group to which the node belongs.
  - `labels`: Add custom labels for additional metadata or categorization.
---

<p align="center">
  <img src="./img/drawio1.png" alt="Drawio Example">
</p>


The above image demonstrates how to correctly label nodes and links and add additional data to nodes for conversion.


## Usage
Convert a .drawio file to YAML:

```bash
uv run python drawio2clab.py -i input_file.drawio
```

> [!TIP]
> If your `.drawio` file has multiple diagrams, use 
> `--diagram-name "Diagram 1"` to specify which one to process.

### Arguments

- `-i, --input`: Path to `.drawio` XML file.
- `-o, --output`: Path to the output YAML file.
- `--style`: YAML style (`block` or `flow`). Default is `flow`.
- `--diagram-name`: Name of the diagram to parse if multiple diagrams exist.
- `--default-kind`: Default kind for nodes (e.g., `nokia_srlinux`).

## Further Documentation & References

- [Containerlab Documentation](https://containerlab.dev)
- [clab2drawio.md](./clab2drawio.md)
- [drawio2clab.md](./drawio2clab.md)
- [grafana.md](./grafana.md)
