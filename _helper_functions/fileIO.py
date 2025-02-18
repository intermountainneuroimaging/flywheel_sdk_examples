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

fw = flywheel.Client('')
log = logging.getLogger(__name__)


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
    
    
os.environ["FLYWHEEL_SDK_REQUEST_TIMEOUT"]="6000"

def upload_file_to_container(conatiner, fp, overwrite=False, update=True, replace_info=[], **kwargs):
    """Upload file to FW container and update info if `update=True`
    
    Args:
        container (flywheel.Project): A Flywheel Container (e.g. project, analysis, acquisition)
        fp (Path-like): Path to file to upload
        update (bool): If true, update container with key/value passed as kwargs.        
        kwargs (dict): Any key/value properties of Acquisition you would like to update.        
    """
    basename = os.path.basename(fp)
    if not os.path.isfile(fp):
        raise ValueError(f'{fp} is not file.')
        
    if conatiner.get_file(basename) and not overwrite:
        log.info(f'File {basename} already exists in container. Skipping.')
        return
    
    if conatiner.get_file(basename) and overwrite:
        log.info(f'File {basename} already exists, overwriting.')
        fw.delete_container_file(conatiner.id,basename)
        time.sleep(10)
        
    log.info(f'Uploading {fp} to container {conatiner.id}')
    conatiner.upload_file(fp)
    while not conatiner.get_file(basename):   # to make sure the file is available before performing an update
        conatiner = conatiner.reload()
        time.sleep(1)
    
    f = conatiner.get_file(basename)
    
    if replace_info:
        f.replace_info(replace_info)
        log.info(f'Replacing info {info.keys()} to acquisition {acquistion.id}')
        
    if update and kwargs:
        f.update(**kwargs)


def download_session_analyses_byid(analysis_id, download_path):
    # loop through all sessions in the project. More detailed filters could be 
    #   used to specify a subset of sessions
        
    analysis = fw.get_container(analysis_id)

    full_session = fw.get_container(analysis["parents"]["session"])

    if analysis:
        for fl in analysis.files:
            if '.zip' in fl['name']:
                download_and_unzip_inputs(analysis, fl, download_path)
            else:
                os.makedirs(os.path.join(download_path,'files'), exist_ok=True)
                fl.download(os.path.join(download_path,'files',fl['name']))

        log.info('Downloaded analysis: %s for Subject: %s Session: %s', analysis.label,full_session.subject.label, full_session.label)      
    else:
        log.info('Analysis not found: for Subject: %s Session: %s', full_session.subject.label, full_session.label)  


        
def download_and_unzip_inputs(parent_obj, file_obj, path):
    """
    unzip_inputs unzips the contents of zipped gear output into the working
    directory.
    Args:
        zip_filename (string): The file to be unzipped
    """
    rc = 0
    outpath = []
    
    os.makedirs(path, exist_ok=True)
    
    # start by checking if zipped file
    if ".zip" not in file_obj.name:
        return
    
    # next check if the zip file is organized with analysis id as top dir
    zip_info = parent_obj.get_file_zip_info(file_obj.name)
    zip_top_dir = zip_info.members[0].path.split('/')[0]
    if len(zip_top_dir)==24:
        # this is an archive zip and needs to be handled special
        with tempfile.TemporaryDirectory(dir=path) as tempdir:
            zipfile = os.path.join(tempdir,file_obj.name)

            # download zip
            file_obj.download(zipfile)

            # use linux "unzip" methods in shell in case symbolic links exist
            log.info("Unzipping file, %s", os.path.basename(zipfile))
            cmd = ["unzip","-qq","-o",zipfile,"-d",tempdir]
            result = sp.run(cmd, check=True, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
            log.info("Done unzipping.")

            try:
                # use subprocess shell command here since there is a wildcard
                cmd = "mv "+os.path.join(tempdir,zip_top_dir,"*")+" "+path
                result = sp.run(cmd, shell=True, check=True, stdout=sp.PIPE, stderr=sp.PIPE)
            except sp.CalledProcessError as e:
                cmd = "cp -R "+os.path.join(tempdir,zip_top_dir,"*")+" "+path
                result = sp.run(cmd, shell=True, check=True, stdout=sp.PIPE, stderr=sp.PIPE)
            finally:
                cmd = ['rm','-Rf',os.path.join(tempdir,zip_top_dir)]
                run_command_with_retry(cmd, delay=5)
    else:
        path = os.path.join(path,"files")
        os.makedirs(path, exist_ok=True)
        zipfile = os.path.join(path,file_obj.name)
        # download zip
        file_obj.download(zipfile)
        # use linux "unzip" methods in shell in case symbolic links exist
        log.info("Unzipping file, %s", os.path.basename(zipfile))
        cmd = ["unzip","-qq","-o",zipfile,"-d",path]
        result = sp.run(cmd, check=True, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
        log.info("Done unzipping.")
        os.remove(zipfile)
        

def run_command_with_retry(cmd, retries=3, delay=1, cwd=os.getcwd()):
    """Runs a command with retries and delay on failure."""

    for attempt in range(retries):
        try:
            result = sp.run(cmd, check=True, stdout=sp.PIPE, stderr=sp.PIPE, text=True, cwd=cwd)
            return result
        except sp.CalledProcessError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise  # Re-raise the exception if all retries fail
        
        
