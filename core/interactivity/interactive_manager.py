from __future__ import annotations
import logging
from typing import Any, Dict, List

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem, Select
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------

def create_layout_select(select_id: str = "layout-select") -> Select:
    """
    Create a Select widget for layout, offering "vertical" or "horizontal".
    """
    options = [("vertical", "vertical"), ("horizontal", "horizontal")]
    return Select(options=options, id=select_id)

def create_theme_select(manager: InteractiveManager, select_id: str = "theme-select") -> Select:
    """
    Create a Select widget containing the manager's available themes.
    """
    theme_options = []
    for name in manager.available_themes:
        # Make the display label user-friendly
        label = name.replace("_", " ").title()
        theme_options.append((label, name))
    return Select(options=theme_options, id=select_id)

def handle_layout_selection(manager: InteractiveManager, changed_value: str) -> None:
    """
    Update the manager's final_summary to record the newly selected layout.
    """
    manager.layout = changed_value
    manager.final_summary["Layout"] = changed_value
    if hasattr(manager.diagram, "layout"):
        manager.diagram.layout = changed_value

def handle_theme_selection(manager: InteractiveManager, changed_value: str) -> None:
    """
    Update the manager's final_summary to record the newly selected theme.
    """
    manager.final_summary["Theme"] = changed_value
    logger.debug(f"User selected theme: {changed_value}")

def build_preview_lines(
    final_summary: dict,
    diagram_nodes: dict,
    ephemeral_nodes: set[str] = None,
    current_level: int = None
) -> list[str]:
    """
    Build lines describing each node's assigned level/icon, plus ephemeral status if needed.
    
    :param final_summary: The dictionary with "Levels" and "Icons" keys (and more).
    :param diagram_nodes: The dictionary of nodes from manager.diagram.nodes (so we know which nodes exist).
    :param ephemeral_nodes: A set of node names that are ephemeral for the current screen (may be None).
    :param current_level: If relevant, pass the current level for a Levels screen so we can show "(will be X)".
    :return: A list of lines for display, e.g. ["node1 Lvl=1 Icon=router", ...].
    """
    if ephemeral_nodes is None:
        ephemeral_nodes = set()
    
    all_node_names = sorted(diagram_nodes.keys())
    lines = []

    # Helper to get assigned level
    def get_assigned_level(n: str) -> int | str:
        for lvl, nds in final_summary["Levels"].items():
            if n in nds:
                return lvl
        # if ephemeral for levels
        if current_level and (n in ephemeral_nodes):
            return f"(will be {current_level})"
        return "-"

    # Helper to get assigned icon
    def get_assigned_icon(n: str) -> str:
        for icon_name, nds in final_summary["Icons"].items():
            if n in nds:
                return icon_name
        return "-"

    # Sort by assigned level (or ephemeral level).
    # We can do a custom sort key if we want to keep the same order as before:
    def sort_key(n: str):
        lvl = get_assigned_level(n)
        # If it's a string like "(will be 2)", we can parse out the int, but let's just rank them last
        if isinstance(lvl, int):
            return lvl
        else:
            return 9999
    sorted_nodes = sorted(all_node_names, key=sort_key)

    for n in sorted_nodes:
        assigned_lvl = get_assigned_level(n)
        assigned_ic = get_assigned_icon(n)

        if assigned_lvl == 9999:
            assigned_lvl = "-"  

        lines.append(f"{n:<20s} Lvl={assigned_lvl} Icon={assigned_ic if assigned_ic != '-' else '-'}")
    return lines

