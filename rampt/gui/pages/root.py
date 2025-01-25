#!/usr/bin/env python3

import os
import tempfile
import json
from pathlib import Path

import taipy as tp
import taipy.gui.builder as tgb
from taipy.gui import notify

# Submodules
from rampt.gui.pages.analysis.analysis import *
from rampt.gui.pages.analysis.summary import *
from rampt.gui.pages.analysis.visualization import *
from rampt.gui.pages.annotation.gnps import *
from rampt.gui.pages.annotation.sirius import *
from rampt.gui.pages.conversion.conversion import *
from rampt.gui.pages.feature_finding.feature_finding import *
from rampt.gui.pages.general.general import *

# Configuration
from rampt.gui.configuration.config import *


# Logger
rampt_user_path = os.path.abspath(os.path.join(Path.home(), ".rampt"))
os.makedirs(rampt_user_path, exist_ok=True)
log_path = os.path.abspath(os.path.join(rampt_user_path, "rampt_log.txt"))
logger.log_file_path = log_path

# Working directory
local = True
work_dir_root = tempfile.gettempdir()

# SYNCHRONISATION (First GUI, then Scenario)
## Synchronisation of GUI
param_segment_names = [
    "global",
    "conversion",
    "feature_finding",
    "gnps",
    "sirius",
    "summary",
    "analysis",
]
save_path = None
save_file_types = [("json files", "*.json")]


def construct_params_dict(state, param_segment_names: list = param_segment_names):
    params = {}
    for segment_name in param_segment_names:
        segment_params = get_attribute_recursive(state, f"{segment_name}_params")
        params[f"{segment_name}_params"] = segment_params.dict_representation()
    return params


def save_params(state, path: StrPath = None, scenario_name: str = None):
    global save_path

    if path:
        path = path
    elif scenario_name:
        path = os.path.join(work_dir_root, f"{scenario_name}_config.json")
    elif save_path:
        path = save_path
    else:
        logger.warn(f"Saving to default path: {os.path.join(work_dir_root, 'Default_config.json')}")
        path = os.path.join(work_dir_root, "Default_config.json")

    with open(path, "w") as file:
        json.dump(construct_params_dict(state), file, indent=4)
    save_path = path


def load_params(state, path: StrPath = None, scenario_name: str = "Default"):
    path = path if path else os.path.join(work_dir_root, f"{scenario_name}_config.json")
    with open(path, "r") as file:
        params = json.loads(file.read())

    for segment_name, segment_params in params.items():
        for attribute, param in segment_params.items():
            set_attribute_recursive(state, f"{segment_name}.{attribute}", param, refresh=True)


# SCENARIO
scenario = tp.create_scenario(ms_analysis_config, name="Default")

out_path_root = None

## Synchronisation of Scenario
# TODO: Change structure so that previous steps are preferred as inputs
match_data_node = {
    # Used to decide which values (the last in the list) are used in case of conflicts
    # Processed chained Inputs are preffered to scheduled targets
    # In Data Paths
    # TODO: ADJUST DATA NODE SEARCH
    "raw_data_paths": [""],
    "community_formatted_data_paths": [
        "feature_finding_params.scheduled_in",
        "conversion_params.processed_out",
    ],
    "processed_data_paths": [
        "summary_params.scheduled_in['quantification']",
        "gnps_params.scheduled_in",
        "sirius_params.scheduled_in",
        "feature_finding_params.processed_out",
    ],
    "gnps_annotation_paths": [
        "summary_params.scheduled_in['annotation']",
        "gnps_params.processed_out",
    ],
    "sirius_annotation_paths": [
        "summary_params.scheduled_in['annotation']",
        "sirius_params.processed_out",
    ],
    "summary_data_paths": ["analysis_params.scheduled_in", "summary_params.processed_out"],
    "analysis_data_paths": ["analysis_params.processed_out"],
    # Out Data
    "out_path_root": ["out_path_root"],
    # Batches and more
    "mzmine_batch": ["feature_finding_params.batch"],
    "mzmine_log": ["feature_finding_params.log_paths", "gnps_params.mzmine_log"],
    "sirius_config": ["sirius_params.config"],
    "sirius_projectspace": ["sirius_params.projectspace"],
}

optional_data_nodes = ["out_path_root", "sirius_annotation_paths", "gnps_annotation_paths"]

