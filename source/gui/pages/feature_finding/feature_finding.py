#!/usr/bin/env python3

import taipy.gui.builder as tgb

from source.feature_finding.mzmine_pipe import MZmine_Runner

feature_finding_params = MZmine_Runner()

with tgb.Page() as feature_finding:
    tgb.part()