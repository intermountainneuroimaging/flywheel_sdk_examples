from pathlib import Path
import subprocess as sp
import sys, os, logging
import flywheel
from datetime import datetime, date
import glob
import pandas as pd
from time import sleep
import time
import re
import tempfile
from zipfile import ZipFile
import json

fw = flywheel.Client('')
log = logging.getLogger(__name__)


def run_gear(gear, config, inputs, tags, dest, analysis_label=[]):
    """Submits a job with specified gear and inputs.
    
    Args:
        gear (flywheel.Gear): A Flywheel Gear.
        config (dict): Configuration dictionary for the gear.
        inputs (dict): Input dictionary for the gear.
        tags (list): List of tags for gear
        dest (flywheel.container): A Flywheel Container where the output will be stored.
        analysis_label (str): label for gear.
        
    Returns:
        str: The id of the submitted job (for utility gear) or analysis container (for analysis gear).
        
    """
    try:
        # Run the gear on the inputs provided, stored output in dest constainer and returns job ID
        if not analysis_label:
            label = gear['gear']['name']+datetime.now().strftime(" %x %X")
        else:
            label = analysis_label
        gear_job_id = gear.run(analysis_label=label, config=config, inputs=inputs, tags=tags, destination=dest)
        log.debug('Submitted job %s', gear_job_id)
        
        return gear_job_id
    except flywheel.rest.ApiException:
        log.exception('An exception was raised when attempting to submit a job for %s',
                      gear_job_id.name)
        
        

def holdjob(jobids, timeout, period=0.25):
    mustend = time.time() + timeout
    while time.time() < mustend:
        if isinstance(jobids, str):
            jobid =  [jobids]
        
        for jid in jobids:
            anlys = fw.get_job(jid)
            
            if any(anlys.state.lower() == s for s in ['complete','cancelled','failed']): 
                log.info('Job %s: completed with status: %s', anlys.id, anlys.state) 
                jobids.remove(jid)
        
        if isempty(jobids):
            return True
    
        time.sleep(period)
        log.info('Job %s: timeout after %s seconds... continuing run script', jobid.id, timeout)
        
    return False


def hasacquisition(session,acq_name):
    for acq in session.acquisitions.find():
        if acq_name in acq.label:
            return True
    
    return False


def searchfiles(path, dryrun=False, find_first=False):
    cmd = "ls -d " + path

    log.debug("\n %s", cmd)

    if not dryrun:
        terminal = sp.Popen(
            cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True
        )
        stdout, stderr = terminal.communicate()
        log.debug("\n %s", stdout)
        log.debug("\n %s", stderr)

        files = stdout.strip("\n").split("\n")

        if find_first:
            files = files[0]

        return files


def replace_line(filename, pattern, repl):
    """
        Perform the pure-Python equivalent of in-place `sed` substitution: e.g.,
        `sed -i -e 's/'${pattern}'/'${repl}' "${filename}"`.
        """
    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)

    # For portability, NamedTemporaryFile() defaults to mode "w+b" (i.e., binary
    # writing with updating). This is usually a good thing. In this case,
    # however, binary writing imposes non-trivial encoding constraints trivially
    # resolved by switching to text writing. Let's do that.
    with tempfile.NamedTemporaryFile(dir=os.getcwd(), mode='w', delete=False) as tmp_file:
        with open(filename) as src_file:
            for line in src_file:
                if re.findall(pattern_compiled, line):
                    tmp_file.write(repl)
                else:
                    tmp_file.write(line)

    # Overwrite the original file with the munged temporary file in a
    # manner preserving file attributes (e.g., permissions).
    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)



def locate_by_pattern(filename, pattern):
    """
    Locates all instances that meet pattern and returns value from file.
    Args:
        filename: text file
        pattern: regex

    Returns:

    """
    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)
    arr = []
    with open(filename) as src_file:
        for line in src_file:
            num = re.findall(pattern_compiled, line)
            if num:
                arr.append(num[0])

    return arr


def create_file(filename):
    try:
        f = open(filename, "x")
        f.close()
        print("File created successfully.")
    except FileExistsError:
        print("File already exists.")

