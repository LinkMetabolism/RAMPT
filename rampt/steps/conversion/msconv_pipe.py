#!/usr/bin/env python

"""
Conversion of manufacturer MS files to .mzML or .mzXMLtarget_format. The folder structure is mimiced at the place of the output.
"""

import os
import argparse
import regex

from os.path import join

from ..general import *


def main(args: argparse.Namespace | dict, unknown_args: list[str] = []):
    """
    Execute the conversion.

    :param args: Command line arguments
    :type args: argparse.Namespace|dict
    :param unknown_args: Command line arguments that are not known.
    :type unknown_args: list[str]
    """
    # Extract arguments
    in_dir = get_value(args, "in_dir")
    out_dir = get_value(args, "out_dir")
    target_format = get_value(args, "target_format", "mzML")
    pattern = get_value(args, "pattern", r"")
    suffix = get_value(args, "suffix", None)
    prefix = get_value(args, "prefix", None)
    contains = get_value(args, "contains", None)
    redo_threshold = get_value(args, "redo_threshold", 1e8)
    overwrite = get_value(args, "overwrite", False)
    nested = get_value(args, "nested", False)
    n_workers = get_value(args, "workers", 1)
    save_log = get_value(args, "save_log", False)
    verbosity = get_value(args, "verbosity", 1)
    additional_args = get_value(args, "msconv_arguments")
    additional_args = additional_args if additional_args else unknown_args

    # Conversion
    msconvert_runner = MSconvert_Runner(
        target_format=target_format,
        pattern=pattern,
        suffix=suffix,
        prefix=prefix,
        contains=contains,
        redo_threshold=redo_threshold,
        overwrite=overwrite,
        save_log=save_log,
        additional_args=additional_args,
        verbosity=verbosity,
        nested=nested,
        workers=n_workers,
    )
    msconvert_runner.scheduled_ios = {
        "in_path": {"standard": in_dir},
        "out_path": {"standard": out_dir},
    }
    return msconvert_runner.run()


