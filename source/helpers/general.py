#!/usr/bin/env python
"""
Methods that are helpful for general processing.
"""
import sys
import os
import subprocess
import time
import math
import warnings
import regex
import requests
import dask
from tqdm.dask import TqdmCallback
import chardet
import tee_subprocess

from source.helpers.types import *




# File opeations
def get_internal_filepath(file:str) -> StrPath:
    """
    Return the filepath of a passed file.

    :param file: file
    :type file: str
    :return: path of file on system
    :rtype: StrPath
    """
    return os.path.abspath(file)


def construct_path(*args:list[StrPath]) -> StrPath:
    """
    Construct a path from the given list of paths

    :return: Combine path
    :rtype: StrPath
    """
    return os.path.abspath(os.path.join(*args))


def make_new_dir(dir:StrPath) -> bool:
    """
    Make a directory, if one does not already exist in its place.

    :param dir: path to directory
    :type dir: StrPath
    :return: whether a new directory has been
    :rtype: bool
    """
    if not os.path.isdir( dir ):
        os.mkdir( dir )
        return True
    return False



# String operations
def change_case_str(s:str, range:SupportsIndex, conversion:str) -> str:
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
            raise(ValueError(f"conversion {conversion} is invalid. Choose upper/lower as a valid conversion."))

    str_list[range] =  selection

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
    def __init__( self, nesting_depth:int = 1, nested_paths:list=[], id_name:str="id", dir_name:str="label", sub_name:str="children" ):
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
        self.nesting_depth  = nesting_depth
        self.nested_paths   = nested_paths
        self.dir_name       = dir_name
        self.sub_name       = sub_name
        self.id_name        = id_name
        self.id_counter     = 0

    def add_nested_lists( self, split_steps, nested_paths, complete_path ):
        self.id_counter += 1
        step = split_steps[0]

        if len(split_steps) == self.nesting_depth:  # Break recursion at desired depth
            if isinstance(nested_paths, list):
                entry_present = [True for nested_path in nested_paths if nested_path.get(self.dir_name) == complete_path]
                if not entry_present:
                    nested_paths.append( { self.id_name: self.id_counter,
                                            self.dir_name: complete_path,
                                            self.sub_name: [] } )
            else:
                nested_paths = [{ self.id_name: self.id_counter,
                                  self.dir_name: step,
                                  self.sub_name: [complete_path]}]
            return nested_paths
        
        split_found = False
        for nested_path in nested_paths :
            if isinstance(nested_path, dict) and step == nested_path.get(self.dir_name):
                nested_path[self.sub_name] = self.add_nested_lists( split_steps[1:],
                                                                    nested_path.get(self.sub_name),
                                                                    complete_path )
                split_found = True

        if not split_found:
            nested_paths.append( { self.id_name: self.id_counter,
                                   self.dir_name: step,
                                   self.sub_name: self.add_nested_lists( split_steps[1:],
                                                                         [],
                                                                         complete_path ) } )

        return nested_paths
        

    def update_nested_paths( self, new_paths:str|list[str] ):
        if isinstance(new_paths, str):
            new_paths = [ new_paths ]
        for new_path in new_paths:
            in_path = os.path.normpath( new_path )
            split_path = in_path.split( os.sep )
            self.nested_paths = self.add_nested_lists( split_path[1:],
                                                       self.nested_paths,
                                                       in_path)
        return self.nested_paths


    def prune_lca( self, nested_paths:list=None ):
        nested_paths = nested_paths if nested_paths is not None else self.nested_paths
        if len(nested_paths) == 1 and len(nested_paths[0][self.sub_name]) == 1:
            return self.prune_lca( nested_paths=nested_paths[0][self.sub_name] )
        else:
            return nested_paths
                
        



# File operations
def open_last_n_line(filepath:str, n:int=1) -> str:
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
    with open(filepath, 'rb') as f:
        # catch OSError in case of a one line file
        f.seek(-2, os.SEEK_END)
        while num_newlines < n :
            f.seek(-2, os.SEEK_CUR)
            if f.read(1) == b'\n':
                num_newlines += 1
        return f.readline().decode()

