#!/usr/bin/env python3

import taipy.gui.builder as tgb

from rampt.gui.helpers import *

# Intemediary paths for selections
## File selection
uploaded_paths = {}
select_folders = {}

selection_trees_pruned = {}
selection_trees_full = {}

selected = {}


def create_expandable_setting(
    create_methods: dict, title: str, hover_text: str = "", expanded=False, **kwargs
):
    with tgb.expandable(title=title, hover_text=hover_text, expanded=expanded, **kwargs):
        with tgb.layout(columns="0.02 1 0.02", gap="2%"):
            tgb.part()
            with tgb.part():
                for title, create_method in create_methods.items():
                    with tgb.part(class_name="segment-box"):
                        if title:
                            tgb.text(f"##### {title}", mode="markdown")
                        create_method()
                    tgb.html("br")
            tgb.part()


def create_file_selection(
    process: str,
    param_attribute_in: str = "scheduled_ios",
    io_key: str = "standard",
    file_dialog_kwargs: dict = {},
):
    naming_list = [process, param_attribute_in, io_key] if io_key else [process, param_attribute_in]

    # Construct intermediary dicts
    selector_id = "_".join(naming_list)

    selection_trees_pruned.update({selector_id: []})
    selection_trees_full.update({selector_id: []})
    uploaded_paths.update({selector_id: "."})
    select_folders.update({selector_id: False})
    selected.update({selector_id: []})

    def construct_selection_tree(state, new_path: StrPath = None):
        """
        Make the selection tree

        :param state: State of taipy
        :type state: State
        :param new_path: Added path (selected in file_selector), defaults to None
        :type new_path: StrPath, optional
        """
        new_path = (
            new_path
            if new_path
            else get_attribute_recursive(state, f"uploaded_paths.{selector_id}")
        )

        if new_path != ".":
            selection_trees_full[selector_id] = path_nester.update_nested_paths(
                selection_trees_full[selector_id], new_paths=new_path
            )
            pruned_tree = path_nester.prune_lca(nested_paths=selection_trees_full[selector_id])
            set_attribute_recursive(state, f"selection_trees_pruned.{selector_id}", pruned_tree)

    def update_selection(state, name, value):
        """
        Merge values of selection with I/O dictionary

        :param state: State of taipy application
        :type state: State
        :param name: Name of variable
        :type name: str
        :param value: Selected value (usually dict)
        :type value: Any
        """
        # Extract selected path from value-dict
        selected_labels = [
            element.get("label") if isinstance(element, dict) else element for element in value
        ]
        # Merge path into i/o dictionary
        if io_key:
            io_dictionary = get_attribute_recursive(state, f"{process}_params.{param_attribute_in}")
            io_dictionary = io_dictionary if io_dictionary else {}
            io_dictionary.update({io_key: selected_labels})
        set_attribute_recursive(
            state, f"{process}_params.{param_attribute_in}", io_dictionary, refresh=True
        )

    with tgb.layout(columns="1 4", columns__mobile="1", gap="5%"):
        # Selector
        with tgb.part():
            tgb.toggle(f"{{select_folders.{selector_id}}}", label="Select folder")
            with tgb.part(render="{local}"):
                tgb.button(
                    "Select in",
                    on_action=lambda state: construct_selection_tree(
                        state,
                        open_file_folder(
                            select_folder=get_attribute_recursive(
                                state, f"select_folders.{selector_id}"
                            ),
                            **file_dialog_kwargs,
                        ),
                    ),
                )
            with tgb.part(render="{not local}"):
                tgb.file_selector(
                    f"{{uploaded_paths.{selector_id}}}",
                    label="Select in",
                    extensions="*",
                    drop_message=f"Drop files/folders for {process} here:",
                    multiple=True,
                    on_action=lambda state: construct_selection_tree(state),
                )

        # Selection tree
        tgb.tree(
            f"{{selected.{selector_id}}}",
            lov=f"{{selection_trees_pruned.{selector_id}}}",
            label=f"Select in for {process}",
            filter=True,
            multiple=io_key is None,
            expanded=True,
            on_change=lambda state, name, value: update_selection(state, name, value),
        )


# List selectors
list_options = {}
list_uploaded = {}
list_selected = {}


def create_list_selection(
    process: str,
    attribute: str = "batch",
    extensions: str = "*",
    name: str = "batch file",
    default_value=str(Path.home()),
    file_dialog_kwargs: dict = {},
):
    selector_id = f"{process}_{attribute}"
    list_options.update({selector_id: []})
    list_uploaded.update({selector_id: ""})
    list_selected.update({selector_id: default_value})

    def construct_selection_list(state, new_path: StrPath = None):
        new_path = (
            new_path if new_path else get_attribute_recursive(state, f"list_uploaded.{selector_id}")
        )

        if new_path:
            if new_path not in list_options:
                list_options[selector_id].append(new_path)
            set_attribute_recursive(state, f"list_options.{selector_id}", list_options[selector_id])

    def update_selection(state, name, value):
        set_attribute_recursive(state, f"{process}_params.{attribute}", value, refresh=True)

    with tgb.layout(columns="1 4", columns__mobile="1", gap="5%"):
        with tgb.part(render="{local}"):
            tgb.button(
                f"Select {name}",
                on_action=lambda state: construct_selection_list(
                    state,
                    open_file_folder(
                        multiple=False,
                        filetypes=[
                            (f"{ext[1:]} files", f"*{ext}") for ext in extensions.split(",")
                        ],
                        initialdir=get_directory(default_value),
                        **file_dialog_kwargs,
                    ),
                ),
            )
        with tgb.part(render="{not local}"):
            tgb.file_selector(
                f"{{list_uploaded.{selector_id}}}",
                label=f"Select {name}",
                extensions=extensions,
                drop_message=f"Drop {name} for {process} here:",
                multiple=False,
                on_action=lambda state: construct_selection_list(state),
            )

        tgb.selector(
            f"{{list_selected.{selector_id}}}",
            lov=f"{{list_options.{selector_id}}}",
            label=f"Select a {name} for {process}",
            filter=True,
            multiple=False,
            mode="radio",
            on_change=lambda state, name, value: update_selection(state, name, value),
        )


def set_if_chosen(state, attribute: str):
    selected_path = open_file_folder(multiple=False)
    if selected_path:
        set_attribute_recursive(state, attribute, refresh=True)


def create_exec_selection(
    process: str, exec_name: str, exec_attribute="exec_path", render: str = True
):
    with tgb.part(render=render):
        with tgb.layout(columns="1 1 1 1", columns__mobile="1", gap="5%"):
            tgb.button(
                "Select executable",
                active="{local}",
                on_action=lambda state: set_if_chosen(state, f"{process}_params.exec_path"),
            )
            tgb.input(
                f"{{{process}_params.{exec_attribute}}}",
                active="{local}",
                label=f"`{exec_name}` executable",
                hover_text=f"You may enter the path to {exec_name}.",
            )
            tgb.part()
            tgb.part()