entrypoints = ["↔️ Conversion", "🔍 Feature finding", "✒️ Annotation", "🧺 Summary", "📈 Analysis"]
entrypoint = "↔️ Conversion"


# TODO merge dicts with | to get node
match_entrypoint = {
    "*": {"out_path_root": ["out_path_root"]},
    "↔️ Conversion": {
        "raw_data_paths": ["conversion_params.scheduled_ios"],
        "mzmine_batch": ["feature_finding_params.batch"],
        "mzmine_user": ["feature_finding_params.user"],
    },
    "🔍 Feature finding": {
        "community_formatted_data_paths": ["feature_finding_params.scheduled_ios"],
        "mzmine_batch": ["feature_finding_params.batch"],
        "mzmine_user": ["feature_finding_params.user"],
    },
    "✒️ Annotation": {
        "processed_data_paths": [
            "summary_params.scheduled_ios",
            "gnps_params.scheduled_ios",
            "sirius_params.scheduled_ios",
        ]
    },
    "🧺 Summary": {
        "gnps_annotation_paths": ["summary_params.scheduled_ios"],
        "sirius_annotation_paths": ["summary_params.scheduled_ios"],
    },
    "📈 Analysis": {"summary_data_paths": ["analysis_params.scheduled_ios"]},
}


def lock_scenario(state):
    # Fetch scenario
    scenario = state.scenario

    # Obtain parameters
    parameters = construct_params_dict(state)

    # Write Nones to optional nodes
    for optional_data_node in optional_data_nodes:
        scenario.data_nodes.get(optional_data_node).write(None)

    # Get required nodes
    entrypoint_required_nodes = match_entrypoint.get(get_attribute_recursive(state, "entrypoint"))
    entrypoint_required_nodes = entrypoint_required_nodes | match_entrypoint.get("*")

    # Iterate over required nodes
    for data_node_id, access_points in entrypoint_required_nodes.items():
        content = {}
        # Iterate over access points of data_node
        for access_point in access_points:
            # Extract information from access_point
            access_point = regex.split(r"\.|(?:\[[\"\'](.*?)[\"\']\])", access_point)
            value = parameters
            for access_part in access_point:
                value = value.get(access_part)

            # Merge content dictionary (Last entry overwrites) just accept last of rest
            content = content | value if isinstance(value, dict) else value

        # Write to data node
        scenario.data_nodes.get(data_node_id).write(content)

    # Write param nodes
    for param_data_node_id, param in parameters.items():
        scenario.data_nodes.get(param_data_node_id).write(param)

    state.scenario = scenario
    state.refresh("scenario")


"""
def lock_scenario(state):
    global scenario
    scenario = state.scenario

    # Retrieve parameters
    params = construct_params_dict(state)
    data_nodes = params.copy()

    # Iterate over all possible matches
    for data_node_key, attribute_keys in match_data_node.items():
        # Iterate over all possible places, where data nodes info could come from
        for istate_attribute in attribute_keys:
            # Split to get attributes
            attribute_split = regex.split(r"\.|(?:\[[\"\'](.*?)[\"\']\])", state_attribute)

            # Filter empty strings out
            attribute_split = [part for part in attribute_split if part]

            # Get final value
            value = params
            for key_part in attribute_split:
                # Case there is a list of values that needs to be passed from dict entry
                if isinstance(value, list):
                    value = [entry.get(key_part) for entry in value]
                else:
                    value = value.get(key_part)

            # Check whether the value is written or optional
            if value:
                # Write value to node directory
                for state_attribute in attribute_keys:
                    set_attribute_recursive(state, state_attribute, value, refresh=True)
                data_nodes[data_node_key] = value

    # Write Nones to optional nodes
    for optional_data_node in optional_data_nodes:
        scenario.data_nodes.get(optional_data_node).write(None)

    # Write values to data node
    for key, data_node in scenario.data_nodes.items():
        if data_nodes.get(key) is not None:
            data_node.write(data_nodes.get(key))

    state.scenario = scenario
    state.refresh("scenario")
"""


## Interaction
def add_scenario(state, id, payload):
    # Save previous scenario
    save_params(state, scenario_name=state.scenario.name)

    # Lock new scenario into current configuration
    lock_scenario(state)
    save_params(state, scenario_name=payload.get("label", "Default"))


