import logging
from typing import Dict, Any

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem
from textual.reactive import reactive
from textual import events
from textual.widgets._list_view import ListView as LV

logger = logging.getLogger(__name__)


class InteractiveManager:
    def __init__(self):
        pass

    def run_interactive_mode(
        self,
        nodes: dict,                  # node_name -> Node object
        icon_to_group_mapping: dict,  # e.g. styles["icon_to_group_mapping"]
        containerlab_data: dict,      # entire .clab YAML
        output_file: str,
        processor,                    # e.g. YAMLProcessor
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

        # We'll store final user selections here
        self.final_summary = {
            "Levels": {},  # e.g. {1: [nodeA, nodeB], 2: [nodeC], ...}
            "Icons": {},   # e.g. {"router": [nodeA], "leaf": [nodeB]}
        }

        # Launch the wizard
        app = _WizardApp(self)
        app.run()

        return self.final_summary


class _WizardApp(App[None]):
    """
    The main wizard application, containing screens for levels, icons, summary, etc.
    """

    # Let’s attach our CSS.
    #CSS_PATH = "wizard.tcss"   # <-- Ensure wizard.tcss is in the same directory or adjust path.

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.levels_screen = AssignLevelsScreen(manager)
        self.icons_screen = AssignIconsScreen(manager)
        self.summary_screen = SummaryScreen(manager)

    def on_mount(self) -> None:
        # Show the levels screen first
        self.push_screen(self.levels_screen)

    def action_goto_icons(self) -> None:
        self.push_screen(self.icons_screen)

    def action_goto_summary(self) -> None:
        self.push_screen(self.summary_screen)

    def action_quit_wizard(self) -> None:
        # Once done, exit app
        self.exit()


#
# 1) Assign Levels
#
class AssignLevelsScreen(Screen):
    current_level: reactive[int] = reactive(0)
    unassigned_nodes: list[str] = []

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.title_label = Static("")
        self.instr_label = Static("(Click or press Space to toggle; Enter to confirm selection.)")
        self.list_view = ListView(id="level_list")
        self.confirm_btn = Button("Confirm for this Level", id="confirm-level")
        self.done_btn = Button("Done (Skip leftover)", id="done-level")
        # New exit button
        self.exit_btn = Button("Exit Wizard", id="exit-button")

        self.unassigned_nodes = list(self.manager.nodes.keys())

    def compose(self) -> ComposeResult:
        yield self.title_label
        yield self.instr_label
        yield self.list_view
        yield self.confirm_btn
        yield self.done_btn
        yield self.exit_btn  # <-- The new button

    def on_show(self) -> None:
        self.current_level = 0
        self._next_level()

    def on_list_view_highlighted(self, event: LV.Highlighted) -> None:
        if event.item is not None:
            event.item.focus()

    def _next_level(self):
        if not self.unassigned_nodes:
            self.app.action_goto_icons()
            return
        self.current_level += 1
        self.title_label.update(f"Select nodes for Level {self.current_level}:")
        self.list_view.clear()
        for node_name in sorted(self.unassigned_nodes):
            item = _MultiCheckItem(node_name)
            self.list_view.append(item)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-level":
            checked = []
            for item in self.list_view.children:
                if isinstance(item, _MultiCheckItem) and item.checked:
                    checked.append(item.text)
            if checked:
                for node_name in checked:
                    self.manager.final_summary["Levels"].setdefault(self.current_level, []).append(node_name)
                    self.manager.nodes[node_name].graph_level = self.current_level
                    self._update_clab(node_name, level=self.current_level)
                    if node_name in self.unassigned_nodes:
                        self.unassigned_nodes.remove(node_name)
            self._next_level()

        elif event.button.id == "done-level":
            # skip leftover. unassigned remain level=0
            self.app.action_goto_icons()

        elif event.button.id == "exit-button":
            # Abort the wizard entirely
            self.app.action_quit_wizard()

    def _update_clab(self, node_name: str, level: int):
        unformatted = node_name
        marker = f"{self.manager.prefix}-{self.manager.lab_name}-"
        if unformatted.startswith(marker):
            unformatted = unformatted.replace(marker, "", 1)
        node_data = self.manager.containerlab_data["topology"]["nodes"].get(unformatted, {})
        if "labels" not in node_data:
            node_data["labels"] = {}
            self.manager.containerlab_data["topology"]["nodes"][unformatted] = node_data
        node_data["labels"]["graph-level"] = level


#
# 2) Assign Icons
#
class AssignIconsScreen(Screen):
    current_icon_index: reactive[int] = reactive(-1)
    icons_list: list[str] = []

    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.title_label = Static("")
        self.instr_label = Static("(Click or press Space to toggle; Enter to confirm selection.)")
        self.list_view = ListView(id="icon_list")
        self.confirm_btn = Button("Confirm these nodes", id="confirm-icon")
        self.done_btn = Button("Done / Next Step", id="done-icon")
        # Could add an exit here too if you want
        self.exit_btn = Button("Exit Wizard", id="exit-button")

        self.icons_list = list(self.manager.icon_to_group_mapping.keys())
        self.icons_list.sort()

    def compose(self) -> ComposeResult:
        yield self.title_label
        yield self.instr_label
        yield self.list_view
        yield self.confirm_btn
        yield self.done_btn
        yield self.exit_btn

    def on_show(self) -> None:
        self.current_icon_index = -1
        self._next_icon()

    def on_list_view_highlighted(self, event: LV.Highlighted) -> None:
        if event.item is not None:
            event.item.focus()

    def _next_icon(self):
        self.current_icon_index += 1
        if self.current_icon_index >= len(self.icons_list):
            self.app.action_goto_summary()
            return
        icon = self.icons_list[self.current_icon_index]
        self.title_label.update(f"Choose nodes for icon '{icon}':")
        self.list_view.clear()
        node_names = list(self.manager.nodes.keys())
        for n in sorted(node_names):
            self.list_view.append(_MultiCheckItem(n))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-icon":
            icon = self.icons_list[self.current_icon_index]
            checked = []
            for item in self.list_view.children:
                if isinstance(item, _MultiCheckItem) and item.checked:
                    checked.append(item.text)
            if checked:
                for node_name in checked:
                    self.manager.final_summary["Icons"].setdefault(icon, []).append(node_name)
                    self.manager.nodes[node_name].graph_icon = icon
                    self._update_clab(node_name, icon)
            self._next_icon()

        elif event.button.id == "done-icon":
            self.app.action_goto_summary()

        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()

    def _update_clab(self, node_name: str, icon: str):
        unformatted = node_name
        marker = f"{self.manager.prefix}-{self.manager.lab_name}-"
        if unformatted.startswith(marker):
            unformatted = unformatted.replace(marker, "", 1)
        node_data = self.manager.containerlab_data["topology"]["nodes"].get(unformatted, {})
        if "labels" not in node_data:
            node_data["labels"] = {}
            self.manager.containerlab_data["topology"]["nodes"][unformatted] = node_data
        node_data["labels"]["graph-icon"] = icon


#
# 3) Show Summary
#
class SummaryScreen(Screen):
    def __init__(self, manager: InteractiveManager):
        super().__init__()
        self.manager = manager
        self.summary_label = Static("", id="summary-label")
        self.yes_btn = Button("Yes", id="yes-button")
        self.no_btn = Button("No", id="no-button")
        self.exit_btn = Button("Exit Wizard", id="exit-button")

    def compose(self) -> ComposeResult:
        yield self.summary_label
        yield self.yes_btn
        yield self.no_btn
        yield self.exit_btn

    def on_show(self) -> None:
        final = self.manager.final_summary
        text = "==== LEVELS ====\n"
        for lvl in sorted(final["Levels"].keys()):
            node_list = final["Levels"][lvl]
            text += f"  Level {lvl}: {', '.join(node_list)}\n"
        text += "\n==== ICONS ====\n"
        for icon in sorted(final["Icons"].keys()):
            node_list = final["Icons"][icon]
            text += f"  Icon '{icon}': {', '.join(node_list)}\n"
        text += "\nDo you want to keep this configuration?"
        self.summary_label.update(text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-button":
            self.app.push_screen(UpdateFileScreen(self.manager))
        elif event.button.id == "no-button":
            # Go back to the first screen so user can reassign if needed
            self.app.pop_screen(to=self.app.levels_screen)
        elif event.button.id == "exit-button":
            self.app.action_quit_wizard()


#
# 4) Optional update .clab file
#
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


#
# A “multi-check” item that toggles on click or space
#
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
        if self._label is not None:
            self._label.update(f"{mark} {self.text}")

    def on_click(self) -> None:
        self.checked = not self.checked

    def on_key(self, event: events.Key) -> None:
        if event.key == "space":
            self.checked = not self.checked
            event.stop()