def build_group_grid(groups_dict: dict[Any, list[str]], layout: str) -> str:
    """
    Build a simple textual 'grid' of the group -> node-list, 
    respecting layout = 'vertical' vs. 'horizontal'.

    groups_dict: e.g. {1: ["spine1", "spine2"], 2: [...]} 
                 or {"router": [...], "switch": [...], "host": [...]}
    layout: 'vertical' or 'horizontal'

    Returns a multiline string, either row-based or column-based.
    """

    # Sort the group keys so we have stable order (levels ascending or icons sorted).
    sorted_keys = sorted(groups_dict.keys(), key=lambda x: str(x))

    # If 'vertical' => each group is a single row, joined by spaces.
    # e.g. 
    # Level 1 => spine1 spine2
    # Level 2 => leaf1 leaf2 leaf3
    # ...
    # If 'horizontal' => we want columns for each group. 
    # That requires pivoting the data so we line up nodes in each group.
    # For example, if we have 3 groups of varying lengths, we transpose them.

    if layout == "vertical":
        lines = []
        for group_key in sorted_keys:
            node_list = groups_dict[group_key]
            row = "  ".join(node_list)
            lines.append(row)
        return "\n".join(lines)

    else:  # layout == "horizontal"
        # We'll pivot columns: each group is one column, top to bottom.
        # 1) find max # of nodes among groups
        max_len = max(len(groups_dict[k]) for k in sorted_keys) if sorted_keys else 0

        # 2) build rows by taking i-th element of each group
        #    if i is out of range, we do e.g. '' or ' '.
        rows = []
        for i in range(max_len):
            row_parts = []
            for group_key in sorted_keys:
                node_list = groups_dict[group_key]
                val = node_list[i] if i < len(node_list) else ""
                row_parts.append(f"{val:8s}")  # fixed width or just use val
            rows.append("  ".join(row_parts).rstrip())
        return "\n".join(rows)


def update_preview_common(
    screen: Screen,
    manager: InteractiveManager,
    ephemeral_nodes: set[str],
    current_level: int | None
) -> None:
    """
    Updates the screen.preview_label with both 'detailed lines' and 'grid-style' blocks.

    :param screen: The Screen that holds preview_label (either AssignLevelsScreen or AssignIconsScreen).
    :param manager: The InteractiveManager, containing final_summary, ephemeral_icons, etc.
    :param ephemeral_nodes: The set of ephemeral nodes for this screen's toggles.
    :param current_level: If this is a Levels screen, pass the current level; else None.
    """

    # 1) Build the "detailed lines" portion using build_preview_lines
    lines = build_preview_lines(
        final_summary=manager.final_summary,
        diagram_nodes=manager.diagram.nodes,
        ephemeral_nodes=ephemeral_nodes,
        current_level=current_level,
    )

    groups_dict = manager.final_summary["Levels"]

    # 3) Pull layout from final_summary
    layout = manager.final_summary["Layout"]

    # 4) Build a grid
    grid_str = build_group_grid(groups_dict, layout)

    # 5) Combine them
    combined = "\n".join([
        *lines,
        "",
        "==== Preview ====",
        grid_str
    ])

    # 6) Show it on screen
    screen.preview_label.update(combined)


# ----------------------------------------------------------------
# A custom message for toggles in the ListView
# ----------------------------------------------------------------
class ItemToggled(Message):
    """Fired when a _MultiCheckItem changes its .checked state."""
    def __init__(self, sender: _MultiCheckItem, checked: bool):
        super().__init__()
        self.sender = sender
        self.checked = checked


# ----------------------------------------------------------------
# Main manager
# ----------------------------------------------------------------
class InteractiveManager:
    """
    Holds references for the TUI wizard:
    - diagram, icon_to_group_mapping, containerlab_data, output_file, etc.
    - final_summary with "Levels", "Icons", "Layout", "Theme".
    - ephemeral_icons: ephemeral sets keyed by icon index for the Icons screen.
    """

    def __init__(self):
        # Default layout is "vertical"
        self.layout = "vertical"
        self.ephemeral_icons: Dict[int, set[str]] = {}

    def run_interactive_mode(
        self,
        diagram: Any,
        available_themes: List[str],
        icon_to_group_mapping: Dict[str, str],
        containerlab_data: Dict[str, Any],
        output_file: str,
        processor,
        prefix: str,
        lab_name: str,
    ) -> Dict[str, Any]:
        """
        Launch the TUI wizard. Return final_summary with "Levels", "Icons", "Layout", "Theme".
        """
        self.diagram = diagram
        self.available_themes = available_themes
        self.icon_to_group_mapping = icon_to_group_mapping
        self.containerlab_data = containerlab_data
        self.output_file = output_file
        self.processor = processor
        self.prefix = prefix
        self.lab_name = lab_name

        # We'll store final user selections here
        self.final_summary = {
            "Levels": {},
            "Icons": {},
            "Layout": self.layout,
            "Theme": "nokia",
        }

        app = _WizardApp(self)
        app.run()
        return self.final_summary