def change_scenario(state, id, scenario_name):
    # Load parameters into Gui
    if scenario_name:
        load_params(state, scenario_name=scenario_name)

    # Push gui parameters into scenario
    lock_scenario(state)


# JOBS
job = None


style = {".sticky-part": {"position": "sticky", "align-self": "flex-start", "top": "10px"}}

with tgb.Page(style=style) as configuration:
    with tgb.layout(columns="1 3 1", columns__mobile="1", gap="2.5%"):
        # Left part
        with tgb.part(class_name="sticky-part"):
            # Save button
            with tgb.layout(columns="1 1.2 1", gap="2%"):
                tgb.button("💾 Save", on_action=lambda state, id, payload: save_params(state))
                tgb.button(
                    "💾 Save as",
                    on_action=lambda state, id, payload: save_params(
                        state,
                        path=open_file_folder(save=True, multiple=False, filetypes=save_file_types),
                    ),
                )
                tgb.button(
                    "📋 Load",
                    on_action=lambda state, id, payload: load_params(
                        state, path=open_file_folder(multiple=False, filetypes=save_file_types)
                    ),
                )
            tgb.button("◀️ Lock scenario", on_action=lambda state, id, payload: lock_scenario(state))

            # Scenario selector
            tgb.text("#### Scenarios", mode="markdown")
            tgb.scenario_selector("{scenario}", on_creation=add_scenario, on_change=change_scenario)

        # Middle part
        with tgb.part():
            tgb.text("## ⚙️ Configuration", mode="markdown")

            tgb.text("Where would you like to enter the workflow ?", mode="markdown")
            tgb.selector(
                "{entrypoint}", lov="{entrypoints}", dropdown=True, filter=True, multiple=False
            )

            # Create possible settings
            # TODO: Unify outpath selection, where the folders are then created
            # TODO: Parse Batch file
            # TODO: Pass entrypoint to backend
            # TODO: Reflect selection of entrypoint in value filling (Discard all I/O entries, not associated to entrypoint)
            with tgb.expandable(
                title="⭐ Recommended settings:",
                hover_text="Settings that are recommended for entering the workflow at the selected point.",
                expanded=True,
            ):
                create_conversion()
                create_feature_finding()
                create_gnps()
                create_sirius()
                create_summary()
                create_analysis()

                tgb.html("br")

                # Out Path
                with tgb.part(render="{local}"):
                    tgb.text("###### Select root folder for output", mode="markdown")
                    tgb.button(
                        "Select out",
                        on_action=lambda state: set_attribute_recursive(
                            state,
                            "out_path_root",
                            open_file_folder(select_folder=True, multiple=False),
                            refresh=True,
                        ),
                    )

            # Create advanced settings
            tgb.text("### Advanced settings", mode="markdown")
            create_expandable_setting(
                create_methods={"": create_general_advanced},
                title="🌐 General",
                hover_text="General settings, that are applied globally.",
            )

            create_expandable_setting(
                create_methods={"": create_conversion_advanced},
                title="↔️ Conversion",
                hover_text="Convert manufacturer files into community formats.",
            )

            create_expandable_setting(
                create_methods={"": create_feature_finding_advanced},
                title="🔍 Feature finding",
                hover_text="Find features with MZmine through applying steps via a batch file.",
            )

            create_expandable_setting(
                create_methods={"GNPS": create_gnps_advanced, "Sirius": create_sirius_advanced},
                title="✒️ Annotation",
                hover_text="Annotation of data with GNPS and Sirius.",
            )

            create_expandable_setting(
                create_methods={
                    "🧺 Summary": create_summary_advanced,
                    "📈 Analysis": create_analysis_advanced,
                },
                title="📈 Analysis",
                hover_text="Statistical analysis of annotated features.",
            )

            # Scenario / workflow management
            # TODO: Callback after scenario creation
            tgb.text("## 🎬 Scenario management", mode="markdown")
            tgb.scenario(
                "{scenario}",
                show_properties=False,
                show_tags=False,
                show_sequences=True,
                on_submission_change=lambda state, submission, details: notify(
                    state, "I", f"{submission.get_label()} submitted."
                ),
            )

            # Job management
            tgb.text("## 🐝 Jobs", mode="markdown")
            tgb.job_selector("{job}")

            # Display Graph of scenario
            tgb.scenario_dag("{scenario}")

        # Right part
        with tgb.part():
            pass


with tgb.Page(style=style) as visualization:
    create_visualization()
