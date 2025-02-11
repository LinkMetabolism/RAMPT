#!/usr/bin/env python
"""
Methods that are helpful for general processing.
"""

import os
import subprocess
import time
import regex
import requests
import dask
from tqdm.dask import TqdmCallback
import tee_subprocess
import functools

from rampt.helpers.types import *
from rampt.helpers.logging import *


# File operations
def get_internal_filepath(file: str) -> StrPath:
    """
    Return the filepath of a passed file.

    :param file: file
    :type file: str
    :return: path of file on system
    :rtype: StrPath
    """
    return os.path.abspath(file)


### ROOT Directory
ROOT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(get_internal_filepath(__file__)), "..", "..")
)


def construct_path(*args: list[StrPath]) -> StrPath:
    """
    Construct a path from the given list of paths

    :return: Combine path
    :rtype: StrPath
    """
    return os.path.abspath(os.path.join(*args))


def make_new_dir(dir: StrPath) -> bool:
    """
    Make a directory, if one does not already exist in its place.

    :param dir: path to directory
    :type dir: StrPath
    :return: Whether a new directory has been made
    :rtype: bool
    """
    if not os.path.isdir(dir):
        os.mkdir(dir)
        return True
    return False


def get_directory(path: StrPath) -> StrPath:
    """
    Extract directory path from file or directory path.

    :param path: File or directory path
    :type path: StrPath
    :return: Directory path
    :rtype: StrPath
    """
    # Base case
    if os.path.isdir(path):
        return path

    directory = os.path.dirname(path)
    if os.path.isdir(directory):
        return directory
    else:
        logger.error(message=f"{path} is not a file or directory", error_type=ValueError)


# List operations
def extend_list(array, extension) -> list:
    """
    Generic method to expand a list or append elements

    :param array: Starting element/list
    :type array: any
    :param extension: Element or list to extend with
    :type extension: any
    :return: Expanded list
    :rtype: list
    """
    array = array if isinstance(array, list) else [array]
    if isinstance(extension, list):
        array.extend(extension)
    else:
        array.append(extension)
    return array


def to_list(object) -> list:
    """
    Put object into list, if not yet a list

    :param object: an object
    :type object: any
    :return: List with object.
    :rtype: list
    """
    if isinstance(object, list):
        return object
    else:
        return [object]


def insert_unlinked_list(arr: list, index: int, object) -> list:
    """
    Insert and element into a copy of a list.

    :param arr: Old list
    :type arr: list
    :param index: Position of insertion
    :type index: int
    :param object: Object to be inserted
    :type object: Any
    :return: List with element at given index
    :rtype: list
    """
    arr_new = arr.copy()
    arr_new.insert(index, object)
    return arr_new


def get_uniques(arr: list) -> list:
    """
    Get unique values from list

    :param arr: Old list
    :type arr: list
    :return: List with unique values from old list
    :rtype: list
    """
    arr_new = []
    for element in arr:
        if element not in arr_new:
            arr_new.append(element)
    return arr_new


# Dict operations
def get_if_dict(container: Any, keys: list[str] | str, default_value: Any = None) -> Any:
    """
    Extracts a key from a container via .get if container is a dict.

    :param container: Container of data
    :type container: Any
    :param keys: Keys for dictionary to try with. If not matching, None is returned.
    :type keys: list[str]|str
    :param default_value: Default value to return when key is not present, defaults to None.
    :type default_value: Any, optional
    :return: Extracted value
    :rtype: Any
    """
    if isinstance(container, dict):
        if isinstance(keys, list):
            if len(keys) == 1:
                return container.get(keys[0], default_value)
            else:
                return [container.get(key, default_value) for key in keys]
        else:
            return container.get(keys, default_value)
    else:
        return container


def flatten_values(obj: Any) -> list:
    """
    Flatten values in dictionaries and lists in lists to one list of values.

    :param obj: Object to be flattened
    :type obj: Any
    :return: Flat list
    :rtype: list
    """
    if isinstance(obj, dict):
        return flatten_values(list(obj.values()))
    elif isinstance(obj, list) or isinstance(obj, tuple):
        accumulator = []
        for x in obj:
            accumulator += flatten_values(obj=x)
        return accumulator
    else:
        return [obj]


