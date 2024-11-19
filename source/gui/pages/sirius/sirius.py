#!/usr/bin/env python3

import taipy.gui.builder as tgb

from source.annotation.sirius_pipe import Sirius_Runner

sirius_params = Sirius_Runner()

with tgb.Page() as sirius:
    tgb.part()