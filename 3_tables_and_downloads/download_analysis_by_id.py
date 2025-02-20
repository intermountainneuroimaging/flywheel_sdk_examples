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
absolute_path = os.path.abspath(__file__)
try:
    sys.path.insert(0, Path(absolute_path).parts[0:-2])
except NameError:
    sys.path.insert(0, os.path.dirname(os.getcwd()))

from _helper_functions import tables, fileIO


# set default permissions
os.umask(0o002);

user_inputs = {  
    "download-path": "/pl/active/banich/studies/mindmem/"
}

# set default permissions
os.umask(0o002);

# get flywheel client
fw = flywheel.Client('')

# option 2: download directly from list of analysis ids
analysis_ids = [
    'analysis-id-1',
    'analysis-id-2',
]
os.makedirs(user_inputs["download-path"], exist_ok=True)
for aid in analysis_ids:
    fileIO.download_session_analyses_byid(aid,user_inputs["download-path"])