def stretch_to_list_of_dicts(dictionary: dict) -> list:
    """
    Stretch a dictionary with a list of lists as entry to a list of dictionaries with a single entry from the list.

    :param dictionary: Dictionary with list of lists
    :type dictionary: dict
    :return: Stretched list
    :rtype: list
    """
    # Extract lists
    lists_in_dict = []
    keys_in_dict = []
    for key, value in dictionary.items():
        for list_in_dict in value:
            lists_in_dict.append(list_in_dict)
            keys_in_dict.append(key)

    # Find maximum length
    max_lenght = 0
    for list_in_dict in lists_in_dict:
        length = len(list_in_dict) if isinstance(list_in_dict, list) else 1
        max_lenght = max(max_lenght, length)

    # Populated stretched list
    stretched_list = []
    for i in range(max_lenght):
        single_dict = {}
        listed_keys = []

        for j, key in enumerate(keys_in_dict):
            # Fill with None, if the length of the list is not sufficient
            if not isinstance(lists_in_dict[j], list):
                if i == 0:
                    element = lists_in_dict[j]
                else:
                    element = None
            elif i < len(lists_in_dict[j]):
                element = lists_in_dict[j][i]
            else:
                element = None

            # Use keys to populate single dict
            if key not in single_dict:
                single_dict[key] = element
            elif key not in listed_keys:
                single_dict[key] = [single_dict[key]] + [element]
                listed_keys.append(key)
            else:
                single_dict[key] = single_dict[key] + [element]

        stretched_list.append(single_dict)

    return stretched_list


# String operations
def change_case_str(s: str, range, conversion: str) -> str:
    """
    Change the case of part of a string.

    :param s: Input string.
    :type s: str
    :param range: Range of string that is to be changed
    :type range: SupportsIndex
    :param conversion: conversion
    :type conversion: str
    :return: Output string.
    :rtype: str
    """
    str_list = list(s)
    selection = s[range]

    match conversion:
        case "upper":
            selection = selection.upper()
        case "lower":
            selection = selection.lower()
        case _:
            logger.error(
                message=f"conversion {conversion} is invalid. Choose upper/lower as a valid conversion.",
                error_type=ValueError,
            )

    str_list[range] = selection

    return "".join(str_list)


class Substring(str):
    """
    Class for matching substrings, rather than strings

    :param str: string
    :type str: str-type
    """

    def __eq__(self, other) -> bool:
        """
        Define == as containing the string

        :param other: other String
        :type other: Any
        :return: Whether the string is contained in the Substring
        :rtype: bool
        """
        return other in self


# Path operations
class Path_Nester:
    """
    Class for nesting paths into a list of directories with lists of subdirectories.
    """

    def __init__(
        self,
        nesting_depth: int = 1,
        nested_paths: list = [],
        id_name: str = "id",
        dir_name: str = "label",
        sub_name: str = "children",
    ):
        """
        Initalize Path_Nester

        :param nesting_depth: Depth of nesting that is used to group final instances (number of subs in last sub), defaults to 1
        :type nesting_depth: int, optional
        :param nested_paths: Current nested paths, defaults to []
        :type nested_paths: list, optional
        :param dir_name: Name for directory structures, defaults to "Directory"
        :type dir_name: str, optional
        :param sub_name: Name for substructures, defaults to "Sub"
        :type sub_name: str, optional
        """
        self.nesting_depth = nesting_depth
        self.dir_name = dir_name
        self.sub_name = sub_name
        self.id_name = id_name
        self.id_counter = 0

    def add_nested_lists(self, split_steps, nested_paths, complete_path):
        self.id_counter += 1
        step = split_steps[0]

        if len(split_steps) == self.nesting_depth:  # Break recursion at desired depth
            if isinstance(nested_paths, list):
                entry_present = [
                    True
                    for nested_path in nested_paths
                    if nested_path.get(self.dir_name) == complete_path
                ]
                if not entry_present:
                    nested_paths.append(
                        {
                            self.id_name: str(self.id_counter),
                            self.dir_name: complete_path,
                            self.sub_name: [],
                        }
                    )
            else:
                nested_paths = [
                    {
                        self.id_name: str(self.id_counter),
                        self.dir_name: step,
                        self.sub_name: [complete_path],
                    }
                ]
            return nested_paths

        split_found = False
        for nested_path in nested_paths:
            if isinstance(nested_path, dict) and step == nested_path.get(self.dir_name):
                nested_path[self.sub_name] = self.add_nested_lists(
                    split_steps[1:], nested_path.get(self.sub_name), complete_path
                )
                split_found = True

        if not split_found:
            nested_paths.append(
                {
                    self.id_name: str(self.id_counter),
                    self.dir_name: step,
                    self.sub_name: self.add_nested_lists(split_steps[1:], [], complete_path),
                }
            )

        return nested_paths

    def update_nested_paths(self, nested_paths, new_paths: str | list[str]):
        if isinstance(new_paths, str):
            new_paths = [new_paths]
        for new_path in new_paths:
            in_paths = os.path.normpath(new_path)
            split_path = in_paths.split(os.sep)
            nested_paths = self.add_nested_lists(split_path[1:], nested_paths, in_paths)
        return nested_paths

    def prune_lca(self, nested_paths):
        if len(nested_paths) == 1 and len(nested_paths[0][self.sub_name]) == 1:
            return self.prune_lca(nested_paths=nested_paths[0][self.sub_name])
        else:
            return nested_paths


