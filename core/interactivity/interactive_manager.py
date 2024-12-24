"""
interactive_manager.py

A Textual-based multi-step wizard for assigning "graph_level" and "graph_icon"
to nodes, with immediate ("live") preview. Now also sorts nodes in the preview
by assigned (or ephemeral) level, so low-level nodes appear on top.

Requires textual >= 0.18.0
"""

import logging
from typing import Dict, Any, Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem
from textual.reactive import reactive
from textual import events
from textual.message import Message
from textual.widgets._list_view import ListView as LV

logger = logging.getLogger(__name__)


# -------------------------------
# A custom message for toggles
# -------------------------------
class ItemToggled(Message):
    """Fired when a _MultiCheckItem changes its .checked state."""
    def __init__(self, sender: "._MultiCheckItem", checked: bool):
        super().__init__()
        self.sender = sender
        self.checked = checked


# -------------------------------
# Main manager
# -------------------------------
class InteractiveManager:
    def __init__(self):
        pass

    def run_interactive_mode(
        self,
        nodes: dict,                  
        icon_to_group_mapping: dict,  
        containerlab_data: dict,      
        output_file: str,
        processor,                    
        prefix: str,
        lab_name: str,
    ) -> dict:
        self.nodes = nodes
        self.icon_to_group_mapping = icon_to_group_mapping
        self.containerlab_data = containerlab_data
        self.output_file = output_file
        self.processor = processor
        self.prefix = prefix
        self.lab_name = lab_name

        self.final_summary = {
            "Levels": {},
            "Icons": {},
        }

        app = _WizardApp(self)
        app.run()
        return self.final_summary


# -------------------------------
# The main TUI App
# -------------------------------
class _WizardApp(App[None]):
    """
    The main wizard application, containing screens for levels, icons, summary, etc.
    """

    CSS = """
    Screen {
        layout: vertical;
        background: black;
        color: white;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }
    #left-pane {
        width: 70%;
        border: tall $accent;
        padding: 1 2;
    }
    #right-pane {
        width: 30%;
        border: tall $secondary;
        padding: 1 2;
    }
    #button-row {
        margin-top: 1;
        height: auto;
    }
    _MultiCheckItem {
        padding: 0 1;
    }
    """

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.levels_screen = AssignLevelsScreen(manager)
        self.icons_screen = AssignIconsScreen(manager)
        self.summary_screen = SummaryScreen(manager)

    def on_mount(self) -> None:
        self.push_screen(self.levels_screen)

    def action_goto_icons(self) -> None:
        self.push_screen(self.icons_screen)

    def action_goto_summary(self) -> None:
        self.push_screen(self.summary_screen)

    def action_quit_wizard(self) -> None:
        self.exit()


