#!/usr/bin/env python
"""
Testing the ion exclusion list creation.
"""

from tests.common import *
from rampt.steps.ion_exclusion.ion_exclusion import *
from rampt.steps.ion_exclusion.ion_exclusion import main as ion_exclusion_pipe_main
import pandas as pd

platform = get_platform()
filepath = get_internal_filepath(__file__)
out_path, mock_path, example_path, batch_path, installs_path = contruct_common_paths(filepath)
make_out(out_path)


def test_ion_exclusion_pipe_main():
    args = argparse.Namespace(
        in_dir=example_path,
        out_dir=out_path,
        data_dir=example_path,
        relative_tolerance=1e-05,
        absolute_tolerance=1e-08,
        nested=True,
        workers=1,
        save_log=False,
        verbosity=0,
        ion_exclusion_args=None,
    )

    ion_exclusion_pipe_main(args, unknown_args=[])

    assert os.path.isfile(join(out_path, "example_files_ms2_presence.tsv"))
    df = pd.read_csv(join(out_path, "example_files_ms2_presence.tsv"), sep="\t")

    assert df.loc[0]["rt"] == 0.25856668

    assert os.path.isfile(join(out_path, "example_nested/example_nested_ms2_presence.tsv"))


def test_clean():
    clean_out(out_path)
