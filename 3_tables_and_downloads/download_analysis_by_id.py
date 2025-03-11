#!/usr/bin/env python
# coding: utf-8

# Download Analyses from Flywheel

from pathlib import Path
import os
import flywheel
import pandas as pd
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')

try:
    absolute_path = os.path.abspath(__file__)
    sys.path.insert(0, Path(absolute_path).parts[0:-2])
except NameError:
    sys.path.insert(0, os.path.dirname(os.getcwd()))

from _helper_functions import tables, fileIO

# set default permissions
os.umask(0o002);

download_path = "<download-path>"

# get flywheel client
fw = flywheel.Client('')

# download directly from list of analysis ids
analysis_ids = [
    'analysis-id-1',
    'analysis-id-2',
]

# make sure download path exists (make if needed)
os.makedirs(download_path, exist_ok=True)

# download analysis files
for aid in analysis_ids:
    fileIO.download_session_analyses_byid(aid,download_path)