# ----------------------------------------------------------------
# The main TUI app
# ----------------------------------------------------------------
class _WizardApp(App[None]):
    """
    The multi-step wizard with 4 screens (Levels -> Icons -> Summary -> UpdateFile).
    """
    CSS_PATH = "style.tcss"  # <-- We use a separate file now, instead of CSS = """..."""

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.levels_screen = AssignLevelsScreen(self.manager)

    def on_mount(self) -> None:
        self.push_screen(self.levels_screen)

    def action_goto_icons(self) -> None:
        new_icons_screen = AssignIconsScreen(self.manager)
        self.push_screen(new_icons_screen)

    def action_goto_summary(self) -> None:
        new_summary_screen = SummaryScreen(self.manager)
        self.push_screen(new_summary_screen)

    def action_quit_wizard(self) -> None:
        self.exit()


# ----------------------------------------------------------------
# 1) Levels Screen
# ----------------------------------------------------------------
class AssignLevelsScreen(Screen):
    """
    Assign levels to nodes, with ephemeral toggles.
    Also presents a layout + theme dropdown.
    """

    current_level: reactive[int] = reactive(1)

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager

        self.title_label = Static("")
        #self.instr_label = Static("('Confirm Level' => finalize).")
        self.list_view = ToggleListView()

        self.prev_btn = Button("Previous Step", id="previous-level")
        self.confirm_btn = Button("Confirm Level", id="confirm")
        self.exit_btn = Button("Exit Wizard", id="exit-button")

        self.layout_select = create_layout_select("layout-select-level")
        self.theme_select = create_theme_select(manager, "theme-select-level")

        self.preview_label = Static("Preview (by level)")

        self.all_node_names = sorted(manager.diagram.nodes.keys())
        self.ephemeral_nodes = set()

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-container"):
            with Vertical(id="left-pane"):
                yield self.title_label
                #yield self.instr_label
                yield self.list_view

                with Vertical(id="button-row"):
                    yield self.layout_select
                    yield self.theme_select
                    yield self.prev_btn
                    yield self.confirm_btn
                    yield self.exit_btn

            with ScrollableContainer(id="right-pane"):
                yield self.preview_label

    def on_show(self) -> None:
        self.title_label.update(f"Assign Levels (Level {self.current_level})")

        self.preview_label.styles.overflow_x = "auto"
        self.preview_label.styles.overflow_y = "auto"
        self.preview_label.styles.width = "auto"
        self.preview_label.styles.height = "auto"

        current_layout = self.manager.final_summary.get("Layout", "vertical")
        self.layout_select.value = current_layout

        current_theme = self.manager.final_summary.get("Theme", "nokia")
        self.theme_select.value = current_theme

        self.prev_btn.display = (self.current_level > 1)

        self._fill_list()
        self._update_preview()

    def on_screen_resume(self) -> None:
        self.on_show()

    def _fill_list(self) -> None:
        self.list_view.clear()

        for node in self.all_node_names:
            is_in_current_level = node in self.manager.final_summary["Levels"].get(self.current_level, [])
            assigned_level = None
            for lvl, nds in self.manager.final_summary["Levels"].items():
                if node in nds:
                    assigned_level = lvl
                    break

            should_show = (
                assigned_level is None
                or assigned_level == self.current_level
                or node in self.ephemeral_nodes
            )

            if should_show:
                item = _MultiCheckItem(node)
                item.checked = (node in self.ephemeral_nodes or is_in_current_level)
                self.list_view.append(item)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "previous-level":
            if self.current_level > 1:
                self.current_level -= 1
                self.on_show()

        elif event.button.id == "confirm":
            # finalize ephemeral => remove from old final, place in new
            for n in self.ephemeral_nodes:
                for lvl, nds in self.manager.final_summary["Levels"].items():
                    if n in nds:
                        nds.remove(n)
                self.manager.final_summary["Levels"].setdefault(self.current_level, []).append(n)
                self.manager.diagram.nodes[n].graph_level = self.current_level
                self._update_clab(n, self.current_level)

            self.ephemeral_nodes.clear()

            assigned_count = sum(len(v) for v in self.manager.final_summary["Levels"].values())
            total_nodes = len(self.all_node_names)
            if assigned_count >= total_nodes:
                self.app.action_goto_icons()
            else:
                self.current_level += 1
                self.on_show()

            list_view = self.query_one(ToggleListView)
            list_view.index = 0  # set highlight to the top item
            list_view.focus()

        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()

    def _update_preview(self) -> None:
        if isinstance(self, AssignLevelsScreen):
            ephemeral = self.ephemeral_nodes
            current_lvl = self.current_level
        else:  # AssignIconsScreen
            ephemeral = self.manager.ephemeral_icons.get(self.current_icon_index, set())
            current_lvl = None

        update_preview_common(
            screen=self,
            manager=self.manager,
            ephemeral_nodes=ephemeral,
            current_level=current_lvl,
        )



    def _update_clab(self, node_name: str, lvl: int) -> None:
        marker = f"{self.manager.prefix}-{self.manager.lab_name}-"
        if node_name.startswith(marker):
            unformatted = node_name.replace(marker, "", 1)
        else:
            unformatted = node_name

        node_data = self.manager.containerlab_data["topology"]["nodes"].get(unformatted, {})
        node_data.setdefault("labels", {})
        node_data["labels"]["graph-level"] = lvl
        self.manager.containerlab_data["topology"]["nodes"][unformatted] = node_data

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "layout-select-level":
            handle_layout_selection(self.manager, event.value)
            self._update_preview()
        elif event.select.id == "theme-select-level":
            handle_theme_selection(self.manager, event.value)

    def on_item_toggled(self, event: ItemToggled) -> None:
        node_name = event.sender.text
        if event.checked:
            for lvl, nds in self.manager.final_summary["Levels"].items():
                if node_name in nds:
                    nds.remove(node_name)
            self.ephemeral_nodes.add(node_name)
        else:
            self.ephemeral_nodes.discard(node_name)
        self._update_preview()
        event.stop()


