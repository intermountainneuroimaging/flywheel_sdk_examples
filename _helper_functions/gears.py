from pathlib import Path
import sys, subprocess, os, logging
import flywheel
import glob
import pandas as pd
from time import sleep
import re
import tempfile
import json
from dateutil.tz import tzutc
from datetime import datetime, timedelta


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')

fw = flywheel.Client('')

## Helper Function for getting date
def get_x_days_ago(x, date=None):
    if date is None:
        date = datetime.now()
    return date - timedelta(days=x)


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
        
        
def generate_inputs(session, template):
    
    # if analysis should run - generate all inputs then run...
    if "inputs" in template:
        # initalize my inputs as dictionary
        myinputs = dict()
        
        # loop through all inputs in template
        for key in template["inputs"]:

            # put input files in the format flywheel gear.run expects...
            if "parent-container" in template["inputs"][key]:
                fw_container = fw.get_container(session.parents[template["inputs"][key]["parent-container"]])
            elif "find-analysis" in template["inputs"][key]:
                fw_container = find_analysis(session, template["inputs"][key]["find-analysis"],status=["complete"])
            else:
                log.error("Unable to interpret inputs: Project %s Subject %s Session %s %s ", project.label, full_session.subject.label, full_session.label, full_session.id)

            # if 'value' key is passed for an input, just get the file from flywheel using given name"
            if "value" in template["inputs"][key]:
                file_found = fw_container.get_file(template["inputs"][key]["value"])
                if "optional" in template["inputs"][key] and template["inputs"][key]["optional"] == True and not file_found:
                        pass
                else:
                    myinputs[key]=fw_container.get_file(template["inputs"][key]["value"])

            # if 'regex' key is passed from an input, look for files matching the regular expression, save file if a match is found
            elif "regex" in template["inputs"][key]:

                namelist = [file['name'] for file in fw_container.files]

                r1=re.compile(template["inputs"][key]["regex"])
                matching_names = [x for x in namelist if r1.search(x)]

                if len(matching_names) == 1:
                    myinputs[key]=fw_container.get_file(matching_names[0])
                    log.debug("files found for analysis: %s"," ,".join(matching_names))

                elif len(matching_names) > 1:
                    log.debug("files found for analysis: %s"," ,".join(matching_names))
                    log.error("not sure which file to use, multiple matches...skipping")
                    run_flag = False 

                elif len(matching_names) < 1:
                    # check if input was optionl, if so, ok that is wasn't found, proceed
                    if "optional" in template["inputs"][key] and template["inputs"][key]["optional"] == True:
                        pass
                    else:
                        log.error("unable to locate required file input...skipping")
                        run_flag = False 
    else:
        myinputs = None
    
    return myinputs



def my_analysis_exists(container, gear_info, status=["complete","running","pending"], status_bool_type="any", count_up_to_failures=1, analysis_label=None):
    # Returns True if analysis already exists with a running or complete status, else false
    # make sure to pass full session object (use fw.get_session(session.id))
    #
    #Get all analyses for the session
    flag=False
    counter=0
    
    #handle checks for any version of gear or specific version 
    if "/" in gear_info:
        gear_name = gear_info.split("/")[0]
        gear_version = gear_info.split("/")[1]  # allow wildcard expressions here to check for multiple gear versions 
    else:
        gear_name = gear_info
        gear_version = []
        
    # pull both session and acquisition level analyses to check... a bit slower but more complete.
    acq_analyses = [ fw.get_acquisition(a.id).analyses for a in container.acquisitions.find()] # pull analyses from all acquisitions
    acq_analyses = [item for sublist in acq_analyses for item in sublist] #flatten list of acquisitons
    ses_analyses = container.analyses
    all_analyses = ses_analyses+acq_analyses
    
    # check all session analyses
    for analysis in all_analyses:
        if not analysis.gear_info:
            continue
        #only print ones that match the analysis label
        if gear_name == analysis.gear_info.name:
            if gear_version:
                r1 = re.compile(gear_version)
                if not r1.search(analysis.gear_info["version"]):
                    continue
            if analysis_label:
                if analysis_label not in analysis.label:
                    continue
            #filter for only successful job
            analysis_job=analysis.job
            if not hasattr(analysis_job,'state'): 
                flag=True
            else:
                if any(analysis_job.state in string for string in status):
                    if analysis_job.state == "failed":
                        counter += 1
                        if counter >= count_up_to_failures:
                            flag=True
                    else:
                        flag=True
                else:
                    # if any of the analyses that match name and version, but do not match status
                    if status_bool_type == "all":
                        return False
    
    return flag


def find_analysis(container, gear_info, status=["complete","running","pending"]):
    # Returns analysis object if exists by analysis name in that container
    # make sure to pass full session object (use fw.get_session(session.id))
    #
   
    #handle checks for any version of gear or specific version 
    if "/" in gear_info:
        gear_name = gear_info.split("/")[0]
        gear_version = gear_info.split("/")[1]  # allow wildcard expressions here to check for multiple gear versions 
    else:
        gear_name = gear_info
        gear_version = []
    
    #Get all analyses for the session
    analys_obj = None
    
    # check all session analyses
    for analysis in container.analyses:
        
        if not analysis.gear_info:
            continue
            
        #only print ones that match the analysis label
        if gear_name == analysis.gear_info.name:
            if gear_version:
                r1 = re.compile(gear_version)
                if not r1.search(analysis.gear_info["version"]):
                    continue
                    
            analysis_job=analysis.job
            if not hasattr(analysis_job,'state'): 
                analys_obj = analysis
            else:
                if any(analysis_job.state in string for string in status):
                    analys_obj = analysis
    
    return analys_obj
    
    
    
