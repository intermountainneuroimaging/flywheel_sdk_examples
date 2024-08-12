from pathlib import Path
import sys, os
import flywheel
import glob
import pandas as pd
from zipfile import ZipFile
import tempfile
import argparse
from functools import partial
import re

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')

__version__ = "0.0.1"

# get flywheel client
fw = flywheel.Client('')
            
            
def download_analysis_byid(analysis_id,path):
    # loop through all sessions in the project. More detailed filters could be 
    #   used to specify a subset of sessions

    analysis = fw.get_container(analysis_id)

    full_session = fw.get_container(analysis["parents"]["session"])

    if analysis:

        # make temp directory for downloads...
        with tempfile.TemporaryDirectory(dir=path) as tmpdirname:
            
            # download analysis files
#             for fl in analysis.files:
#                 fl.download(os.path.join(tmpdirname,fl['name']))

#                 # unzip files
#                 if '.zip' in fl['name']:
#                     zipfile = ZipFile(os.path.join(tmpdirname,fl['name']), "r")
#                     zipfile.extractall(tmpdirname)

            # move file contents to group folder...
            cmd = 'cd '+tmpdirname+' ; chmod -R ug+rw '+str(analysis.id)+'; rysnc -aI '+str(analysis.id)+"/* ../ ; rm -Rf "+str(analysis.id)
            print(cmd)
    #         os.system(cmd)

        log.info('Downloaded analysis: %s for Subject: %s Session: %s', analysis.label,full_session.subject.label, full_session.label)      
    else:
        log.info('Analysis not found: for Subject: %s Session: %s', full_session.subject.label, full_session.label)  

    
    
def parser(context):
    
    parser = argparse.ArgumentParser(
        description="Method using Flywheel sdk to download analysis files to local filesystem.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # parse inputs 

    def _path_exists(path, parser):
        """Ensure a given path exists."""
        if path is None or not Path(path).exists():
            raise parser.error(f"Path does not exist: <{path}>.")
        return Path(path).absolute()

    def _is_file(path, parser):
        """Ensure a given path exists and it is a file."""
        path = _path_exists(path, parser)
        if not path.is_file():
            raise parser.error(f"Path should point to a file (or symlink of file): <{path}>.")
        return path

    PathExists = partial(_path_exists, parser=parser)
    IsFile = partial(_is_file, parser=parser)

    ##########################
    #   Required Arguments   #
    ##########################
    
    requiredNamed = parser.add_argument_group('required named arguments')

    requiredNamed.add_argument(
        "--analysis-table",
        action="store",
        metavar="TABLE",
        type=PathExists,
        help="file path to analysis table",
        required=True
    )
    
    requiredNamed.add_argument(
        "--download-path",
        action="store",
        metavar="PATH",
        type=PathExists,
        help="download path to local filesystem."
    )
    
    parser.add_argument(
        "--analysis-id-column",
        action="store",
        metavar="COLUMN NAME",
        default="analysis.id",
        help="column name from input spreadsheet storing analysis ids for download"
    )
    
    parser.add_argument(
        "--include-column",
        action="store",
        metavar="COLUMN NAME",
        help="column name from input spreadsheet storing boolean flag to download."
    )
    
    parser.add_argument(
        "--apply-custom-script",
        action="store",
        metavar="TBD",
        help="TO DO..."
    )
    
    args = parser.parse_args()
    
    # add all args to context
    args_dict = args.__dict__
    context.update(args_dict)
    
    log.info("Using Configuration Settings: ")
    log.parent.handlers[0].setFormatter(logging.Formatter('\t\t%(message)s'))
    
    log.info("analysis table path: %s", str(context["analysis_table"]))
    log.info("download path: %s", str(context["download_path"]))
    log.info("analysis-id-column: %s", str(context["analysis_id_column"]))
    log.info("include-column: %s", str(context["include_column"]))
    log.info("apply-custom-script: %s", str(context["apply_custom_script"]))
    log.parent.handlers[0].setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    
    return
    


if __name__ == "__main__":
    
    # Welcome message
    welcome_str = '{} {}'.format(Path(__file__).name, __version__)
    welcome_decor = '=' * len(welcome_str)
    log.info('\n{}\n{}\n{}'.format(welcome_decor, welcome_str, welcome_decor))

    # store command line arguments
    pycontext = dict()
    parser(pycontext)
    
    # check for download path
     # path to download directory
    if pycontext["download_path"]:
        path = pycontext["download_path"]
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
    else:
        log.warning("WARNING: No path provided for download. Using current directory")
        path = os.getcwd()
    
    log.info("Download directory: %s", path)
    
    df = pd.read_csv(pycontext["analysis_table"])
    
    if pycontext["analysis_id_column"] in df.columns:
        analysis_ids = df[pycontext["analysis_id_column"]].values
    else:
        log.error("Analysis ID column not found. Exiting...")
        sys.exit()
    
    # if include column defined
    if pycontext["include_column"] and include_column in df.columns:
        include = df[pycontext["include_column"]]
        analysis_ids = df.loc[df['include_column'], pycontext["analysis_id_column"]].values
    
    print(analysis_ids)
    for aid in analysis_ids:
        download_analysis_byid(aid, path)
    
    