# ----------------------------------------------------------------
# 2) Icons Screen
# ----------------------------------------------------------------
class AssignIconsScreen(Screen):
    """
    Allows assigning (and de-assigning) nodes to icons.
    Clicking "Confirm Icons" finalizes ephemeral toggles.
    Also has layout + theme selects, preserving user selection.
    """

    current_icon_index: reactive[int] = reactive(0)

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager

        self.title_label = Static("Assign Icons")
        #self.instr_label = Static("(Toggle nodes -> ephemeral; 'Confirm Icons' -> finalize).")
        self.list_view = ToggleListView()

        self.prev_btn = Button("Previous Step", id="previous-icon")
        self.confirm_btn = Button("Confirm Icons", id="confirm")
        self.exit_btn = Button("Exit Wizard", id="exit-button")

        # Layout + Theme selects
        self.layout_select_icons = create_layout_select("layout-select-icons")
        self.theme_select_icons = create_theme_select(manager, "theme-select-icons")

        self.preview_label = Static("Preview Icons", id="preview-icons")

        # We read the icons list from manager.icon_to_group_mapping
        self.icons_list = sorted(self.manager.icon_to_group_mapping.keys())
        self.all_node_names = sorted(self.manager.diagram.nodes.keys())

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-container"):
            with Vertical(id="left-pane"):
                yield self.title_label
                #yield self.instr_label
                yield self.list_view
                with Vertical(id="button-row"):
                    yield self.layout_select_icons
                    yield self.theme_select_icons
                    yield self.prev_btn
                    yield self.confirm_btn
                    yield self.exit_btn
            with ScrollableContainer(id="right-pane"):
                yield self.preview_label

    def on_show(self) -> None:
        """Called when this screen is first pushed."""
        # Preselect the layout & theme from manager.final_summary
        current_layout = self.manager.final_summary.get("Layout", "vertical")
        self.layout_select_icons.value = current_layout

        self.preview_label.styles.overflow_x = "auto"
        self.preview_label.styles.overflow_y = "auto"
        self.preview_label.styles.width = "auto"
        self.preview_label.styles.height = "auto"

        current_theme = self.manager.final_summary.get("Theme", "nokia")
        self.theme_select_icons.value = current_theme

        # Fill the list & preview
        self._repopulate()

    def on_screen_resume(self) -> None:
        """Called if we return to this screen after pop from another."""
        self.on_show()

    def _repopulate(self) -> None:
        """Re-populate the ListView and the preview based on current icon index."""
        self._fill_list_for_current_icon()
        self._update_preview()

    def _fill_list_for_current_icon(self) -> None:
        """Fill the list with nodes relevant for the current icon, respecting ephemeral toggles."""
        self.list_view.clear()

        if not self.icons_list:
            self.title_label.update("No icons configured - press 'Done/Next' to continue")
            # Show all nodes unassigned
            for n in self.all_node_names:
                item = _MultiCheckItem(n)
                item.checked = False
                self.list_view.append(item)
            return

        # Which icon are we assigning now?
        icon = self.icons_list[self.current_icon_index]
        self.title_label.update(
            f"Choose nodes for icon '{icon}' "
            f"({self.current_icon_index + 1}/{len(self.icons_list)})"
        )

        ephem_set = self.manager.ephemeral_icons.setdefault(self.current_icon_index, set())

        # Collect nodes assigned to other icons so we don't show them unless ephemeral overrides
        assigned_other_icons = set()
        for assigned_icon, nds in self.manager.final_summary["Icons"].items():
            if assigned_icon != icon:
                assigned_other_icons.update(nds)

        # The final list for *this* icon
        final_for_this_icon = set(self.manager.final_summary["Icons"].get(icon, []))

        # Show nodes if:
        # - not assigned to a different icon
        # - OR ephemeral for this icon
        # - OR final for this icon
        for node_name in self.all_node_names:
            if (
                node_name not in assigned_other_icons
                or node_name in ephem_set
                or node_name in final_for_this_icon
            ):
                item = _MultiCheckItem(node_name)
                if node_name in ephem_set or node_name in final_for_this_icon:
                    item.checked = True
                self.list_view.append(item)

    def _update_preview(self) -> None:
        if isinstance(self, AssignLevelsScreen):
            ephemeral = self.ephemeral_nodes
            current_lvl = self.current_level
        else:  # AssignIconsScreen
            ephemeral = self.manager.ephemeral_icons.get(self.current_icon_index, set())
            current_lvl = None

        update_preview_common(
            screen=self,
            manager=self.manager,
            ephemeral_nodes=ephemeral,
            current_level=current_lvl,
        )


    def _update_clab(self, node_name: str, icon: str) -> None:
        """
        Update containerlab data with the new 'graph-icon' label, so the
        containerlab file / mod.yml can reflect the chosen icon.
        """
        marker = f"{self.manager.prefix}-{self.manager.lab_name}-"
        if node_name.startswith(marker):
            unformatted = node_name.replace(marker, "", 1)
        else:
            unformatted = node_name

        node_data = self.manager.containerlab_data["topology"]["nodes"].get(unformatted, {})
        if "labels" not in node_data:
            node_data["labels"] = {}
        node_data["labels"]["graph-icon"] = icon
        self.manager.containerlab_data["topology"]["nodes"][unformatted] = node_data

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle layout/theme selection changes."""
        if event.select.id == "layout-select-icons":
            handle_layout_selection(self.manager, event.value)
            self._update_preview()
        elif event.select.id == "theme-select-icons":
            handle_theme_selection(self.manager, event.value)

    def on_item_toggled(self, event: ItemToggled) -> None:
        """Handle toggling a node on/off in ephemeral for the current icon."""
        if not self.icons_list:
            return  # no icons => skip

        ephem_set = self.manager.ephemeral_icons.setdefault(self.current_icon_index, set())
        node_name = event.sender.text

        if event.checked:
            ephem_set.add(node_name)
        else:
            ephem_set.discard(node_name)

        self._update_preview()
        event.stop()

    def _are_all_nodes_assigned(self) -> bool:
        """
        Check if all nodes have been assigned to an icon (any icon).
        """
        assigned_nodes = set()
        for icon_nodes in self.manager.final_summary["Icons"].values():
            assigned_nodes.update(icon_nodes)
        return len(assigned_nodes) >= len(self.all_node_names)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation and finalizing ephemeral toggles."""
        if event.button.id == "previous-icon":
            if self.current_icon_index > 0:
                self.current_icon_index -= 1
                self._repopulate()
            else:
                # If at the first icon index, go back to the previous screen
                self.app.pop_screen()

        elif event.button.id == "confirm":
            if not self.icons_list:
                # No icons? go to summary
                self.app.action_goto_summary()
                return

            # 1) Identify current icon
            icon = self.icons_list[self.current_icon_index]
            ephem_set = self.manager.ephemeral_icons.setdefault(self.current_icon_index, set())

            # 2) Remove ephemeral nodes from other icons (ensuring one icon per node)
            for other_icon, nds in self.manager.final_summary["Icons"].items():
                if other_icon != icon:
                    for n in list(nds):
                        if n in ephem_set:
                            nds.remove(n)

            # 3) Convert final list for this icon to a set
            final_nodes = self.manager.final_summary["Icons"].setdefault(icon, [])
            final_set = set(final_nodes)

            # 4) Remove from final any nodes no longer ephemeral (handles de-select)
            for node in list(final_set):
                if node not in ephem_set:
                    final_set.remove(node)

            # 5) Add ephemeral toggles to final, update diagram + clab
            for node in ephem_set:
                if node not in final_set:
                    final_set.add(node)
                    # 5a) set diagram data
                    self.manager.diagram.nodes[node].graph_icon = icon
                    # 5b) also set containerlab data
                    self._update_clab(node, icon)

            # 6) Store back in final summary
            self.manager.final_summary["Icons"][icon] = list(final_set)

            # 7) Clear ephemeral for this icon
            ephem_set.clear()

            # 8) If this was the last icon or all assigned => summary
            if self.current_icon_index >= len(self.icons_list) - 1 or self._are_all_nodes_assigned():
                self.app.action_goto_summary()
            else:
                # Move to the next icon
                self.current_icon_index += 1
                self._repopulate()

            # Refresh the preview
            self._update_preview()

            list_view = self.query_one(ToggleListView)
            list_view.index = 0  # set highlight to the top item
            list_view.focus()

        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()


