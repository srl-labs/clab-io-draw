import argparse
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import yaml
import re
import os

def report_error(message):
    """Prints an error message to the console."""
    print(f"Error: {message}")

def parse_xml(file_path, diagram_name=None):
    """
    Parses an XML file and returns the mxGraphModel/root element for the specified diagram name.
    If no diagram name is specified or the specified diagram is not found, defaults to the first diagram.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    # If a diagram name is specified, try to find the diagram by name
    if diagram_name:
        for diagram in root.findall('diagram'):
            if diagram.get('name') == diagram_name:
                # Directly navigate to the mxGraphModel/root within the selected diagram
                mxGraphModel_root = diagram.find('.//mxGraphModel/root')
                if mxGraphModel_root is not None:
                    return mxGraphModel_root
                else:
                    print(f"mxGraphModel/root not found in diagram '{diagram_name}'.")
                    return None
        print(f"Diagram named '{diagram_name}' not found.")
        return None

    # Default to the first diagram if no name is specified
    first_diagram = root.find('diagram')
    if first_diagram is not None:
        mxGraphModel_root = first_diagram.find('.//mxGraphModel/root')
        if mxGraphModel_root is not None:
            return mxGraphModel_root
        else:
            print("mxGraphModel/root not found in the first diagram.")
            return None

    print("No diagrams found in the file.")
    return None

def extract_nodes(mxGraphModel):
    """
    Extracts and returns node names and their IDs from the mxGraphModel.
    Handles both standalone mxCell elements with their own IDs and
    object elements with embedded mxCell, using the object's ID.
    """
    node_details = {}
    
    # Process all objects which might contain nodes or represent nodes directly
    for obj in mxGraphModel.findall(".//object"):
        node_id = obj.get('id')
        node_label = obj.get('label', '').strip()
        node_type = obj.get('type', None)  # Capture the 'type' attribute
        mgmt_ipv4 = obj.get('mgmt-ipv4', None)
        group = obj.get('group', None)
        labels = obj.get('labels', None)  # Assuming 'labels' is stored directly; adjust if it's more complex
        node_kind = obj.get('kind', 'nokia_srlinux')

        # If label is not directly on the object, try to find it in a child mxCell
        if not node_label:
            mxCell = obj.get('mxCell')
            if not mxCell:
                continue
            if mxCell is not None:
                node_label = mxCell.get('value', '').strip()
        # Add to node_details if a label was found
        if node_label:
            node_details[node_id] = {
                'label': node_label, 
                'type': node_type,
                'mgmt-ipv4': mgmt_ipv4,
                'group': group,
                'labels': labels,
                'kind': node_kind
            }

    # Process all mxCell elements that have vertex='1'
    for mxCell in mxGraphModel.findall(".//mxCell[@vertex='1']"):
        node_id = mxCell.get('id')
        # Ensure this mxCell is not a descendant of an object element
        if mxCell.find("ancestor::object") is None and node_id not in node_details:
            node_label = mxCell.get('value', '').strip()
            style = mxCell.get('style', '')
            if not "image=data" in style:
                continue
            if node_label:
                node_details[node_id] = {
                    'label': node_label,
                    'kind': node_kind
                }

    return node_details


def extract_links(mxGraphModel, node_details):
    """
    Extracts link information from the mxGraphModel, including source, target,
    and any geometric data. Links are represented by mxCell elements with a source and target.
    """
    links_info = {}
    if mxGraphModel:
        # Process links defined directly within mxGraphModel
        for mxCell in mxGraphModel.findall(".//mxCell[@source][@target][@edge]"):
            link_info = extract_link_info(mxCell, node_details)
            if link_info:
                links_info[link_info['id']] = link_info

        # Process links defined within objects
        for object_elem in mxGraphModel.findall(".//object"):
            mxCells = object_elem.findall(".//mxCell[@source][@target][@edge]")
            for mxCell in mxCells:
                # Use the object's ID as a fallback if the mxCell lacks an ID
                object_id = object_elem.get('id')
                link_info = extract_link_info(mxCell, node_details, fallback_id=object_id)
                if link_info:
                    links_info[link_info['id']] = link_info

    return links_info

def extract_link_info(mxCell, node_details, fallback_id=None):
    """
    Extracts information for a single link from an mxCell element,
    including its source, target, and geometry. 
    """
    source_id, target_id = mxCell.get('source'), mxCell.get('target')
    link_id = mxCell.get('id') or fallback_id
    geometry = mxCell.find('mxGeometry')
    x, y = (float(geometry.get(coord, 0)) for coord in ('x', 'y')) if geometry is not None else (None, None)

    # Adjusted to access 'label' from node_details
    source_label = node_details.get(source_id, {}).get('label', "Unknown")
    target_label = node_details.get(target_id, {}).get('label', "Unknown")

    if link_id:
        return {
            'id': link_id,
            'source': source_label,
            'target': target_label,
            'geometry': {'x': x, 'y': y},
            'labels': []
        }

def extract_link_labels(mxGraphModel, links_info):
    """
    Enhances links with label information, including the label's value and geometric position.
    This function populates the labels array within each link's information.
    """
    for mxCell in mxGraphModel.findall(".//mxCell[@value]"):
        parent_id = mxCell.get('parent')
        if parent_id in links_info:
            label_value, geometry = mxCell.get('value'), mxCell.find("mxGeometry")
            if label_value and geometry is not None:
                x_position, y_position = float(geometry.get('x', 0)), float(geometry.get('y', 0))
                links_info[parent_id]['labels'].append({
                    'value': label_value,
                    'x_position': x_position,
                    'y_position': y_position
                })

def aggregate_node_information(node_details):
    """
    Aggregates node information by potentially modifying the 'kind' for each node based on specific criteria.
    If a 'kind' is explicitly provided, it is respected. If not, the function assigns 'linux' to nodes
    with 'client' in their label, maintaining other kinds as defined or defaulting to 'nokia_srlinux'.
    """
    updated_node_details = {}
    for node_id, details in node_details.items():
        # Use the existing 'kind' if it's explicitly defined and not default 'nokia_srlinux', or
        # apply custom logic to determine 'kind'.
        if details.get('kind') and details.get('kind') != 'nokia_srlinux':
            # 'kind' is explicitly provided, so we keep it.
            node_kind = details['kind']
        else:
            # Apply custom logic: if 'client' in label, set as 'linux'; otherwise, keep existing or default to 'nokia_srlinux'.
            node_kind = 'linux' if 'client' in details['label'] else details.get('kind', 'nokia_srlinux')
        
        # Update node details with potentially modified 'kind'.
        updated_details = details.copy()
        updated_details['kind'] = node_kind
        updated_node_details[node_id] = updated_details

    return updated_node_details

def compile_link_information(links_info, style='block'):
    """
    Compiles and formats link information into a structured format. 
    When there are three or more labels on a link, only the labels closest to the source and destination are considered.
    The 'style' parameter determines the format of the endpoints in the output.
    """
    compiled_links = []
    for link_id, info in links_info.items():
        sorted_labels = sorted(info['labels'], key=lambda label: label['x_position'])
        
        # Handle insufficient labels gracefully
        if len(sorted_labels) < 2:
            report_error(f"Not enough labels for link {link_id}. At least 2 labels are required.")
            continue  # Skip this link

        source_label = sorted_labels[0]['value']
        target_label = sorted_labels[-1]['value']
        
        if style == 'block':
            endpoints = [f"{info['source']}:{source_label}", f"{info['target']}:{target_label}"]
        elif style == 'flow':
            # For flow style, prepare endpoints in a list first for consistent sorting
            endpoints_list = [f"{info['source']}:{source_label}", f"{info['target']}:{target_label}"]
            # Ensure consistent sorting for flow style before converting to string
            endpoints_list.sort(key=lambda x: x.split(':')[0])
            endpoints = f"[\"{endpoints_list[0]}\", \"{endpoints_list[1]}\"]"
            
        compiled_links.append({'endpoints': endpoints})

    # Sort the compiled_links list by the source of the endpoint
    compiled_links.sort(key=lambda x: (x['endpoints'][0].split(':')[0] if style == 'block' else x['endpoints']))

    return compiled_links


def filter_nodes(links_info, node_details):
    """
    Filters nodes to include only those nodes involved in the links, based on their labels.
    This helps to eliminate any nodes that are not part of the actual topology being described.
    """
    # Collect labels of nodes involved in links
    involved_labels = {info['source'] for info in links_info.values()} | {info['target'] for info in links_info.values()}

    # Filter node_details to include only those nodes with labels involved in links
    filtered_details = {node_id: details for node_id, details in node_details.items() if details['label'] in involved_labels}

    return filtered_details

def generate_yaml_structure(filtered_node_details, compiled_links, input_file):
    """
    Generates the final YAML structure based on filtered node details and compiled link information,
    omitting the 'type' key for nodes where it is not explicitly provided.
    """
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    nodes = {}
    kinds = {}

    for node_id, details in filtered_node_details.items():
        node_label = details['label']
        node_kind = details['kind']

        # Dynamically construct the kinds dictionary with default settings for known kinds
        if node_kind not in kinds:
            kinds[node_kind] = {'image': 'ghcr.io/nokia/srlinux', 'type': 'ixrd3'} if node_kind == 'nokia_srlinux' \
                else {'image': 'ghcr.io/hellt/network-multitool'} if node_kind == 'linux' \
                else {'image' : None }  # Add more conditions as necessary for other kinds

        # Prepare node information, conditionally including 'type' if it exists and is not None
        node_info = {'kind': node_kind}
        if details.get('type'):
            node_info['type'] = details['type']

        # Optionally add other details if they exist and are not None
        for attr in ['mgmt-ipv4', 'group', 'labels']:
            attr_value = details.get(attr)
            if attr_value is not None:  # Check for None to exclude 'null' values
                node_info[attr] = attr_value

        # Assign the node information to the node label, ensuring no null values are included
        nodes[node_label] = node_info

    return {
        'name': base_name,
        'topology': {
            'kinds': kinds,
            'nodes': nodes,
            'links': compiled_links
        }
    }

def write_yaml_file(yaml_data, file_name, style='block'):
    """
    Writes the generated YAML structure to a file. Adjusts the style of lists based on the 'style' argument.
    """

    with open(file_name, 'w') as file:
        yaml.dump(yaml_data, file, default_flow_style=False, sort_keys=False)
    print(f"YAML file generated successfully at {file_name}.")


def post_process_yaml_file_for_flow_style(file_name):
    """
    Post-processes the YAML file to ensure 'endpoints' within 'links' are in flow style without single quotes.
    """
    # Read the original YAML content
    with open(file_name, 'r') as file:
        content = file.read()

    # Regular expression to match 'endpoints' lines with single-quoted flow-style lists
    # Note the use of triple quotes to allow for internal single and double quotes without needing to escape them
    pattern = re.compile(r"""- endpoints: '\["([^"]+)", "([^"]+)"\]'""")

    # Function to replace matched patterns with unquoted flow-style lists
    def replace_with_unquoted_flow_style(match):
        # Extracting the two endpoint items
        endpoint1, endpoint2 = match.group(1), match.group(2)
        # Formatting as an unquoted flow-style list
        return f'  - endpoints: ["{endpoint1}", "{endpoint2}"]'

    # Replace the matched patterns with unquoted flow-style lists
    new_content = pattern.sub(replace_with_unquoted_flow_style, content)

    # Write the modified content back to the file
    with open(file_name, 'w') as file:
        file.write(new_content)
        

def main(input_file, output_file, style='block', diagram_name=None):
    """
    The main function orchestrates the parsing, extraction, and processing of .drawio XML content,
    and then generates and writes the YAML file. It ties together all the steps necessary to convert
    .drawio diagrams into YAML-based network topologies.
    """
    if not output_file:
        output_file = os.path.splitext(input_file)[0] + ".yaml"

    root = parse_xml(input_file, diagram_name)
    node_details = extract_nodes(root)
    links_info = extract_links(root, node_details)
    extract_link_labels(root, links_info)

    # Debug print for links info with label geometry
    print("Links Info with Label Geometry:")
    for link_id, info in links_info.items():
        labels_str = "; ".join([f"{label['value']} (x: {label['x_position']}, y: {label['y_position']})" for label in info.get('labels', [])])
        print(f"Link ID: {link_id}, Source: {info['source']}, Target: {info['target']}, Labels: {labels_str}")


    node_details = aggregate_node_information(node_details)
    compiled_links = compile_link_information(links_info, style)
    filtered_nodes = filter_nodes(links_info, node_details)
    yaml_data = generate_yaml_structure(filtered_nodes, compiled_links, input_file)
    write_yaml_file(yaml_data, output_file, style)
    if style == "flow":
        post_process_yaml_file_for_flow_style(output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a draw.io XML file and generate a YAML file with a specified style.")
    parser.add_argument("-i", "--input", dest="input_file", required=True, help="The input XML file to be parsed.")
    parser.add_argument("-o", "--output", dest="output_file", required=False, help="The output YAML file.")
    parser.add_argument("--style", dest="style", choices=['block', 'flow'], default="block", help="The style for YAML endpoints. Choose 'block' or 'flow'. Default is 'block'.")
    parser.add_argument("--diagram-name", dest="diagram_name", required=False, help="The name of the diagram (tab) to be parsed.")

    args = parser.parse_args()

    main(args.input_file, args.output_file, args.style, args.diagram_name)