def my_checks(session, template):
    
    my_gear_name=template["gear-name"]+"/"+template["gear-version"] if "gear-version" in template else template["gear-name"]
    my_gear_label = template["custom-label"] if "custom-label" in template else template["gear-name"]
    numfails = template["count-failures"] if "count-failures" in template else 1
    run_flag = True
    
    # 1. check if analysis already run 
    if my_analysis_exists(session, my_gear_name, status=["complete","running","pending", "failed"], count_up_to_failures=numfails, analysis_label=my_gear_label):
        log.info("EXISTING analysis found: Skipping... %s for Project %s Subject %s Session %s %s", my_gear_label, fw.get_project(session.parents["project"]).label, session.subject.label, session.label,session.id)
        return False 

    # 2. check if prerequisites are satisfied
    if "prerequisites" in template:
        for prereq in template["prerequisites"]:
            prereq_gear_name = prereq["prereq-gear"]
            prereq_gear_label = prereq["prereq-analysis-label"] if "prereq-analysis-label" in prereq else None
            prereq_type = prereq["prereq-complete-analysis"] if "prereq-complete-analysis" in prereq else "any"
            
            if not my_analysis_exists(session, prereq_gear_name, status=["complete"],status_bool_type=prereq_type, analysis_label=prereq_gear_label):
                log.info("PREREQUISITES not met: Skipping... %s for Project %s Subject %s Session %s %s", my_gear_label, fw.get_project(session.parents["project"]).label, session.subject.label, session.label,session.id)
                return False

    # 3. check for any completeness or session tags
    if "completeness-tags" in template:
        if "COMPLETENESS" not in session.info:
            run_flag = False
            log.info("Completeness conditions not accessible ... Project %s Subject %s Session %s %s ", fw.get_project(session.parents["project"]).label, session.subject.label, session.label, session.id)
        else:
            for tag in template["completeness-tags"]:
                if not session.info["COMPLETENESS"][tag]:
                    run_flag = False
                    log.info("Completeness condition not satified: %s ... Project %s Subject %s Session %s %s ",tag, fw.get_project(session.parents["project"]).label, session.subject.label, session.label,session.id)

    if run_flag == False: return False

    if "session-tags" in template:
        for tag in template["session-tags"]:
            if tag not in session.tags:
                run_flag = False
                log.info("Missing Required session tag: %s ... Project %s Subject %s Session %s %s ",tag, fw.get_project(session.parents["project"]).label, session.subject.label, session.label,session.id)

    if run_flag == False: return False

    # if you reach this point, all checks passed...
    return True



def read_file_to_memory(file):
    file_content = file.read()
    try:
        output = json.loads(file_content.decode('utf-8'))  # Decode bytes to string and load JSON
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return
    return output
    
    
def get_container_type(cid):
    return fw.get_container(cid).container_type


def run_auto_gear(session_id, template_file_name = "gears_template_JSON.txt"):
    
    # check id passed is a session id, if not abort
    if get_container_type(session_id) != 'session':
        log.info("Flywheel Container %s is a %s... not session. Skipping", session_id, get_container_type(session_id))
        return
    
    full_session=fw.get_session(session_id)
    project = fw.get_project(full_session["parents"]["project"])
         
    template_file = project.get_file(template_file_name)
    if not template_file:
        log.info(f"{template_file_name} not found within project: {project.label}. Skipping...")
        return
    template = read_file_to_memory(template_file)
    
    # run each analysis...based on conditions in template
    for itr, json in enumerate(template["analysis"]):
        
        # pull session and project info at the beggining of each gear call in case changes have occured
        full_session=fw.get_session(session_id)

        # get gear for analysis (check for optional template entry "gear version" to include in gear descrip)
        my_gear_name = json["gear-name"]+"/"+json["gear-version"] if "gear-version" in json else json["gear-name"]
        gear = fw.lookup("gears"+"/"+my_gear_name)

        # generate analysis label
        mylabel = json["custom-label"] if "custom-label" in json else gear['gear']['name']

        # ------------------------------- #
        # ----------- checks ------------ #
        # ------------------------------- #
        
        # 1. check for exisiting analyses...
        if not my_checks(full_session, json):
            continue
        
        # ------------------------------- #
        # ------------ run -------------- #
        # ------------------------------- #
                                   
        # label for new analysis....
        mylabel = mylabel+datetime.now().strftime(" %x %X")
        
        # pull inputs
        myinputs = generate_inputs(full_session, json)
                                      
        # pull config
        myconfig = json["config"]

        # pull tags
        mytags = json["tags"]

        run_gear(gear, myconfig, myinputs, mytags, full_session, analysis_label=mylabel)
        log.info('RUNNING gear: %s Project %s Subject %s, Session %s %s ', mylabel, project.label, full_session.subject.label, full_session.label, full_session.id)
        sleep(json["sleep_seconds"])
                                      
    return
                                      
        