# ----------------------------------------------------------------
# 3) Summary Screen
# ----------------------------------------------------------------
class SummaryScreen(Screen):
    """
    The third screen. Also created new each time for a full re-mount.
    """

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager

        self.preview_label = Static("", id="summary-preview")
        self.summary_label = Static("", id="summary-text")

        self.prev_btn = Button("Previous Step", id="previous-summary")
        self.yes_btn = Button("Yes", id="yes-button")
        self.no_btn = Button("No", id="no-button")
        self.exit_btn = Button("Exit Wizard", id="exit-button")

    def compose(self) -> ComposeResult:
        # Use a main vertical container so it fills the screen top-to-bottom
        with Vertical(id="main-container"):
            # A scrollable container so we can see everything if it’s large
            with ScrollableContainer(id="summary-scroll"):
                # First, the preview
                yield self.preview_label
                # Then the traditional textual summary
                yield self.summary_label

            # At the bottom, the button row
            with Horizontal(id="button-row"):
                yield self.prev_btn
                yield self.yes_btn
                yield self.no_btn
                yield self.exit_btn

    def on_show(self) -> None:

        ephemeral = set()
        current_lvl = None  # or None means icons are done

        # We can use the same update_preview_common approach:
        preview_lines = build_preview_lines(
            final_summary=self.manager.final_summary,
            diagram_nodes=self.manager.diagram.nodes,
            ephemeral_nodes=ephemeral,
            current_level=current_lvl,
        )
        layout = self.manager.final_summary["Layout"]

        self.preview_label.styles.overflow_x = "auto"
        self.preview_label.styles.overflow_y = "auto"
        self.preview_label.styles.width = "auto"
        self.preview_label.styles.height = "auto"

        grid_str = build_group_grid(self.manager.final_summary["Levels"], layout)

        combined_preview = "\n".join([
            *preview_lines,
            "",
            "==== Final Grid Preview ====",
            grid_str
        ])

        self.preview_label.update(combined_preview)

        # 2) Now build the old textual summary in a similar way
        lines = []
        lines.append("\n==== LEVELS ====")
        for lvl in sorted(self.manager.final_summary["Levels"].keys()):
            node_list = self.manager.final_summary["Levels"][lvl]
            lines.append(f"  Level {lvl}: {', '.join(node_list)}")

        lines.append("\n==== ICONS ====")
        for icon in sorted(self.manager.final_summary["Icons"].keys()):
            nds = self.manager.final_summary["Icons"][icon]
            lines.append(f"  Icon '{icon}': {', '.join(nds)}")

        lines.append(f"\nLayout = {self.manager.layout}")

        chosen_theme = self.manager.final_summary.get("Theme", "nokia")
        lines.append(f"Theme = {chosen_theme}")

        lines.append("Do you want to keep this configuration?")

        self.summary_label.update("\n".join(lines))


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "previous-summary":
            self.app.pop_screen()
        elif event.button.id == "yes-button":
            self.app.push_screen(UpdateFileScreen(self.manager))
        elif event.button.id == "no-button":
            self.app.pop_screen()
        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()


