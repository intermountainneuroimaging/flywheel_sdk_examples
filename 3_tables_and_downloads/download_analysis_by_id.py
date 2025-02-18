#!/usr/bin/env python
# coding: utf-8

# # Download Analyses from Flywheel
# 

from pathlib import Path
import os
import flywheel
import pandas as pd
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')

# import custom helper functions, need to first add path to system envrionment... 
#      do that using current directory inside jupyter notebooks, 
#      or __file__ attribute in script
try:
    sys.path.insert(0, os.path.dirname(__file__))
except NameError:
    sys.path.insert(0, os.path.dirname(os.getcwd()))
from _helper_functions import tables, fileIO


# set default permissions
os.umask(0o002);

user_inputs = {  
    "download-path": "/scratch/alpine/amhe4269/cancat/analysis"
}

# set default permissions
os.umask(0o002);

# get flywheel client
fw = flywheel.Client('')

# option 2: download directly from list of analysis ids
analysis_ids = [
    '67a5649d64ab7de9b6443528',
    '67a6599c2c68e61dc120a354'
]
os.makedirs(user_inputs["download-path"], exist_ok=True)
for aid in analysis_ids:
    download_session_analyses_byid(aid,user_inputs["download-path"])

        



