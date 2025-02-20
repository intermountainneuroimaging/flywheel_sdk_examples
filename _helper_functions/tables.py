import sys, os, logging
import flywheel
from datetime import datetime, date
import pandas as pd
import re
import json

fw = flywheel.Client('')
log = logging.getLogger(__name__)

        
def get_table_by_gearname(pycontext, gearname):
    
    pycontext["gear"] = gearname
    log.info("Using Configuration Settings: ")
    log.parent.handlers[0].setFormatter(logging.Formatter('\t%(message)s'))
    
    log.info("project: %s", str(pycontext["project"]))
    log.info("gear name: %s", str(pycontext["gear"]))
    if "version" in pycontext:
        log.info("gear version: %s", str(pycontext["version"]))
    if "regex" in pycontext:
        log.info("analysis label regex: %s", str(pycontext["regex"]))
    log.parent.handlers[0].setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    
    summary=pd.DataFrame()

    # find flywheel project
    project = fw.projects.find_one('label='+pycontext["project"]+',group='+pycontext["group"])
    
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
            
            #only print ones that match the analysis label
            if pycontext["gear"] == analysis.gear_info.name:
                if "version" in pycontext:
                    r1 = re.compile(pycontext["version"])
                    if not r1.search(analysis.gear_info["version"]):
                        continue
                if "regex" in pycontext and pycontext["regex"] not in analysis.label:
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

        
def get_table_by_template(user_inputs, template_file_name="gear_template.json"):
    
    log.info("Using Configuration Settings: ")
    log.parent.handlers[0].setFormatter(logging.Formatter('\t%(message)s'))
    log.info("project: %s", str(user_inputs["project"]))

    # get project specifics
    project = fw.projects.find_one(f'label={user_inputs["project"]},group={user_inputs["group"]}')
    
    template_file = project.get_file(template_file_name)
    if not template_file:
        log.info(f"{template_file_name} not found within project: {project.label}. Skipping...")
        return
    
    log.info("analysis template: %s", template_file.name)
    log.parent.handlers[0].setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

    file_content = template_file.read()
    try:
        template = json.loads(file_content.decode('utf-8'))  # Decode bytes to string and load JSON
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return

    # STEP 1: create dataframe with all sessions and info
    table = pd.DataFrame()
    for ses in project.sessions.find():

        full_session=fw.get_session(ses.id)

        if  "pilot" in full_session.tags:
            continue

        df=pd.DataFrame({"timestamp": full_session.timestamp,
                         "subject.label":full_session.subject.label, 
                         "session.label":full_session.label,
                         "flywheel_id": str(full_session.id),
                         "project": fw.get_container(full_session.project).label,
                         "Run Downstream Analyses": full_session.info["COMPLETENESS"]["Run Downstream Analyses"] if "COMPLETENESS" in full_session.info else None,
                         "Notes": " ".join([x["text"] for x in full_session.notes])}, index=[0])
        table = pd.concat([table,df], ignore_index = True)
    
    log.info('adding %s sessions...', len(table))
    
    # STEP 2: Sort Columns to Pull
    gears_dict = {}
    for itr, itr_template in enumerate(template["analysis"]):

        # analysis information...
        my_gear_name=itr_template["gear-name"]+"/"+itr_template["gear-version"] if "gear-version" in itr_template else itr_template["gear-name"]
        my_gear_label = itr_template["custom-label"] if "custom-label" in itr_template else itr_template["gear-name"]
        
        # what if gear names are used more than once...
        ii=0
        while my_gear_name in gears_dict.keys():
            my_gear_name += "+"
            ii += 1
            if ii > 10:
                break

        gears_dict.update({my_gear_name: my_gear_label})
    
    log.info('adding %s analyses from template...', len(gears_dict))
    
    #initalize columns
    for gear in gears_dict.keys():
        gear_label = gears_dict[gear]
        table[gear_label] = ""
    
    # STEP 3: fill in analysis columns
    for idx, row in table.iterrows():
        full_session = fw.get_session(row["flywheel_id"])

        for analysis in full_session.analyses:
                if not analysis.job:
                    continue
                if analysis.job.state == "complete":
                    for g in gears_dict.keys():
                        # store gear label 
                        g_label = gears_dict[g]
                        # remove placeholder for repeat columns...
                        gear_name = g.replace("+","")
                        if "/" in g:   ## this is a gear + version
                            if (analysis.gear_info.name == gear_name.split("/")[0]) and (analysis.gear_info.version == gear_name.split("/")[1]) and (g_label in analysis.label):
                                table.loc[idx, g_label] = str(analysis.id)
                        else:
                            if (analysis.gear_info.name == gear_name) and (g_label in analysis.label):
                                table.loc[idx, g_label] = str(analysis.id)
    
    # make sure notes are last column
    column_to_move = table.pop("Notes")
    table.insert(len(table.columns), "Notes", column_to_move)
    
    table = table.sort_values('timestamp', ignore_index = True)
    
    return table