# ------------------------------------------
# 1) Assign Levels, with ephemeral toggles
# ------------------------------------------
class AssignLevelsScreen(Screen):
    current_level: reactive[int] = reactive(0)

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager

        self.title_label = Static("Assign Levels")
        self.instr_label = Static("(Click or press Space to toggle; Items update preview immediately; 'Confirm' finalizes them.)")

        self.list_view = ListView()
        self.confirm_btn = Button("Confirm for this Level", id="confirm-level")
        self.done_btn = Button("Done (Skip leftover)", id="done-level")
        self.exit_btn = Button("Exit Wizard", id="exit-button")

        self.preview_label = Static("Preview", id="preview-levels")
        self.preview_label.styles.color = "yellow"

        self.unassigned_nodes = list(self.manager.nodes.keys())
        # ephemeral toggles
        self.ephemeral_nodes = set()

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-container"):
            with Vertical(id="left-pane"):
                yield self.title_label
                yield self.instr_label
                yield self.list_view
                with Vertical(id="button-row"):
                    yield self.confirm_btn
                    yield self.done_btn
                    yield self.exit_btn

            with Vertical(id="right-pane"):
                yield self.preview_label

    def on_show(self) -> None:
        self.current_level = 1
        self._fill_list()

    def on_list_view_highlighted(self, event: LV.Highlighted) -> None:
        if event.item is not None:
            event.item.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-level":
            # Move ephemeral_nodes into final_summary
            if self.ephemeral_nodes:
                for node_name in self.ephemeral_nodes:
                    self.manager.final_summary["Levels"].setdefault(self.current_level, []).append(node_name)
                    self.manager.nodes[node_name].graph_level = self.current_level
                    self._update_clab(node_name, self.current_level)
                    if node_name in self.unassigned_nodes:
                        self.unassigned_nodes.remove(node_name)

            self.ephemeral_nodes.clear()
            self.current_level += 1
            self._fill_list()

        elif event.button.id == "done-level":
            self.app.action_goto_icons()

        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()

        self._update_preview()

    def _fill_list(self):
        if not self.unassigned_nodes:
            self.app.action_goto_icons()
            return
        self.list_view.clear()
        self.title_label.update(f"Select nodes for Level {self.current_level}:")
        self.ephemeral_nodes.clear()

        for node_name in sorted(self.unassigned_nodes):
            self.list_view.append(_MultiCheckItem(node_name))

        self._update_preview()

    def _update_preview(self):
        """
        We'll show a line for each node, sorted by assigned-level ascending (lowest on top).
        If ephemeral, treat that as current_level.
        If no assigned or ephemeral, treat as level=999 to sink it to bottom.
        """
        lines = []
        all_nodes = sorted(self.manager.nodes.keys())

        # Build a function that returns the numeric level used for sorting
        def get_level(node_name: str) -> int:
            # final assigned
            for lvl, node_list in self.manager.final_summary["Levels"].items():
                if node_name in node_list:
                    return lvl
            # ephemeral
            if node_name in self.ephemeral_nodes:
                return self.current_level
            return 999

        # sort by that function
        sorted_nodes = sorted(all_nodes, key=get_level)

        for n in sorted_nodes:
            # figure out assigned level
            assigned_level: Optional[int] = None
            for lvl, node_list in self.manager.final_summary["Levels"].items():
                if n in node_list:
                    assigned_level = lvl
                    break
            # ephemeral override
            if (assigned_level is None) and (n in self.ephemeral_nodes):
                assigned_level = f"(will be {self.current_level})"

            # figure out assigned icon
            assigned_icon = None
            for ic, ndlist in self.manager.final_summary["Icons"].items():
                if n in ndlist:
                    assigned_icon = ic
                    break

            lines.append(f"{n:<20s} Lvl={assigned_level if assigned_level else '-'}  Icon={assigned_icon if assigned_icon else '-'}")

        self.preview_label.update("Preview of all nodes:\n" + "\n".join(lines))

    def _update_clab(self, node_name, level: int):
        unformatted = node_name
        marker = f"{self.manager.prefix}-{self.manager.lab_name}-"
        if unformatted.startswith(marker):
            unformatted = unformatted.replace(marker, "", 1)
        node_data = self.manager.containerlab_data["topology"]["nodes"].get(unformatted, {})
        if "labels" not in node_data:
            node_data["labels"] = {}
            self.manager.containerlab_data["topology"]["nodes"][unformatted] = node_data
        node_data["labels"]["graph-level"] = level

    def on_item_toggled(self, event: ItemToggled) -> None:
        node_name = event.sender.text
        if event.checked:
            self.ephemeral_nodes.add(node_name)
        else:
            self.ephemeral_nodes.discard(node_name)
        self._update_preview()
        event.stop()