# File operations
def open_last_n_line(filepath: str, n: int = 1) -> str:
    """
    Open the n-th line from the back of a file

    :param filepath: Path to the file
    :type filepath: str
    :param n: position from the back, defaults to 1
    :type n: int, optional
    :return: n-th last line
    :rtype: str
    """
    num_newlines = 0
    with open(filepath, "rb") as f:
        # catch OSError in case of a one line file
        f.seek(-2, os.SEEK_END)
        while num_newlines < n:
            f.seek(-2, os.SEEK_CUR)
            if f.read(1) == b"\n":
                num_newlines += 1
        return f.readline().decode()


def open_last_line_with_content(filepath: str) -> str:
    """
    Extract the last line which does not only contain whitespace from a file.

    :param filepath: Path to the file
    :type filepath: str
    :return: Last line with content (not only whitespaces)
    :rtype: str
    """
    n = 1
    while n < 1e3:
        try:
            line = open_last_n_line(filepath=filepath, n=n)
        except OSError as e:
            raise logger.error(
                message=f"File {filepath} does not contain a line with content",
                error_type=ValueError,
                raise_error=False,
            ) from e
        if regex.search(r".*\S.*", line):
            return line
        n += 1
    logger.error(
        message=f"File {filepath} does not contain a line with content for 1000 lines",
        error_type=ValueError,
    )


def replace_file_ending(path: StrPath, new_ending: str) -> str:
    """
    Replace the ending of a file by matchin the last ".".

    :param path: Path to file
    :type path: StrPath
    :param new_ending: _description_
    :type new_ending: new_ending
    :return: File path with new ending
    :rtype: str
    """
    new_ending = new_ending[1:] if new_ending.startswith(".") else new_ending
    return ".".join(path.split(".")[:-1] + [new_ending])


# Command methods
def execute_verbose_command(
    cmd: str | list,
    verbosity: int = 1,
    log_path: StrPath = None,
    decode_text: bool = True,
    **kwargs,
) -> tuple[str, str]:
    """
    Execute a command with the adequate verbosity.

    :param cmd: Command as a string or list
    :type cmd: str|list
    :param verbosity: Verbosity level, defaults to 1
    :type verbosity: int, optional
    :param log_path: Path to logfile, defaults to None
    :type log_path: StrPath
    :param decode_text: Whether to decode the text, defaults to True
    :type decode_text: bool
    :return: Stdout, Stderr
    :rtype: tuple[str,str]
    """
    logger.log(f"Starting command: {cmd}", minimum_verbosity=3, verbosity=verbosity)
    process = tee_subprocess.run(
        cmd,
        shell=True,
        stdout=None if verbosity >= 4 else subprocess.DEVNULL,
        stderr=None if verbosity >= 3 else subprocess.DEVNULL,
        text=decode_text,
        capture_output=True,
    )

    if log_path:
        with open(log_path, "w") as out_file:
            out_file.write(f"out:\n{process.stdout}\n\n\nerr:\n{process.stderr}")
    return None, process.stdout, process.stderr


