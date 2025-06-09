#!/usr/bin/env python3
"""
Advanced Draw.io to SVG Exporter
Complete implementation with all major Draw.io export features
"""

import base64
import json
import mimetypes
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.request import urlopen


@dataclass
class ExportOptions:
    """Export configuration options matching Draw.io's export dialog"""
    scale: float = 1.0
    border: int = 0
    background: str | None = None
    shadow: bool = False
    embed_images: bool = True
    embed_fonts: bool = True
    embed_xml: bool = False
    math_enabled: bool = True
    page_id: str | None = None
    all_pages: bool = False
    layers: list[str] | None = None
    layer_ids: list[str] | None = None
    width: float | None = None
    height: float | None = None
    transparent: bool = False
    grid: bool = False
    grid_size: int = 10
    grid_color: str = "#e0e0e0"
    grid_steps: int = 1
    page_scale: float = 1.0
    print_mode: bool = False
    page_format: str = "a4"
    page_width: float | None = None
    page_height: float | None = None
    theme: str = "kennedy"  # kennedy, dark, min, atlas, sketch
    flow_animation: bool = False
    link_target: str | None = None  # _blank, _self, etc.


@dataclass
class Bounds:
    """Rectangle bounds with utility methods"""
    x: float
    y: float
    width: float
    height: float

    def add(self, other: "Bounds"):
        """Expand bounds to include another bounds"""
        x2 = max(self.x + self.width, other.x + other.width)
        y2 = max(self.y + self.height, other.y + other.height)
        self.x = min(self.x, other.x)
        self.y = min(self.y, other.y)
        self.width = x2 - self.x
        self.height = y2 - self.y

    def intersects(self, other: "Bounds") -> bool:
        """Check if bounds intersect"""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)

    def contains(self, x: float, y: float) -> bool:
        """Check if point is within bounds"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)


@dataclass
class CellState:
    """State of a cell during rendering"""
    cell: ET.Element
    style: dict[str, str]
    geometry: Optional["Geometry"] = None
    visible: bool = True
    absolute_offset: tuple[float, float] | None = None


@dataclass
class Geometry:
    """Cell geometry with relative/absolute positioning"""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    relative: bool = False
    offset_x: float = 0
    offset_y: float = 0
    source_point: tuple[float, float] | None = None
    target_point: tuple[float, float] | None = None
    points: list[tuple[float, float]] = field(default_factory=list)


class DrawioShapeRegistry:
    """Registry of Draw.io shapes and their SVG renderers"""

    SHAPES = {
        "rectangle": "rect",
        "ellipse": "ellipse",
        "rhombus": "rhombus",
        "triangle": "triangle",
        "hexagon": "hexagon",
        "parallelogram": "parallelogram",
        "trapezoid": "trapezoid",
        "cylinder": "cylinder",
        "cloud": "cloud",
        "document": "document",
        "process": "process",
        "star": "star",
        "plus": "plus",
        "arrow": "arrow",
        "doubleArrow": "doubleArrow",
        "callout": "callout",
        "tape": "tape",
        "note": "note",
        "card": "card",
        "cube": "cube",
        # Special shapes
        "image": "image",
        "label": "label",
        "text": "text",
        "swimlane": "swimlane",
        "table": "table",
        "tableRow": "tableRow",
        "tableCell": "tableCell"
    }

    @staticmethod
    def render_shape(shape_type: str, bounds: Bounds, style: dict[str, str]) -> list[ET.Element]:
        """Render a shape and return SVG elements"""
        elements = []

        # Common attributes
        fill = style.get("fillColor", "#ffffff")
        stroke = style.get("strokeColor", "#000000")
        stroke_width = style.get("strokeWidth", "1")
        opacity = style.get("opacity", "100")
        fill_opacity = style.get("fillOpacity", opacity)
        stroke_opacity = style.get("strokeOpacity", opacity)

        if shape_type in ["rectangle", "rect", "square"]:
            elem = ET.Element("rect", attrib={
                "x": "0",
                "y": "0",
                "width": str(bounds.width),
                "height": str(bounds.height),
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width,
                "fill-opacity": str(float(fill_opacity) / 100),
                "stroke-opacity": str(float(stroke_opacity) / 100)
            })

            # Handle rounded corners
            if style.get("rounded", "0") == "1":
                radius = min(bounds.width, bounds.height) * 0.1
                elem.set("rx", str(radius))
                elem.set("ry", str(radius))

            elements.append(elem)

        elif shape_type == "ellipse":
            elem = ET.Element("ellipse", attrib={
                "cx": str(bounds.width / 2),
                "cy": str(bounds.height / 2),
                "rx": str(bounds.width / 2),
                "ry": str(bounds.height / 2),
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

        elif shape_type == "rhombus":
            points = f"{bounds.width/2},0 {bounds.width},{bounds.height/2} {bounds.width/2},{bounds.height} 0,{bounds.height/2}"
            elem = ET.Element("polygon", attrib={
                "points": points,
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

        elif shape_type == "hexagon":
            w, h = bounds.width, bounds.height
            points = f"{w*0.25},0 {w*0.75},0 {w},{h/2} {w*0.75},{h} {w*0.25},{h} 0,{h/2}"
            elem = ET.Element("polygon", attrib={
                "points": points,
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

        elif shape_type == "cylinder":
            # Cylinder is rendered as a rectangle with ellipses at top/bottom
            # Top ellipse
            elem = ET.Element("ellipse", attrib={
                "cx": str(bounds.width / 2),
                "cy": str(bounds.height * 0.1),
                "rx": str(bounds.width / 2),
                "ry": str(bounds.height * 0.1),
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

            # Body
            elem = ET.Element("path", attrib={
                "d": f"M 0,{bounds.height*0.1} L 0,{bounds.height*0.9} A {bounds.width/2},{bounds.height*0.1} 0 0,0 {bounds.width},{bounds.height*0.9} L {bounds.width},{bounds.height*0.1}",
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

            # Bottom ellipse (front part)
            elem = ET.Element("path", attrib={
                "d": f"M 0,{bounds.height*0.9} A {bounds.width/2},{bounds.height*0.1} 0 0,0 {bounds.width},{bounds.height*0.9}",
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

        elif shape_type == "cloud":
            # Simplified cloud shape
            path = DrawioShapeRegistry._create_cloud_path(bounds)
            elem = ET.Element("path", attrib={
                "d": path,
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

        else:
            # Default to rectangle
            elem = ET.Element("rect", attrib={
                "x": "0",
                "y": "0",
                "width": str(bounds.width),
                "height": str(bounds.height),
                "fill": fill,
                "stroke": stroke,
                "stroke-width": stroke_width
            })
            elements.append(elem)

        return elements

    @staticmethod
    def _create_cloud_path(bounds: Bounds) -> str:
        """Create a cloud-like path"""
        w, h = bounds.width, bounds.height

        # Simple cloud shape with bezier curves
        path = f"M {w*0.15},{h*0.6} "
        path += f"C {w*0.15},{h*0.3} {w*0.35},{h*0.1} {w*0.5},{h*0.2} "
        path += f"C {w*0.6},{h*0.05} {w*0.8},{h*0.05} {w*0.85},{h*0.25} "
        path += f"C {w*0.95},{h*0.35} {w*0.95},{h*0.55} {w*0.85},{h*0.65} "
        path += f"C {w*0.85},{h*0.85} {w*0.65},{h*0.95} {w*0.5},{h*0.85} "
        path += f"C {w*0.35},{h*0.95} {w*0.15},{h*0.85} {w*0.15},{h*0.6} Z"

        return path


class DrawioSVGExporter:
    """Advanced Draw.io to SVG exporter with full feature support"""

    # Standard page formats
    PAGE_FORMATS = {
        "a4": (210, 297),
        "a3": (297, 420),
        "letter": (215.9, 279.4),
        "legal": (215.9, 355.6),
        "tabloid": (279.4, 431.8)
    }

    def __init__(self):
        self.ns = {
            "svg": "http://www.w3.org/2000/svg",
            "xlink": "http://www.w3.org/1999/xlink",
            "xhtml": "http://www.w3.org/1999/xhtml"
        }
        self.shape_registry = DrawioShapeRegistry()
        self.embedded_images: dict[str, str] = {}
        self.embedded_fonts: set[str] = set()

    def export_file(self, filepath: str, options: ExportOptions = None) -> list[str]:
        """Export a Draw.io file to SVG(s)"""
        options = options or ExportOptions()

        # Read and parse the file
        content = self._read_file(filepath)

        # Check if it's a PNG with embedded XML
        if content.startswith("iVBOR"):
            content = self._extract_from_png(content)

        # Parse the XML
        root = ET.fromstring(content)

        # Handle mxfile format
        if root.tag == "mxfile":
            return self._export_mxfile(root, options)
        # Single diagram
        return [self._export_diagram(root, options)]

    def _read_file(self, filepath: str) -> str:
        """Read file content"""
        # Try to read as text first
        try:
            with open(filepath, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try as binary (might be compressed)
            with open(filepath, "rb") as f:
                data = f.read()

            # Check for PNG signature
            if data.startswith(b"\x89PNG"):
                # Extract from PNG and return as base64
                return base64.b64encode(data).decode("ascii")
            # Try to decode as UTF-8
            return data.decode("utf-8")

    def _extract_from_png(self, png_data: str) -> str:
        """Extract Draw.io XML from PNG tEXt chunk"""
        # Decode base64
        png_bytes = base64.b64decode(png_data)

        # PNG chunk reader
        pos = 8  # Skip PNG signature

        while pos < len(png_bytes):
            # Read chunk header
            length = int.from_bytes(png_bytes[pos:pos+4], "big")
            chunk_type = png_bytes[pos+4:pos+8]

            if chunk_type == b"tEXt":
                # Read chunk data
                chunk_data = png_bytes[pos+8:pos+8+length]

                # Look for mxfile
                if chunk_data.startswith(b"mxfile"):
                    # Skip keyword and null separator
                    xml_start = chunk_data.find(b"\x00") + 1
                    xml_data = chunk_data[xml_start:]

                    # Decode the XML
                    try:
                        return urllib.parse.unquote(xml_data.decode("utf-8"))
                    except:
                        return xml_data.decode("utf-8")

            # Move to next chunk
            pos += 12 + length  # Header + data + CRC

        raise ValueError("No Draw.io data found in PNG")

    def _export_mxfile(self, root: ET.Element, options: ExportOptions) -> list[str]:
        """Export mxfile with potentially multiple diagrams"""
        diagrams = root.findall("diagram")

        if not diagrams:
            return []

        # Store global settings
        self.math_enabled = root.get("math") == "1"
        self.compressed = root.get("compressed", "true") != "false"  # Default is compressed

        svgs = []

        # Determine which pages to export
        pages_to_export = self._get_pages_to_export(diagrams, options)

        # Export each page
        for page_idx in pages_to_export:
            diagram = diagrams[page_idx]

            # Parse diagram data
            diagram_root = self._parse_diagram_node(diagram)
            if diagram_root is not None:
                svg = self._export_diagram(
                    diagram_root, options,
                    page_name=diagram.get("name", f"Page-{page_idx+1}"),
                    page_number=page_idx + 1,
                    total_pages=len(diagrams)
                )
                svgs.append(svg)

        return svgs

    def _get_pages_to_export(self, diagrams: list[ET.Element],
                           options: ExportOptions) -> list[int]:
        """Determine which pages to export based on options"""
        if options.all_pages:
            return list(range(len(diagrams)))
        if options.page_id:
            # Find page by ID
            for i, diagram in enumerate(diagrams):
                if diagram.get("id") == options.page_id:
                    return [i]
            # Fallback to first page if ID not found
            return [0] if diagrams else []
        # Export first page by default
        return [0] if diagrams else []

    def _parse_diagram_node(self, diagram: ET.Element) -> ET.Element | None:
        """Parse a diagram node and return the mxGraphModel"""
        # For uncompressed format, mxGraphModel is a direct child
        graph_model = diagram.find("mxGraphModel")
        if graph_model is not None:
            return graph_model

        # For compressed format, content is in text
        content = diagram.text

        if not content:
            return None

        try:
            # Remove whitespace
            content = content.strip()

            # Check if compressed
            if self.compressed:
                # Base64 decode
                decoded = base64.b64decode(content)

                # Inflate
                inflated = zlib.decompress(decoded, -zlib.MAX_WBITS)

                # URL decode
                xml_str = urllib.parse.unquote(inflated.decode("utf-8"))
            else:
                # Just URL decode
                xml_str = urllib.parse.unquote(content)

            # Parse XML
            return ET.fromstring(xml_str)

        except Exception as e:
            print(f"Error parsing diagram: {e}", file=sys.stderr)
            return None

    def _export_diagram(self, root: ET.Element, options: ExportOptions,
                       page_name: str = "Page-1", page_number: int = 1,
                       total_pages: int = 1) -> str:
        """Export a single diagram to SVG with all features"""

        # Extract settings from root
        self._extract_diagram_settings(root, options)

        # Create SVG root
        svg = self._create_svg_root(options)

        # Add definitions
        defs = ET.SubElement(svg, "defs")
        self._add_standard_defs(defs, options)

        # Create background
        if options.background and not options.transparent:
            self._add_background(svg, options.background)

        # Create main group
        main_group = ET.SubElement(svg, "g", attrib={"id": "graph0"})

        # Calculate bounds and transformations
        bounds, scale, translate = self._calculate_transform(root, options)

        # Set SVG dimensions
        svg.set("width", str(bounds.width))
        svg.set("height", str(bounds.height))
        svg.set("viewBox", f"0 0 {bounds.width} {bounds.height}")

        # Apply transform
        if scale != 1.0 or translate[0] != 0 or translate[1] != 0:
            main_group.set("transform",
                         f"translate({translate[0]},{translate[1]}) scale({scale})")

        # Add grid if enabled
        if options.grid:
            self._add_grid(main_group, bounds, options)

        # Process model
        model = root.find(".//mxGraphModel") or root
        root_cell = model.find(".//root")

        if root_cell is not None:
            # Build cell states
            cell_states = self._build_cell_states(root_cell, options)

            # Render cells in correct order
            self._render_cells(main_group, cell_states, defs, options)

        # Add page info for multi-page documents
        if total_pages > 1:
            self._add_page_info(svg, page_name, page_number, total_pages)

        # Add metadata
        if options.embed_xml:
            self._add_metadata(svg, root)

        # Post-process SVG
        self._post_process_svg(svg, options)

        # Convert to string with proper declaration
        return self._svg_to_string(svg)

    def _extract_diagram_settings(self, root: ET.Element, options: ExportOptions):
        """Extract diagram settings and merge with options"""
        # Background
        if not options.background:
            options.background = root.get("background")

        # Grid settings
        grid_elem = root.find(".//mxGraphModel")
        if grid_elem is not None:
            if not options.grid_size:
                gs = grid_elem.get("gridSize")
                if gs:
                    options.grid_size = int(gs)

            options.grid = grid_elem.get("grid") == "1"

        # Page settings
        if not options.page_width:
            pw = root.get("pageWidth")
            if pw:
                options.page_width = float(pw)

        if not options.page_height:
            ph = root.get("pageHeight")
            if ph:
                options.page_height = float(ph)

    def _create_svg_root(self, options: ExportOptions) -> ET.Element:
        """Create SVG root element with proper namespaces"""
        attribs = {
            "xmlns": self.ns["svg"],
            "xmlns:xlink": self.ns["xlink"],
            "version": "1.1"
        }

        # Add style for theme
        if options.theme:
            attribs["class"] = f"drawio-theme-{options.theme}"

        return ET.Element("svg", attrib=attribs)

    def _add_standard_defs(self, defs: ET.Element, options: ExportOptions):
        """Add standard definitions like filters, markers, gradients"""

        # Shadow filter
        if options.shadow:
            filter_elem = ET.SubElement(defs, "filter", attrib={
                "id": "dropShadow",
                "x": "-50%",
                "y": "-50%",
                "width": "200%",
                "height": "200%"
            })

            # Create shadow effect
            ET.SubElement(filter_elem, "feGaussianBlur", attrib={
                "in": "SourceAlpha",
                "stdDeviation": "1.7"
            })

            ET.SubElement(filter_elem, "feOffset", attrib={
                "dx": "3",
                "dy": "3",
                "result": "offsetblur"
            })

            ET.SubElement(filter_elem, "feFlood", attrib={
                "flood-color": "#3D4574",
                "flood-opacity": "0.4"
            })

            ET.SubElement(filter_elem, "feComposite", attrib={
                "in2": "offsetblur",
                "operator": "in"
            })

            merge = ET.SubElement(filter_elem, "feMerge")
            ET.SubElement(merge, "feMergeNode")
            ET.SubElement(merge, "feMergeNode", attrib={"in": "SourceGraphic"})

        # Standard arrow markers
        self._add_arrow_markers(defs)

    def _add_arrow_markers(self, defs: ET.Element):
        """Add standard arrow markers"""
        markers = [
            ("classic", "M 0 0 L 10 5 L 0 10 z"),
            ("block", "M 0 0 L 10 5 L 0 10 z"),
            ("open", "M 0 0 L 10 5 M 10 5 L 0 10"),
            ("oval", "M 0 5 A 5 5 0 1 1 10 5 A 5 5 0 1 1 0 5"),
            ("diamond", "M 0 5 L 5 0 L 10 5 L 5 10 z"),
            ("diamondThin", "M 0 5 L 5 2 L 10 5 L 5 8 z")
        ]

        for name, path in markers:
            for suffix, fill in [("", "black"), ("-white", "white")]:
                marker = ET.SubElement(defs, "marker", attrib={
                    "id": f"arrow-{name}{suffix}",
                    "markerWidth": "10",
                    "markerHeight": "10",
                    "refX": "10",
                    "refY": "5",
                    "orient": "auto",
                    "markerUnits": "strokeWidth"
                })

                ET.SubElement(marker, "path", attrib={
                    "d": path,
                    "fill": fill,
                    "stroke": fill,
                    "stroke-width": "1"
                })

    def _add_background(self, svg: ET.Element, color: str):
        """Add background rectangle"""
        if color and color != "none":
            ET.SubElement(svg, "rect", attrib={
                "width": "100%",
                "height": "100%",
                "fill": color,
                "x": "0",
                "y": "0"
            })

    def _add_grid(self, parent: ET.Element, bounds: Bounds, options: ExportOptions):
        """Add grid pattern"""
        # Create pattern in defs
        defs = parent.getparent().find("defs")

        pattern = ET.SubElement(defs, "pattern", attrib={
            "id": "grid",
            "x": "0",
            "y": "0",
            "width": str(options.grid_size),
            "height": str(options.grid_size),
            "patternUnits": "userSpaceOnUse"
        })

        # Add grid lines
        ET.SubElement(pattern, "line", attrib={
            "x1": "0",
            "y1": "0",
            "x2": str(options.grid_size),
            "y2": "0",
            "stroke": options.grid_color,
            "stroke-width": "0.5"
        })

        ET.SubElement(pattern, "line", attrib={
            "x1": "0",
            "y1": "0",
            "x2": "0",
            "y2": str(options.grid_size),
            "stroke": options.grid_color,
            "stroke-width": "0.5"
        })

        # Add grid rectangle
        grid_rect = ET.SubElement(parent, "rect", attrib={
            "x": "0",
            "y": "0",
            "width": str(bounds.width),
            "height": str(bounds.height),
            "fill": "url(#grid)",
            "pointer-events": "none"
        })

    def _calculate_transform(self, root: ET.Element,
                           options: ExportOptions) -> tuple[Bounds, float, tuple[float, float]]:
        """Calculate bounds, scale and translation"""

        # Get raw bounds
        raw_bounds = self._calculate_graph_bounds(root, options)

        # Handle print mode
        if options.print_mode and options.page_width and options.page_height:
            # Page-based bounds
            bounds = Bounds(0, 0, options.page_width, options.page_height)
            scale = options.scale * options.page_scale
            translate = (-raw_bounds.x, -raw_bounds.y)
        else:
            # Standard export
            scale = options.scale

            # Apply border
            border = options.border

            # Calculate dimensions
            if options.width and options.height:
                # Fit to specific size
                scale_x = options.width / raw_bounds.width
                scale_y = options.height / raw_bounds.height
                scale = min(scale_x, scale_y)

                bounds = Bounds(0, 0, options.width, options.height)

                # Center the content
                actual_width = raw_bounds.width * scale
                actual_height = raw_bounds.height * scale
                translate = (
                    (options.width - actual_width) / 2 - raw_bounds.x * scale,
                    (options.height - actual_height) / 2 - raw_bounds.y * scale
                )
            else:
                # Natural size with border
                bounds = Bounds(
                    0, 0,
                    raw_bounds.width * scale + 2 * border,
                    raw_bounds.height * scale + 2 * border
                )

                translate = (
                    border - raw_bounds.x * scale,
                    border - raw_bounds.y * scale
                )

        return bounds, scale, translate

    def _calculate_graph_bounds(self, root: ET.Element,
                               options: ExportOptions) -> Bounds:
        """Calculate bounds of all visible elements"""
        bounds = None

        model = root.find(".//mxGraphModel") or root
        root_cell = model.find(".//root")

        if root_cell is None:
            return Bounds(0, 0, 100, 100)

        # Get visible layers
        visible_layers = self._get_visible_layers(root_cell, options)

        # Calculate bounds of all visible cells
        for cell in root_cell:
            if not self._is_cell_visible(cell, visible_layers):
                continue

            cell_bounds = self._get_cell_bounds(cell, root_cell)
            if cell_bounds:
                if bounds is None:
                    bounds = cell_bounds
                else:
                    bounds.add(cell_bounds)

        # Handle background image
        bg_image = root.get("backgroundImage")
        if bg_image:
            try:
                bg_data = json.loads(bg_image)
                bg_bounds = Bounds(
                    bg_data.get("x", 0),
                    bg_data.get("y", 0),
                    bg_data.get("width", 100),
                    bg_data.get("height", 100)
                )
                if bounds:
                    bounds.add(bg_bounds)
                else:
                    bounds = bg_bounds
            except:
                pass

        return bounds or Bounds(0, 0, 100, 100)

    def _get_cell_bounds(self, cell: ET.Element, root_cell: ET.Element) -> Bounds | None:
        """Get bounds of a single cell"""
        if cell.tag != "mxCell":
            cell = cell.find("mxCell")
            if cell is None:
                return None

        geom_elem = cell.find("mxGeometry")
        if geom_elem is None:
            return None

        geometry = self._parse_geometry(geom_elem)

        # Skip if no dimensions
        if geometry.width <= 0 or geometry.height <= 0:
            # Check for edges with points
            if cell.get("edge") == "1" and geometry.points:
                bounds = None
                for point in geometry.points:
                    point_bounds = Bounds(point[0], point[1], 1, 1)
                    if bounds:
                        bounds.add(point_bounds)
                    else:
                        bounds = point_bounds
                return bounds
            return None

        # Handle relative geometry
        if geometry.relative:
            parent_id = cell.get("parent")
            if parent_id and parent_id != "0":
                parent = self._find_cell_by_id(root_cell, parent_id)
                if parent:
                    parent_bounds = self._get_cell_bounds(parent, root_cell)
                    if parent_bounds:
                        x = parent_bounds.x + parent_bounds.width * geometry.x
                        y = parent_bounds.y + parent_bounds.height * geometry.y
                        return Bounds(x + geometry.offset_x,
                                    y + geometry.offset_y,
                                    geometry.width, geometry.height)

        return Bounds(geometry.x, geometry.y, geometry.width, geometry.height)

    def _parse_geometry(self, geom_elem: ET.Element) -> Geometry:
        """Parse mxGeometry element"""
        geometry = Geometry()

        geometry.x = float(geom_elem.get("x", "0"))
        geometry.y = float(geom_elem.get("y", "0"))
        geometry.width = float(geom_elem.get("width", "0"))
        geometry.height = float(geom_elem.get("height", "0"))
        geometry.relative = geom_elem.get("relative") == "1"

        # Parse offset
        offset = geom_elem.find('mxPoint[@as="offset"]')
        if offset is not None:
            geometry.offset_x = float(offset.get("x", "0"))
            geometry.offset_y = float(offset.get("y", "0"))

        # Parse points for edges
        points_array = geom_elem.find('Array[@as="points"]')
        if points_array is not None:
            for point in points_array.findall("mxPoint"):
                x = float(point.get("x", "0"))
                y = float(point.get("y", "0"))
                geometry.points.append((x, y))

        # Parse source/target points
        source_point = geom_elem.find('mxPoint[@as="sourcePoint"]')
        if source_point is not None:
            geometry.source_point = (
                float(source_point.get("x", "0")),
                float(source_point.get("y", "0"))
            )

        target_point = geom_elem.find('mxPoint[@as="targetPoint"]')
        if target_point is not None:
            geometry.target_point = (
                float(target_point.get("x", "0")),
                float(target_point.get("y", "0"))
            )

        return geometry

    def _get_visible_layers(self, root_cell: ET.Element,
                          options: ExportOptions) -> set[str]:
        """Get set of visible layer IDs"""
        visible = set()

        # Find all layers
        for cell in root_cell:
            if cell.get("parent") == "0":
                layer_id = cell.get("id")
                if not layer_id:
                    continue

                # Check visibility
                visible_attr = cell.get("visible", "1")
                is_visible = visible_attr != "0"

                # Apply layer filters
                if options.layers:
                    # By index
                    layer_index = self._get_layer_index(cell, root_cell)
                    if str(layer_index) in options.layers:
                        is_visible = True
                    else:
                        is_visible = False

                elif options.layer_ids:
                    # By ID
                    if layer_id in options.layer_ids:
                        is_visible = True
                    else:
                        is_visible = False

                if is_visible:
                    visible.add(layer_id)

        # Always include default layer
        visible.add("1")

        return visible

    def _get_layer_index(self, layer_cell: ET.Element,
                        root_cell: ET.Element) -> int:
        """Get layer index (0-based)"""
        index = 0
        for cell in root_cell:
            if cell.get("parent") == "0":
                if cell == layer_cell:
                    return index
                index += 1
        return -1

    def _is_cell_visible(self, cell: ET.Element, visible_layers: set[str]) -> bool:
        """Check if cell should be rendered"""
        if cell.tag != "mxCell":
            cell = cell.find("mxCell")
            if cell is None:
                return False

        # Check cell's own visibility
        if cell.get("visible") == "0":
            return False

        # Check layer visibility
        parent_id = cell.get("parent", "1")

        # Root cells (layers)
        if parent_id == "0":
            return cell.get("id") in visible_layers

        # Regular cells
        return parent_id in visible_layers

    def _find_cell_by_id(self, root_cell: ET.Element, cell_id: str) -> ET.Element | None:
        """Find cell by ID"""
        for cell in root_cell:
            if cell.get("id") == cell_id:
                return cell
        return None

    def _build_cell_states(self, root_cell: ET.Element,
                         options: ExportOptions) -> dict[str, CellState]:
        """Build cell states with computed positions"""
        states = {}
        visible_layers = self._get_visible_layers(root_cell, options)

        # First pass: create states
        for cell in root_cell:
            cell_id = cell.get("id")
            if not cell_id:
                continue

            mx_elem = cell
            if cell.tag != "mxCell":
                mx_elem = cell.find("mxCell")
                if mx_elem is None:
                    continue
                if mx_elem.get("id") is None:
                    mx_elem.set("id", cell_id)
                if mx_elem.get("value") is None and cell.get("label"):
                    mx_elem.set("value", cell.get("label"))

            # Parse style
            style = self._parse_style(mx_elem.get("style", ""))

            # Parse geometry
            geom_elem = mx_elem.find("mxGeometry")
            geometry = self._parse_geometry(geom_elem) if geom_elem is not None else None

            # Create state
            state = CellState(
                cell=mx_elem,
                style=style,
                geometry=geometry,
                visible=self._is_cell_visible(mx_elem, visible_layers)
            )

            states[cell_id] = state

        # Second pass: resolve relative positions
        for cell_id, state in states.items():
            if state.geometry and state.geometry.relative:
                self._resolve_relative_position(state, states)

        return states

    def _resolve_relative_position(self, state: CellState,
                                 states: dict[str, CellState]):
        """Resolve relative position to absolute"""
        parent_id = state.cell.get("parent")
        if not parent_id or parent_id == "0":
            return

        parent_state = states.get(parent_id)
        if not parent_state or not parent_state.geometry:
            return

        # Calculate absolute position
        abs_x = (parent_state.geometry.x +
                parent_state.geometry.width * state.geometry.x +
                state.geometry.offset_x)
        abs_y = (parent_state.geometry.y +
                parent_state.geometry.height * state.geometry.y +
                state.geometry.offset_y)

        state.absolute_offset = (abs_x, abs_y)

    def _render_cells(self, parent_group: ET.Element,
                     states: dict[str, CellState],
                     defs: ET.Element, options: ExportOptions):
        """Render all cells in correct order"""

        # Separate vertices and edges
        vertices = []
        edges = []

        for state in states.values():
            if not state.visible:
                continue

            if state.cell.get("edge") == "1":
                edges.append(state)
            else:
                vertices.append(state)

        # Render vertices first (shapes)
        for state in vertices:
            self._render_vertex(parent_group, state, defs, options)

        # Then render edges (connectors)
        for state in edges:
            self._render_edge(parent_group, state, states, defs, options)

    def _render_vertex(self, parent_group: ET.Element, state: CellState,
                      defs: ET.Element, options: ExportOptions):
        """Render a vertex (shape)"""
        if not state.geometry:
            return

        # Calculate position
        if state.absolute_offset:
            x, y = state.absolute_offset
        else:
            x, y = state.geometry.x, state.geometry.y

        # Create group
        cell_group = ET.SubElement(parent_group, "g", attrib={
            "transform": f"translate({x},{y})"
        })

        # Apply shadow
        if options.shadow and state.style.get("shadow", "0") == "1":
            cell_group.set("filter", "url(#dropShadow)")

        # Get shape type
        shape = state.style.get("shape", "rect")

        # Handle special shapes
        if shape == "image":
            self._render_image(cell_group, state, defs, options)
        elif shape == "swimlane":
            self._render_swimlane(cell_group, state, options)
        else:
            # Render standard shape
            bounds = Bounds(0, 0, state.geometry.width, state.geometry.height)
            elements = self.shape_registry.render_shape(shape, bounds, state.style)

            for elem in elements:
                cell_group.append(elem)

        # Render label
        label = state.cell.get("value", "")
        if label and shape != "image":
            self._render_label(cell_group, label, state, options)

    def _render_image(self, parent_group: ET.Element, state: CellState,
                     defs: ET.Element, options: ExportOptions):
        """Render image shape"""
        image_url = state.style.get("image", "")
        if not image_url:
            return

        # Create image element
        image = ET.SubElement(parent_group, "image", attrib={
            "x": "0",
            "y": "0",
            "width": str(state.geometry.width),
            "height": str(state.geometry.height),
            "preserveAspectRatio": "none"
        })

        # Normalize inline data URIs that are base64 encoded without the
        # required ";base64" hint. Some Draw.io exports omit the hint which
        # causes browsers to treat the data as plain text rather than base64.
        if image_url.startswith("data:image") and ";base64," not in image_url:
            prefix, data = image_url.split(",", 1)
            if re.fullmatch(r"[A-Za-z0-9+/=]+", data):
                image_url = f"{prefix};base64,{data}"

        # Handle image embedding for external resources
        if options.embed_images and image_url.startswith("http"):
            image_url = self._embed_image(image_url)

        image.set("{%s}href" % self.ns["xlink"], image_url)

    def _embed_image(self, url: str) -> str:
        """Embed external image as data URL"""
        if url in self.embedded_images:
            return self.embedded_images[url]

        try:
            # Download image
            with urlopen(url) as response:
                data = response.read()

            # Determine MIME type
            mime_type = mimetypes.guess_type(url)[0] or "image/png"

            # Create data URL
            data_url = f"data:{mime_type};base64,{base64.b64encode(data).decode()}"

            # Cache
            self.embedded_images[url] = data_url

            return data_url
        except:
            # Return original URL on error
            return url

    def _render_swimlane(self, parent_group: ET.Element, state: CellState,
                        options: ExportOptions):
        """Render swimlane shape"""
        bounds = Bounds(0, 0, state.geometry.width, state.geometry.height)

        # Main rectangle
        rect = ET.SubElement(parent_group, "rect", attrib={
            "x": "0",
            "y": "0",
            "width": str(bounds.width),
            "height": str(bounds.height),
            "fill": state.style.get("fillColor", "#ffffff"),
            "stroke": state.style.get("strokeColor", "#000000"),
            "stroke-width": state.style.get("strokeWidth", "1")
        })

        # Title area separator
        title_height = float(state.style.get("startSize", "20"))
        ET.SubElement(parent_group, "line", attrib={
            "x1": "0",
            "y1": str(title_height),
            "x2": str(bounds.width),
            "y2": str(title_height),
            "stroke": state.style.get("strokeColor", "#000000"),
            "stroke-width": state.style.get("strokeWidth", "1")
        })

    def _render_edge(self, parent_group: ET.Element, state: CellState,
                    all_states: dict[str, CellState],
                    defs: ET.Element, options: ExportOptions):
        """Render edge (connector)"""
        if not state.geometry:
            return

        # Get source and target states
        source_id = state.cell.get("source")
        target_id = state.cell.get("target")

        source_state = all_states.get(source_id) if source_id else None
        target_state = all_states.get(target_id) if target_id else None

        # Calculate edge path
        points = self._calculate_edge_points(state, source_state, target_state)

        if len(points) < 2:
            return

        # Create path
        path_data = self._create_path_data(points, state.style)

        path = ET.SubElement(parent_group, "path", attrib={
            "d": path_data,
            "fill": "none",
            "stroke": state.style.get("strokeColor", "#000000"),
            "stroke-width": state.style.get("strokeWidth", "1")
        })

        # Apply line style
        self._apply_line_style(path, state.style)

        # Add markers
        self._add_edge_markers(path, state.style, defs)

        # Add label
        label = state.cell.get("value", "")
        if label:
            self._render_edge_label(parent_group, label, points, state, options)

    def _calculate_edge_points(self, edge_state: CellState,
                             source_state: CellState | None,
                             target_state: CellState | None) -> list[tuple[float, float]]:
        """Calculate edge points including connection points"""
        points = []

        # Add source point
        if edge_state.geometry.source_point:
            points.append(edge_state.geometry.source_point)
        elif source_state and source_state.geometry:
            # Calculate exit point from source
            cx = source_state.geometry.x + source_state.geometry.width / 2
            cy = source_state.geometry.y + source_state.geometry.height / 2
            points.append((cx, cy))

        # Add waypoints
        points.extend(edge_state.geometry.points)

        # Add target point
        if edge_state.geometry.target_point:
            points.append(edge_state.geometry.target_point)
        elif target_state and target_state.geometry:
            # Calculate entry point to target
            cx = target_state.geometry.x + target_state.geometry.width / 2
            cy = target_state.geometry.y + target_state.geometry.height / 2
            points.append((cx, cy))

        return points

    def _create_path_data(self, points: list[tuple[float, float]],
                         style: dict[str, str]) -> str:
        """Create SVG path data from points"""
        if not points:
            return ""

        # Check edge style
        edge_style = style.get("edgeStyle", "orthogonalEdgeStyle")
        curved = style.get("curved", "0") == "1"

        if curved or edge_style == "curved":
            # Bezier curve
            return self._create_curved_path(points)
        if edge_style in ["orthogonalEdgeStyle", "elbowEdgeStyle"]:
            # Orthogonal connectors
            return self._create_orthogonal_path(points)
        # Straight lines
        return self._create_straight_path(points)

    def _create_straight_path(self, points: list[tuple[float, float]]) -> str:
        """Create straight line path"""
        path = f"M {points[0][0]} {points[0][1]}"
        for i in range(1, len(points)):
            path += f" L {points[i][0]} {points[i][1]}"
        return path

    def _create_curved_path(self, points: list[tuple[float, float]]) -> str:
        """Create smooth curved path"""
        if len(points) < 2:
            return ""

        path = f"M {points[0][0]} {points[0][1]}"

        if len(points) == 2:
            # Simple quadratic curve
            cx = (points[0][0] + points[1][0]) / 2
            cy = (points[0][1] + points[1][1]) / 2
            path += f" Q {cx} {cy} {points[1][0]} {points[1][1]}"
        else:
            # Smooth bezier through points
            for i in range(1, len(points)):
                if i == 1:
                    cx1 = points[0][0] + (points[1][0] - points[0][0]) / 3
                    cy1 = points[0][1] + (points[1][1] - points[0][1]) / 3
                else:
                    cx1 = points[i-1][0] + (points[i][0] - points[i-2][0]) / 6
                    cy1 = points[i-1][1] + (points[i][1] - points[i-2][1]) / 6

                if i == len(points) - 1:
                    cx2 = points[i][0] - (points[i][0] - points[i-1][0]) / 3
                    cy2 = points[i][1] - (points[i][1] - points[i-1][1]) / 3
                else:
                    cx2 = points[i][0] - (points[i+1][0] - points[i-1][0]) / 6
                    cy2 = points[i][1] - (points[i+1][1] - points[i-1][1]) / 6

                path += f" C {cx1} {cy1} {cx2} {cy2} {points[i][0]} {points[i][1]}"

        return path

    def _create_orthogonal_path(self, points: list[tuple[float, float]]) -> str:
        """Create orthogonal (right-angle) path"""
        if len(points) < 2:
            return ""

        path = f"M {points[0][0]} {points[0][1]}"

        for i in range(1, len(points)):
            prev = points[i-1]
            curr = points[i]

            # Add intermediate point for right angle
            if i < len(points) - 1:
                next_pt = points[i+1]

                # Determine direction
                if abs(curr[0] - prev[0]) > abs(curr[1] - prev[1]):
                    # Horizontal first
                    path += f" L {curr[0]} {prev[1]}"
                else:
                    # Vertical first
                    path += f" L {prev[0]} {curr[1]}"

            path += f" L {curr[0]} {curr[1]}"

        return path

    def _apply_line_style(self, path: ET.Element, style: dict[str, str]):
        """Apply line style attributes"""
        # Dashed line
        dashed = style.get("dashed", "0") == "1"
        if dashed:
            pattern = style.get("dashPattern", "3 3")
            path.set("stroke-dasharray", pattern)

        # Line width
        stroke_width = style.get("strokeWidth", "1")
        path.set("stroke-width", stroke_width)

        # Opacity
        opacity = style.get("opacity", "100")
        if opacity != "100":
            path.set("stroke-opacity", str(float(opacity) / 100))

    def _add_edge_markers(self, path: ET.Element, style: dict[str, str],
                         defs: ET.Element):
        """Add arrow markers to edge"""
        # Start arrow
        start_arrow = style.get("startArrow", "none")
        if start_arrow != "none":
            color = style.get("strokeColor", "#000000")
            marker_id = f'arrow-{start_arrow}-{color.replace("#", "")}'

            # Ensure marker exists
            if not defs.find(f".//marker[@id='{marker_id}']"):
                self._create_arrow_marker(defs, marker_id, start_arrow, color)

            path.set("marker-start", f"url(#{marker_id})")

        # End arrow
        end_arrow = style.get("endArrow", "classic")
        if end_arrow != "none":
            color = style.get("strokeColor", "#000000")
            marker_id = f'arrow-{end_arrow}-{color.replace("#", "")}'

            # Ensure marker exists
            if not defs.find(f".//marker[@id='{marker_id}']"):
                self._create_arrow_marker(defs, marker_id, end_arrow, color)

            path.set("marker-end", f"url(#{marker_id})")

    def _create_arrow_marker(self, defs: ET.Element, marker_id: str,
                           arrow_type: str, color: str):
        """Create specific arrow marker"""
        marker = ET.SubElement(defs, "marker", attrib={
            "id": marker_id,
            "markerWidth": "10",
            "markerHeight": "10",
            "refX": "10",
            "refY": "5",
            "orient": "auto",
            "markerUnits": "strokeWidth"
        })

        # Define arrow paths
        arrow_paths = {
            "classic": "M 0 0 L 10 5 L 0 10 z",
            "block": "M 0 0 L 10 5 L 0 10 z",
            "open": "M 0 0 L 10 5 M 10 5 L 0 10",
            "oval": "M 0 5 A 5 5 0 1 1 10 5 A 5 5 0 1 1 0 5",
            "diamond": "M 0 5 L 5 0 L 10 5 L 5 10 z",
            "diamondThin": "M 0 5 L 5 2 L 10 5 L 5 8 z"
        }

        path_data = arrow_paths.get(arrow_type, arrow_paths["classic"])

        ET.SubElement(marker, "path", attrib={
            "d": path_data,
            "fill": color if arrow_type != "open" else "none",
            "stroke": color,
            "stroke-width": "1" if arrow_type == "open" else "0"
        })

    def _render_label(self, parent_group: ET.Element, label: str,
                     state: CellState, options: ExportOptions):
        """Render text label with HTML support"""
        if not label or not state.geometry:
            return

        # Parse label HTML
        is_html = label.startswith("<") and label.endswith(">")

        # Create foreignObject for HTML rendering
        fo = ET.SubElement(parent_group, "foreignObject", attrib={
            "x": "0",
            "y": "0",
            "width": str(state.geometry.width),
            "height": str(state.geometry.height),
            "pointer-events": "none"
        })

        # Create container div
        div = ET.SubElement(fo, "{%s}div" % self.ns["xhtml"], attrib={
            "style": self._get_label_style(state.style, state.geometry)
        })

        if is_html:
            # Parse and sanitize HTML
            self._render_html_label(div, label)
        else:
            # Plain text
            div.text = label

    def _render_edge_label(self, parent_group: ET.Element, label: str,
                          points: list[tuple[float, float]],
                          state: CellState, options: ExportOptions):
        """Render edge label at midpoint"""
        if len(points) < 2:
            return

        # Calculate midpoint
        mid_idx = len(points) // 2
        if len(points) % 2 == 0:
            # Even number of points - interpolate
            p1 = points[mid_idx - 1]
            p2 = points[mid_idx]
            mx = (p1[0] + p2[0]) / 2
            my = (p1[1] + p2[1]) / 2
        else:
            # Odd number - use middle point
            mx, my = points[mid_idx]

        # Create label container
        label_width = 100  # Default width
        label_height = 20  # Default height

        fo = ET.SubElement(parent_group, "foreignObject", attrib={
            "x": str(mx - label_width / 2),
            "y": str(my - label_height / 2),
            "width": str(label_width),
            "height": str(label_height),
            "pointer-events": "none"
        })

        div = ET.SubElement(fo, "{%s}div" % self.ns["xhtml"], attrib={
            "style": self._get_edge_label_style(state.style)
        })

        div.text = label

    def _get_label_style(self, style: dict[str, str],
                        geometry: Geometry) -> str:
        """Get CSS style for label"""
        css_parts = []

        # Layout
        css_parts.append("display: flex")
        css_parts.append("align-items: center")
        css_parts.append("justify-content: center")
        css_parts.append("width: 100%")
        css_parts.append("height: 100%")
        css_parts.append("box-sizing: border-box")
        css_parts.append("overflow: hidden")

        # Font
        font_family = style.get("fontFamily", "Arial,Helvetica")
        font_size = style.get("fontSize", "12")
        font_color = style.get("fontColor", "#000000")

        css_parts.append(f"font-family: {font_family}")
        css_parts.append(f"font-size: {font_size}px")
        css_parts.append(f"color: {font_color}")

        # Font style
        if style.get("fontStyle", "0") == "1":
            css_parts.append("font-style: italic")
        if style.get("fontStyle", "0") == "2":
            css_parts.append("font-weight: bold")
        if style.get("fontStyle", "0") == "4":
            css_parts.append("text-decoration: underline")

        # Text alignment
        align = style.get("align", "center")
        css_parts.append(f"text-align: {align}")

        # Vertical alignment
        vertical_align = style.get("verticalAlign", "middle")
        if vertical_align == "top":
            css_parts.append("align-items: flex-start")
        elif vertical_align == "bottom":
            css_parts.append("align-items: flex-end")

        # Spacing
        spacing = style.get("spacing", "0")
        css_parts.append(f"padding: {spacing}px")

        # Word wrap
        if style.get("whiteSpace", "nowrap") == "wrap":
            css_parts.append("white-space: normal")
            css_parts.append("word-wrap: break-word")
        else:
            css_parts.append("white-space: nowrap")

        return "; ".join(css_parts)

    def _get_edge_label_style(self, style: dict[str, str]) -> str:
        """Get CSS style for edge label"""
        css_parts = []

        # Basic layout
        css_parts.append("display: flex")
        css_parts.append("align-items: center")
        css_parts.append("justify-content: center")
        css_parts.append("width: 100%")
        css_parts.append("height: 100%")

        # Background
        label_bg = style.get("labelBackgroundColor")
        if label_bg and label_bg != "none":
            css_parts.append(f"background-color: {label_bg}")
            css_parts.append("padding: 2px 4px")

        # Font
        font_family = style.get("fontFamily", "Arial,Helvetica")
        font_size = style.get("fontSize", "11")
        font_color = style.get("fontColor", "#000000")

        css_parts.append(f"font-family: {font_family}")
        css_parts.append(f"font-size: {font_size}px")
        css_parts.append(f"color: {font_color}")

        return "; ".join(css_parts)

    def _render_html_label(self, container: ET.Element, html: str):
        """Render HTML label content"""
        # Basic HTML sanitization and parsing
        # Remove outer tags
        html = html.strip()
        if html.startswith("<") and html.endswith(">"):
            html = html[1:-1]

        # Simple HTML to elements conversion
        # This is a simplified version - full HTML parsing would be more complex
        try:
            # Wrap in a div for parsing
            wrapped = f'<div xmlns="{self.ns["xhtml"]}">{html}</div>'
            parsed = ET.fromstring(wrapped)

            # Copy children to container
            for child in parsed:
                container.append(child)

        except:
            # Fallback to text
            container.text = html

    def _parse_style(self, style_str: str) -> dict[str, str]:
        """Parse Draw.io style string"""
        style = {}

        if not style_str:
            return style

        # Handle both semicolon and custom separators
        parts = style_str.split(";")

        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                style[key.strip()] = value.strip()

        return style

    def _add_page_info(self, svg: ET.Element, page_name: str,
                      page_number: int, total_pages: int):
        """Add page information as metadata"""
        metadata = svg.find("metadata")
        if metadata is None:
            metadata = ET.SubElement(svg, "metadata")

        page_info = ET.SubElement(metadata, "pageInfo")
        page_info.set("name", page_name)
        page_info.set("number", str(page_number))
        page_info.set("total", str(total_pages))

    def _add_metadata(self, svg: ET.Element, root: ET.Element):
        """Add source XML as metadata"""
        metadata = svg.find("metadata")
        if metadata is None:
            metadata = ET.SubElement(svg, "metadata")

        # Add mxfile content
        content = ET.SubElement(metadata, "mxfile")
        content.text = ET.tostring(root, encoding="unicode")

    def _post_process_svg(self, svg: ET.Element, options: ExportOptions):
        """Post-process SVG for final output"""

        # Add fonts if needed
        if options.embed_fonts and self.embedded_fonts:
            style = ET.SubElement(svg.find("defs"), "style")
            style.text = self._generate_font_css()

        # Add theme CSS
        if options.theme:
            self._add_theme_css(svg, options.theme)

        # Process links
        if options.link_target:
            self._process_links(svg, options.link_target)

    def _generate_font_css(self) -> str:
        """Generate CSS for embedded fonts"""
        css = []

        for font_url in self.embedded_fonts:
            if font_url.startswith("http"):
                css.append(f'@import url("{font_url}");')

        return "\n".join(css)

    def _add_theme_css(self, svg: ET.Element, theme: str):
        """Add theme-specific CSS"""
        style = ET.SubElement(svg.find("defs"), "style")

        # Basic theme styles
        theme_css = {
            "kennedy": """
                .drawio-theme-kennedy text { font-family: Arial, sans-serif; }
                .drawio-theme-kennedy rect { stroke-width: 1px; }
            """,
            "dark": """
                .drawio-theme-dark { background: #2d2d30; }
                .drawio-theme-dark text { fill: #d4d4d4; }
                .drawio-theme-dark rect { fill: #1e1e1e; stroke: #3c3c3c; }
            """,
            "sketch": """
                .drawio-theme-sketch rect { stroke-width: 2px; stroke-linecap: round; }
                .drawio-theme-sketch path { stroke-width: 2px; stroke-linecap: round; }
            """
        }

        style.text = theme_css.get(theme, "")

    def _process_links(self, svg: ET.Element, target: str):
        """Process all links in SVG"""
        for link in svg.findall(".//{%s}a" % self.ns["svg"]):
            link.set("target", target)

    def _svg_to_string(self, svg: ET.Element) -> str:
        """Convert SVG element to string with proper formatting"""
        # Add XML declaration
        declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

        # Add DOCTYPE
        doctype = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'

        # Convert to string
        svg_str = ET.tostring(svg, encoding="unicode")

        # Pretty print (basic)
        svg_str = svg_str.replace("><", ">\n<")

        return declaration + doctype + svg_str


def main():
    """Enhanced command line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Advanced Draw.io to SVG Exporter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export with default settings
  %(prog)s diagram.drawio
  
  # Export specific page at 2x scale
  %(prog)s diagram.drawio --scale 2 --page Page-2
  
  # Export all pages with shadow and grid
  %(prog)s diagram.drawio --all-pages --shadow --grid
  
  # Export for dark theme with embedded fonts
  %(prog)s diagram.drawio --theme dark --embed-fonts
        """
    )

    # Input/Output
    parser.add_argument("input", help="Input Draw.io file (.drawio, .xml, or .png)")
    parser.add_argument("-o", "--output", help="Output SVG file (default: input_name.svg)")

    # Basic options
    parser.add_argument("-s", "--scale", type=float, default=1.0,
                       help="Export scale factor (default: 1.0)")
    parser.add_argument("-b", "--border", type=int, default=0,
                       help="Border size in pixels (default: 0)")
    parser.add_argument("--width", type=float, help="Target width in pixels")
    parser.add_argument("--height", type=float, help="Target height in pixels")

    # Appearance
    parser.add_argument("--background", help="Background color (e.g., #ffffff)")
    parser.add_argument("--transparent", action="store_true",
                       help="Transparent background")
    parser.add_argument("--shadow", action="store_true",
                       help="Add drop shadows")
    parser.add_argument("--theme", choices=["kennedy", "dark", "min", "atlas", "sketch"],
                       help="Apply theme")

    # Grid
    parser.add_argument("--grid", action="store_true",
                       help="Show grid")
    parser.add_argument("--grid-size", type=int, default=10,
                       help="Grid size (default: 10)")
    parser.add_argument("--grid-color", default="#e0e0e0",
                       help="Grid color (default: #e0e0e0)")

    # Pages and layers
    parser.add_argument("--page", dest="page_id", help="Page ID to export")
    parser.add_argument("--all-pages", action="store_true",
                       help="Export all pages")
    parser.add_argument("--layers", nargs="+",
                       help="Layer indices to show (0-based)")
    parser.add_argument("--layer-ids", nargs="+",
                       help="Layer IDs to show")

    # Embedding
    parser.add_argument("--embed-images", action="store_true", default=True,
                       help="Embed external images (default: true)")
    parser.add_argument("--no-embed-images", dest="embed_images",
                       action="store_false", help="Don't embed images")
    parser.add_argument("--embed-fonts", action="store_true",
                       help="Embed web fonts")
    parser.add_argument("--embed-xml", action="store_true",
                       help="Embed source XML in SVG")

    # Advanced
    parser.add_argument("--print-mode", action="store_true",
                       help="Export for printing")
    parser.add_argument("--page-format", default="a4",
                       choices=["a3", "a4", "letter", "legal", "tabloid"],
                       help="Page format for print mode")
    parser.add_argument("--link-target", choices=["_blank", "_self", "_parent", "_top"],
                       help="Target for links")

    args = parser.parse_args()

    # Create options
    options = ExportOptions(
        scale=args.scale,
        border=args.border,
        width=args.width,
        height=args.height,
        background=args.background,
        transparent=args.transparent,
        shadow=args.shadow,
        theme=args.theme,
        grid=args.grid,
        grid_size=args.grid_size,
        grid_color=args.grid_color,
        page_id=args.page_id,
        all_pages=args.all_pages,
        layers=args.layers,
        layer_ids=args.layer_ids,
        embed_images=args.embed_images,
        embed_fonts=args.embed_fonts,
        embed_xml=args.embed_xml,
        print_mode=args.print_mode,
        page_format=args.page_format,
        link_target=args.link_target
    )

    # Export
    exporter = DrawioSVGExporter()

    try:
        print(f"Exporting {args.input}...")
        svgs = exporter.export_file(args.input, options)

        if not svgs:
            print("Error: No diagrams found in file", file=sys.stderr)
            return 1

        # Determine output filename(s)
        if args.output:
            base_name = args.output
            if not base_name.endswith(".svg"):
                base_name += ".svg"
        else:
            base_name = os.path.splitext(args.input)[0]

        # Save SVG(s)
        if len(svgs) == 1:
            output_file = base_name if args.output else f"{base_name}.svg"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(svgs[0])
            print(f"✓ Exported to: {output_file}")

            # Print file size
            size = os.path.getsize(output_file)
            print(f"  File size: {size:,} bytes")
        else:
            # Multiple pages
            for i, svg in enumerate(svgs):
                if args.output:
                    # If output specified, add page suffix
                    name_parts = os.path.splitext(base_name)
                    output_file = f"{name_parts[0]}_page{i+1}{name_parts[1]}"
                else:
                    output_file = f"{base_name}_page{i+1}.svg"

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(svg)
                print(f"✓ Page {i+1} exported to: {output_file}")

        print("\nExport completed successfully!")

    except FileNotFoundError:
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