# ------------------------------------------
# 2) Assign Icons, also ephemeral
# ------------------------------------------
class AssignIconsScreen(Screen):
    current_icon_index: reactive[int] = reactive(-1)

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager

        self.title_label = Static("Assign Icons")
        self.instr_label = Static("(Toggle => immediate preview; 'Confirm' => finalize).")
        self.list_view = ListView()

        self.confirm_btn = Button("Confirm these nodes", id="confirm-icon")
        self.done_btn = Button("Done / Next Step", id="done-icon")
        self.exit_btn = Button("Exit Wizard", id="exit-button")

        self.preview_label = Static("Preview Icons")
        self.preview_label.styles.color = "green"

        self.icons_list = sorted(self.manager.icon_to_group_mapping.keys())
        self.ephemeral_icons = set()

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-container"):
            with Vertical(id="left-pane"):
                yield self.title_label
                yield self.instr_label
                yield self.list_view
                with Vertical(id="button-row"):
                    yield self.confirm_btn
                    yield self.done_btn
                    yield self.exit_btn

            with Vertical(id="right-pane"):
                yield self.preview_label

    def on_show(self) -> None:
        self.current_icon_index = -1
        self._next_icon()

    def on_list_view_highlighted(self, event: LV.Highlighted) -> None:
        if event.item is not None:
            event.item.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-icon":
            if self.ephemeral_icons:
                icon = self.icons_list[self.current_icon_index]
                for node_name in self.ephemeral_icons:
                    self.manager.final_summary["Icons"].setdefault(icon, []).append(node_name)
                    self.manager.nodes[node_name].graph_icon = icon
                    self._update_clab(node_name, icon)
            self.ephemeral_icons.clear()
            self._next_icon()

        elif event.button.id == "done-icon":
            self.app.action_goto_summary()

        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()

        self._update_preview()

    def _next_icon(self):
        self.current_icon_index += 1
        if self.current_icon_index >= len(self.icons_list):
            self.app.action_goto_summary()
            return
        icon = self.icons_list[self.current_icon_index]
        self.title_label.update(f"Choose nodes for icon '{icon}'")
        self.ephemeral_icons.clear()
        self.list_view.clear()

        # fill list
        all_nodes = list(self.manager.nodes.keys())
        for n in sorted(all_nodes):
            self.list_view.append(_MultiCheckItem(n))

        self._update_preview()

    def _update_preview(self):
        """
        Sort by assigned level ascending, then show assigned icon (or ephemeral icon).
        """
        lines = []
        all_nodes = list(self.manager.nodes.keys())

        # figure out current icon
        current_icon = None
        if 0 <= self.current_icon_index < len(self.icons_list):
            current_icon = self.icons_list[self.current_icon_index]

        def get_level(n: str) -> int:
            for lvl, node_list in self.manager.final_summary["Levels"].items():
                if n in node_list:
                    return lvl
            return 999

        sorted_nodes = sorted(all_nodes, key=get_level)

        for n in sorted_nodes:
            # assigned level
            assigned_level = None
            for lvl, node_list in self.manager.final_summary["Levels"].items():
                if n in node_list:
                    assigned_level = lvl
                    break

            # assigned icon
            assigned_icon = None
            for ic, ndlist in self.manager.final_summary["Icons"].items():
                if n in ndlist:
                    assigned_icon = ic
                    break

            # ephemeral?
            if current_icon and (n in self.ephemeral_icons) and (assigned_icon is None):
                assigned_icon = f"(will be '{current_icon}')"

            lines.append(f"{n:<20s} Lvl={assigned_level if assigned_level else '-'}  Icon={assigned_icon if assigned_icon else '-'}")

        self.preview_label.update("Preview:\n" + "\n".join(lines))

    def _update_clab(self, node_name, icon: str):
        unformatted = node_name
        marker = f"{self.manager.prefix}-{self.manager.lab_name}-"
        if unformatted.startswith(marker):
            unformatted = unformatted.replace(marker, "", 1)
        node_data = self.manager.containerlab_data["topology"]["nodes"].get(unformatted, {})
        if "labels" not in node_data:
            node_data["labels"] = {}
            self.manager.containerlab_data["topology"]["nodes"][unformatted] = node_data
        node_data["labels"]["graph-icon"] = icon

    def on_item_toggled(self, event: ItemToggled) -> None:
        node_name = event.sender.text
        if event.checked:
            self.ephemeral_icons.add(node_name)
        else:
            self.ephemeral_icons.discard(node_name)
        self._update_preview()
        event.stop()


# -------------------------------
# 3) Summary screen
# -------------------------------
class SummaryScreen(Screen):
    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.summary_label = Static("")
        self.yes_btn = Button("Yes", id="yes-button")
        self.no_btn = Button("No", id="no-button")
        self.exit_btn = Button("Exit Wizard", id="exit-button")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield self.summary_label
            yield self.yes_btn
            yield self.no_btn
            yield self.exit_btn

    def on_show(self) -> None:
        final = self.manager.final_summary
        text = "==== LEVELS ====\n"
        for lvl in sorted(final["Levels"].keys()):
            nodes_ = final["Levels"][lvl]
            text += f"  Level {lvl}: {', '.join(nodes_)}\n"
        text += "\n==== ICONS ====\n"
        for ic, ndlist in sorted(final["Icons"].items()):
            text += f"  Icon '{ic}': {', '.join(ndlist)}\n"
        text += "\nDo you want to keep this configuration?"
        self.summary_label.update(text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-button":
            self.app.push_screen(UpdateFileScreen(self.manager))
        elif event.button.id == "no-button":
            self.app.pop_screen(to=self.app.levels_screen)
        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()


# -------------------------------
# 4) Optionally update .clab file
# -------------------------------
class UpdateFileScreen(Screen):
    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.question = Static("Update ContainerLab file with your new config?")
        self.yes_button = Button("Yes", id="yes-button")
        self.no_button = Button("No", id="no-button")

    def compose(self) -> ComposeResult:
        yield self.question
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


# -------------------------------
# The toggling ListItem
# -------------------------------
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
        mark = "[x]" if new_val else "[ ]"
        if self._label:
            self._label.update(f"{mark} {self.text}")
        # Let parent know
        self.post_message(ItemToggled(self, new_val))

    def on_click(self) -> None:
        self.checked = not self.checked

    def on_key(self, event: events.Key) -> None:
        if event.key == "space":
            self.checked = not self.checked
            event.stop()