class MSconvert_Runner(Pipe_Step):
    """
    General class for file conversion along matched patterns.
    """

    def __init__(
        self,
        exec_path: StrPath = "msconvert",
        target_format: str = "mzML",
        redo_threshold: float = 1e8,
        overwrite: bool = False,
        save_log=False,
        additional_args: list = [],
        verbosity=1,
        **kwargs,
    ):
        """
        Initializes the file converter.

        :param exec_path: Path of executive
        :type exec_path: StrPath
        :param target_format: _description_, defaults to "mzML"
        :type target_format: str, optional
        :param redo_threshold: Threshold in bytess for a target file to be considered as incomplete and scheduled for re running the conversion, defaults to 1e8
        :type redo_threshold: float, optional
        :param overwrite: Overwrite all, do not check whether file already exists, defaults to False
        :type overwrite: bool, optional
        :param save_log: Whether to save the output(s).
        :type save_log: bool, optional
        :param additional_args: Additional arguments for mzmine, defaults to []
        :type additional_args: list, optional
        :param verbosity: Level of verbosity, defaults to 1
        :type verbosity: int, optional
        """
        self.valid_formats = [
            "raw",
            "d",
            "lcd",
            "t2d",
            "baf",
            "fid",
            "tdf",
            "tsf",
            "wiff",
            "wiff2",
            "yep",
            "mzML",
            "mzXML",
            "imzML",
        ]
        self.valid_folder_formats = ["raw", "d"]
        super().__init__(
            mandatory_patterns={
                "in": rf".*\.({r'|'.join(self.valid_formats)})$",
                "in_folder": rf".*\.({r'|'.join(self.valid_folder_formats)})$",
            },
            exec_path=exec_path,
            save_log=save_log,
            overwrite=overwrite,
            additional_args=additional_args,
            verbosity=verbosity,
        )
        if kwargs:
            self.update(kwargs)
        self.redo_threshold = redo_threshold
        self.target_format = target_format if target_format.startswith(".") else f".{target_format}"
        self.target_format = change_case_str(
            s=self.target_format, range=slice(3, len(self.target_format)), conversion="upper"
        )
        self.name = "msconvert"

    def select_for_conversion(self, in_path: StrPath, out_path: StrPath) -> bool:
        """
        Convert one file with msconvert.

        :param in_path: Path to scheduled file.
        :type in_path: StrPath
        :param out_path: Path to output directory.
        :type out_path: StrPath
        :return: Whether the file was converted
        :rtype: bool
        """
        # Check origin
        in_valid = super().match_path(pattern=self.patterns["in"], path=in_path)
        # Check target
        out_valid = (
            self.overwrite
            or (not os.path.isfile(out_path))
            or os.path.getsize(out_path) < float(self.redo_threshold)
            or not regex.search("^</.*>$", open_last_line_with_content(filepath=out_path))
        )

        return in_valid, out_valid

    # Distribution
    def distribute_scheduled(self, **scheduled_io):
        return super().distribute_scheduled(**scheduled_io)

    def run_single(self, in_path: dict[str, StrPath], out_path: dict[str, StrPath], **kwargs):
        """
        Convert one file with msconvert.

        :param in_path: Path to scheduled file.
        :type in_path: dict[str, StrPath]
        :param out_path: Path to output directory.
        :type out_path: dict[str, StrPath]
        """
        in_path, out_path = self.extract_standard(in_path=in_path, out_path=out_path)
        additional_args = self.link_additional_args(**kwargs)

        out_file_name = ".".join(os.path.basename(in_path).split(".")[:-1]) + self.target_format

        cmd = (
            rf'"{self.exec_path}" --{self.target_format[1:]} -e {self.target_format} --64 '
            + rf'-o "{out_path}" --outfile "{out_file_name}" "{in_path}" {additional_args}'
        )

        if not os.path.isfile(out_path):
            out_path = os.path.join(out_path, out_file_name)

        self.compute(
            step_function=execute_verbose_command,
            cmd=cmd,
            in_out=dict(
                in_path=in_path, out_path=out_path
            ),
            log_path=self.get_log_path(out_path=out_path),
            verbosity=self.verbosity,
        )

    def run_directory(self, in_path: dict[str, StrPath], out_path: dict[str, StrPath], **kwargs):
        """
        Convert all matching files in a folder.

        :param in_path: Path to scheduled file.
        :type in_path: dict[str, StrPath]
        :param out_path: Path to output directory.
        :type out_path: dict[str, StrPath]
        """
        in_path, out_path = self.extract_standard(in_path=in_path, out_path=out_path)
        
        # Check folder with valid input:
        if self.match_path(in_path, self.patterns["in_folder"]):
            self.run_single(in_path=in_path, out_path=out_path, **kwargs)
        else:
            for entry in os.listdir(in_path):
                entry_path = join(in_path, entry)
                hypothetical_out_path = join(
                    out_path, replace_file_ending(entry, self.target_format)
                )
                in_valid, out_valid = self.select_for_conversion(
                    in_path=entry_path, out_path=hypothetical_out_path
                )

                if in_valid and out_valid:
                    os.makedirs(out_path, exist_ok=True)
                    self.run_single(in_path=entry_path, out_path=out_path, **kwargs)

    def run_nested(
        self,
        in_path: dict[str, StrPath],
        out_path: dict[str, StrPath],
        recusion_level: int = 0,
        **kwargs,
    ):
        """
        Converts multiple files in multiple folders, found in in_path with msconvert and saves them
        to a location out_path again into their respective folders.

        :param in_path: Starting folder for descent.
        :type in_path: dict[str, StrPath]
        :param out_path: Folder where structure is mimiced and files are converted to
        :type out_path: dict[str, StrPath]
        :param recusion_level: Current level of recursion, important for determination of level of verbose output, defaults to 0
        :type recusion_level: int, optional
        """
        in_path, out_path = self.extract_standard(in_path=in_path, out_path=out_path)
        has_in_file = False

        root, dirs, files = next(os.walk(in_path))
        
        for i, file in enumerate(files):
            if self.match_path(pattern=self.patterns["in"], path=file):
                self.run_directory(in_path=in_path, out_path=out_path, **kwargs)
                has_in_file = True
                break

        for dir in dirs:
            if self.match_path(pattern=self.patterns["in_folder"], path=file):
                if not has_in_file:
                    self.run_directory(in_path=in_path, out_path=out_path, **kwargs)
                    has_in_file = True
            else:
                self.run_nested(
                    in_path=join(in_path, dir),
                    out_path=join(out_path, dir),
                    recusion_level=recusion_level + 1,
                    **kwargs,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="msconv_pipe.py",
        description="Conversion of manufacturer MS files to .mzML or .mzXML target_format.\
                                             The folder structure is mimiced at the place of the output.",
    )
    parser.add_argument("-in", "--in_dir", required=True)
    parser.add_argument("-out", "--out_dir", required=True)
    parser.add_argument("-tf", "--target_format", required=False)
    parser.add_argument("-pat", "--pattern", required=False)
    parser.add_argument("-suf", "--suffix", required=False)
    parser.add_argument("-pre", "--prefix", required=False)
    parser.add_argument("-con", "--contains", required=False)
    parser.add_argument("-rt", "--redo_threshold", required=False)
    parser.add_argument("-o", "--overwrite", required=False, action="store_true")
    parser.add_argument("-n", "--nested", required=False, action="store_true")
    parser.add_argument("-w", "--workers", required=False, type=int)
    parser.add_argument("-s", "--save_log", required=False, action="store_true")
    parser.add_argument("-v", "--verbosity", required=False, type=int)
    parser.add_argument("-msconv", "--msconv_arguments", required=False, nargs=argparse.REMAINDER)

    args, unknown_args = parser.parse_known_args()
    main(args=args, unknown_args=unknown_args)