# Parallel processing
def compute_scheduled(
    futures: list, num_workers: int = 1, scheduler="threads", verbose: bool = False
):
    """
    Compute scheduled operations in parallel.

    :param futures: Scheduled computations
    :type futures: list
    :param num_workers: Number of parallel processes, defaults to 1
    :type num_workers: int, optional
    :param scheduler: Scheduler ('threads', 'processes', 'synchronous'), defaults to "threads"
    :type scheduler: str, optional
    :param verbose: Print the output ?, defaults to False
    :type verbose: bool, optional
    :return: Returns of function
    :rtype: any
    """
    with dask.config.set(scheduler=scheduler, num_workers=num_workers):
        if verbose:
            with TqdmCallback(desc="Compute"):
                results = dask.compute(futures)
        else:
            results = dask.compute(futures)

    return results


# Webrequests
def check_for_str_request(
    url: str | bytes,
    query_success: str,
    query_failed: str = None,
    query_running: str = None,
    retries: int = 90,
    allowed_fails: int = 5,
    retry_time: float = 20.0,
    verbosity: int = 1,
    **kwargs,
) -> bool:
    """
    Check the given URL for a given query. The task is retried a number of times with logarithmically (log2) decreasing time between requests after one initial request.

    :param url: Target URL
    :type url: str | bytes
    :param query_success: Query string that is searched in response to indicate successful completion
    :type query_success: str
    :param query_failed: Query string that is searched in response to indicate failure
    :type query_failed: str
    :param query_running: Query string that is searched in response to indicate ongoing process
    :type query_running: str
    :param retries: Number of retries, defaults to 100
    :type retries: int, optional
    :param allowed_fails: Number of times the request are allowed to fail, defaults to 10
    :type allowed_fails: int, optional
    :param retry_time: Time till retry, defaults to 20.0
    :type retry_time: float, optional
    :param verbosity: Level of verbosity, defaults to 1
    :type verbosity: int, optional
    :param kwargs: Additional arguments, passed on to requests.get()
    :type kwargs: any, optional
    :return: Query found ?
    :rtype: bool
    """
    fails = []
    for i in range(retries):
        response = requests.get(url, **kwargs)

        if response.status_code == 200:
            if query_success in str(response.content):
                logger.log(
                    message=f"Request succeeded ({query_success} in response).",
                    minimum_verbosity=3,
                    verbosity=verbosity,
                )
                return True

            elif query_failed and query_failed in str(response.content):
                logger.log(
                    message=f"Request failed ({query_failed} in response).",
                    minimum_verbosity=3,
                    verbosity=verbosity,
                )
                return False
            elif query_running and query_running in str(response.content):
                logger.log(
                    message=f"Request still running ({query_running} in response).",
                    minimum_verbosity=3,
                    verbosity=verbosity,
                )
        else:
            fails.append(response.status_code)
            logger.warn(
                f"{url} returned status code {response.status_code} after {i} retries.\
                    Requesting this URL will be terminated after further {allowed_fails - len(fails)} failed requests.",
                category=UserWarning,
            )

        # Check Failure
        if len(fails) > allowed_fails:
            raise LookupError(
                f"The request to {url} failed more than {allowed_fails} times with the following status codes:\n{fails}"
            )

        # Retry
        logger.log(
            message=f"{query_success} not found at {url}. Retrying in {retry_time}s.",
            minimum_verbosity=2,
            verbosity=verbosity,
        )
        time.sleep(retry_time)

    return False


# Class handling
def get_attribute_recursive(object, attribute: str, *args) -> any:
    """
    Recursive retrival of nested attributes.

    :param object: Class/Object with attributes
    :type object: any
    :param attribute: Attributes, chained as "attr1.attr2.deep_attr"
    :type attribute: str
    :return: Retrieved object
    :rtype: any
    """

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [object] + attribute.split("."))


def set_attribute_recursive(object, attribute: str, value, refresh: bool = False) -> None:
    """
    Recursive setting of nested attributes.

    :param object: Class/Object with attributes
    :type object: any
    :param attribute: Attribute as a string
    :type attribute: any
    :param value: Value to set to attribute
    :type value: any
    :param refresh: Refresh object
    :type refresh: bool
    :return: None
    :rtype: None
    """
    pre, _, post = attribute.rpartition(".")
    setattr(get_attribute_recursive(object, pre) if pre else object, post, value)
    if refresh:
        object.refresh(attribute)
        object.refresh(pre)
    return object
