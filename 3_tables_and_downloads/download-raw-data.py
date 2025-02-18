from pathlib import Path
import sys, os
import flywheel
import pandas as pd
import re

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')


def download_bids(project, path):
    for ses in project.sessions.find():
        full_session=fw.get_session(ses.id)  # this is necessary to pull the full object 

        for acq in full_session.acquisitions():
            full_acq = fw.get_acquisition(acq.id)   # this is necessary to pull the full object 
            if "BIDS" not in full_acq.info.keys() or full_acq.info["BIDS"]["ignore"]:
                continue
            for fl in full_acq.files:
                if "BIDS" in fl.info.keys():
                    if fl.info["BIDS"]["ignore"]:
                        continue
                    bidspath = os.path.join(path,fl.info["BIDS"]["Path"],fl.info["BIDS"]["Filename"])
                    os.makedirs(os.path.dirname(bidspath),exist_ok = True)
                    fl.download(bidspath)
                    log.info("Downloaded: %s", bidspath)
    return


def download_file_by_pattern(project, path, pattern):
    
    pattern_compiled = re.compile(pattern)
    
    for ses in project.sessions.find():
        full_session=fw.get_session(ses.id)  # this is necessary to pull the full object 

        for acq in full_session.acquisitions():
            full_acq = fw.get_acquisition(acq.id)   # this is necessary to pull the full object 

            for fl in full_acq.files:
                if bool(re.search(pattern_compiled, fl.name)):
                    downloadpath=os.path.join(path, "sub-"+full_session.subject.label,"ses-"+full_session.label,"files")
                    os.makedirs(downloadpath,exist_ok=True)
                    fl.download(os.path.join(downloadpath,fl["name"]))
                    log.info("Downloaded: %s", os.path.join(downloadpath,fl["name"]))
    
    return
    
    
                
if __name__ == "__main__":
    #Setup the flywheel client
    fw = flywheel.Client('')
    fw.get_config().site.api_url

    PROJECT_PATH = "<group/project>"   ## e.g.  project_path = "mbanich/ABCDQA"
    
    # download project data for local analyses
    project = fw.get(fw.lookup(PROJECT_PATH).id)
    
    # path to download directory
    path='<path-to-downloads>'
    
    # download bids files
    download_bids(project, path)
    
    # download file by pattern
    pattern="recording"
    download_file_by_pattern(project, path, pattern)