def open_last_line_with_content(filepath:str) -> str:
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
        except OSError:
            raise(ValueError(f"File {filepath} does not contain a line with content"))
        if regex.search(r".*\S.*", line):
            return line
        n += 1
    raise(ValueError(f"File {filepath} does not contain a line with content for 1000 lines"))


def replace_file_ending( path:StrPath, new_ending:str ) -> str:
    """
    Replace the ending of a file by matchin the last ".".

    :param path: Path to file
    :type path: StrPath
    :param new_ending: _description_
    :type new_ending: new_ending
    :return: File path with new ending
    :rtype: str
    """
    return regex.sub(r"(.*\.).*", rf"\1{new_ending}", path)



# Command methods
def execute_verbose_command( cmd:str|list, verbosity:int=1,
                             out_path:StrPath=None, decode_text:StrPath=True ) -> bool:
    """
    Execute a command with the adequate verbosity.

    :param cmd: Command as a string
    :type cmd: str
    :param verbosity: Verbosity level, defaults to 1
    :type verbosity: int, optional
    :param out_path: Path to outfile.
    :type out_path: StrPath
    :return: Success of execution
    :rtype: bool
    """
    process = tee_subprocess.run( cmd, 
                                  shell=True, 
                                  stdout=None if verbosity >= 3 else subprocess.DEVNULL,
                                  stderr=None if verbosity >= 2 else subprocess.DEVNULL,
                                  text=decode_text,
                                  capture_output=True )
    
    if out_path:
        with open(out_path, "w") as out_file:
            out_file.write(f"out:\n{process.stdout}\n\n\nerr:\n{process.stderr}")

    return process.stdout, process.stderr



# Parallel processing
def compute_scheduled( futures:list, num_workers:int=1, verbose:bool=False ) -> bool:
        dask.config.set(scheduler='processes', num_workers=num_workers)
        if verbose:
            with TqdmCallback(desc="Compute"):
                dask.compute(futures)
        else:
            dask.compute(futures)
        
        return True



# Webrequests
def check_for_str_request(url:str | bytes, query:str, retries:int=100, allowed_fails:int=10, expected_wait_time:float=600.0, verbosity:int=1, **kwargs) -> bool:
    """
    Check the given URL for a given query. The task is retried a number of times with logarithmically (log2) decreasing time between requests after one initial request.

    :param url: Target URL
    :type url: str | bytes
    :param query: Query string that is searched in response
    :type query: str
    :param retries: Number of retries, defaults to 100
    :type retries: int, optional
    :param allowed_fails: Number of times the request are allowed to fail, defaults to 10
    :type allowed_fails: int, optional
    :param expected_wait_time: Expected time until query is found, defaults to 10.0
    :type expected_wait_time: float, optional
    :param verbosity: Level of verbosity, defaults to 1
    :type verbosity: int, optional
    :param kwargs: Additional arguments, passed on to requests.get()
    :type kwargs: any, optional
    :return: Query found ?
    :rtype: bool
    """
    fails = []
    for i in range(retries):
        response = requests.get(url,  **kwargs)

        if response.status_code == 200:
            if query in  str(response.content):
                return True
        else:
            fails.append(response.status_code)
            if verbosity >= 1:
                warnings.warn( f"{url} returned status code {response.status_code} after {i} retries.\
                            Requesting this URL will be terminated after further {allowed_fails - len(fails)} failed requests.",
                            category=UserWarning )
        if len(fails) > allowed_fails:
            raise LookupError(f"The request to {url} failed more than {allowed_fails} times with the following status codes:\n{fails}")
        
        # Retry
        retry_time = ( 1 / math.log2(i + 2) ) * expected_wait_time
        if verbosity >= 2:
            print(f"{query} not found at {url}. Retrying in {retry_time}s.")
        time.sleep(retry_time)

    return False