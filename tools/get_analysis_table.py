from pathlib import Path
import os
import flywheel
import pandas as pd
import argparse
from functools import partial
import re

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')

__version__ = "0.0.1"

# get flywheel client
fw = flywheel.Client('')

def get_table(pycontext):
    
    summary=pd.DataFrame()

    # find flywheel project
    project = fw.projects.find_one('label='+pycontext["project"])
    
    # get full flywheel object
    project = fw.get_project(project.id)
    
    # get gear-name
    gear = pycontext["gear"]
    
    # loop session in project
    for ses in project.sessions.find():

        full_session=fw.get_session(ses.id)

        if  "pilot" in full_session.tags:
            continue
        
        # loop analyses in session TODO: Find a more generic walker strategy
        for analysis in full_session.analyses:
            
            # only explore flywheel jobs (not uploads)
            if not analysis.job:
                continue

        for analysis in full_session.analyses:
            if not analysis.job:
                continue
            if not pycontext["ignore_states"] and analysis.job.state != "complete":
                continue
            
            #only print ones that match the analysis label
            if pycontext["gear"] == analysis.gear_info.name:
                if pycontext["version"]:
                    r1 = re.compile(pycontext["version"])
                    if not r1.search(analysis.gear_info["version"]):
                        continue
                if pycontext["regex"] and pycontext["regex"] not in analysis.label:
                    continue
                
                # we met all conditions, store in table now
                df=pd.DataFrame({"timestamp":full_session.timestamp, 
                                 "subject.label":full_session.subject.label, 
                                 "session.label":full_session.label,
                                 "session.id": str(full_session.id),
                                 "project": fw.get_container(full_session.project).label,
                                 "Run Downstream Analyses": "COMPLETENESS" in full_session.info and full_session.info["COMPLETENESS"]["Run Downstream Analyses"] or None,
                                 "gear.name": analysis.gear_info.name,
                                 "gear.version": analysis.gear_info["version"],
                                 "analysis.label": analysis.label,
                                 "analysis.state": analysis.job.state,
                                 "analysis.id": analysis.id,
                                 "cli.cmd": 'fw download -o download.zip "{}/{}/{}/{}/{}"'.format(fw.get_container(full_session.project).label,full_session.subject.label, full_session.label,"analyses",analysis.label),
                                 "Notes": " ".join([x["text"] for x in full_session.notes])}, index=[0])
            


                summary = pd.concat([summary, df])

    summary = summary.sort_values('timestamp', ignore_index = True)
    
    return summary


def parser(context):
    
    parser = argparse.ArgumentParser(
        description="Method using Flywheel sdk to generate a table of all analyses for a specified gear. The method should be used to prepare nessesary inputs for download methods.",
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
        "--project",
        action="store",
        metavar="PROJECT",
        help="project name",
        required=True
    )

    requiredNamed.add_argument(
        "--gear",
        action="store",
        metavar="GEAR NAME",
        help="analysis gear name",
        required=True
    )
    
    parser.add_argument(
        "--version",
        action="store",
        metavar="VERSION",
        help="analysis gear version number"
    )
    
    parser.add_argument(
        "--regex",
        action="store",
        metavar="LABEL REGULAR EXPRESSION",
        help="regular expression to subselect analyses by label"
    )
    
    parser.add_argument(
        "--ignore-states",
        action="store_true",
        default=False,
        help="(Default: False) Ignore analyses with state 'failed, running, or cancelled'. Report all analyses regardless of state in table."
    )
    
    args = parser.parse_args()
    
    # add all args to context
    args_dict = args.__dict__
    context.update(args_dict)
    
    log.info("Using Configuration Settings: ")
    log.parent.handlers[0].setFormatter(logging.Formatter('\t\t%(message)s'))
    
    log.info("project: %s", str(context["project"]))
    log.info("gear name: %s", str(context["gear"]))
    log.info("gear version: %s", str(context["version"]))
    log.info("analysis label regex: %s", str(context["regex"]))
    log.info("ignore job status: %s", str(context["ignore_states"]))
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
    
    # generate gear table
    summary = get_table(pycontext)
    
    # save spreadsheet
    if pycontext["version"]:
        label=pycontext["project"].lower()+"."+pycontext["gear"]+"-"+pycontext["version"]+".table.csv"
    else:
        label=pycontext["project"].lower()+"."+pycontext["gear"]+".table.csv"
    
    summary.to_csv(label,index=False)
    
    log.info("Analysis Spreadsheet saved: %s", os.path.join(os.getcwd(),label))
    