# ----------------------------------------------------------------
# 4) UpdateFileScreen
# ----------------------------------------------------------------
class UpdateFileScreen(Screen):
    """
    Final screen. Yes => save mod.yml, No => do not save. Then exit wizard.
    """

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager

        self.question = Static("Update ContainerLab file with your new config?")
        self.yes_button = Button("Yes", id="yes-button")
        self.no_button = Button("No", id="no-button")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield self.question
            with Horizontal(id="button-row"):
                yield self.yes_button
                yield self.no_button

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-button":
            mod_file = self.manager.output_file.rsplit('.', 1)[0] + ".mod.yml"
            self.manager.processor.save_yaml(self.manager.containerlab_data, mod_file)
            print(f"ContainerLab file updated: {mod_file}")
            self.app.action_quit_wizard()
        elif event.button.id == "no-button":
            print("File not updated.")
            self.app.action_quit_wizard()


# ----------------------------------------------------------------
# Toggling ListItem
# ----------------------------------------------------------------
class ToggleListView(ListView):
    """A ListView that toggles items with the space key when they are highlighted."""

    # Define a binding: press space -> call action_toggle_item
    BINDINGS = [
        Binding("space", "toggle_item", "Toggle the currently highlighted item"),
        Binding("tab", "focus_confirm_button", "Move focus to confirm button"),
    ]

    def action_toggle_item(self) -> None:
        """
        Toggle the currently highlighted item, if it's a _MultiCheckItem.
        """
        if self.index is not None:
            # self.index is the 0-based index of the highlighted item
            item = self.children[self.index]
            if isinstance(item, _MultiCheckItem):
                item.checked = not item.checked

    def action_focus_confirm_button(self) -> None:
        screen = self.screen
        if screen:
            confirm_btn = screen.query_one("#confirm", Button)
            if confirm_btn:
                confirm_btn.focus()

class _MultiCheckItem(ListItem):
    checked: bool = reactive(False)

    def __init__(self, text: str):
        super().__init__()
        self.text = text
        self.can_focus = True
        self._label = None

    def compose(self) -> ComposeResult:
        mark = "[x]" if self.checked else "[ ]"
        self._label = Static(f"{mark} {self.text}")
        yield self._label

    def watch_checked(self, old_val: bool, new_val: bool) -> None:
        # This updates the text whenever .checked changes
        mark = "[x]" if new_val else "[ ]"
        if self._label:
            self._label.update(f"{mark} {self.text}")
        # Also post ItemToggled
        self.post_message(ItemToggled(self, new_val))

    def on_click(self) -> None:
        # If the user clicks with the mouse, also toggle
        self.checked = not self.checked

