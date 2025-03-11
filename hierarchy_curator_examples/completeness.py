"""
A curator script to check for session completeness
"""

import dataclasses
import json
import logging
import pandas as pd
import numpy as np
import os, sys
import flywheel
from flywheel_gear_toolkit.utils.curator import HierarchyCurator
from flywheel_gear_toolkit.utils.reporters import BaseLogRecord
import tempfile
import shutil

log = logging.getLogger("my_curator")
log.setLevel("DEBUG")


def image_counts(template, full_session: flywheel.Session, out_dict):
    acquisitions = full_session.acquisitions.find(sort='timestamp:asc')
    flag_incomplete_acqs = False
    incomplete_acqs_list = []
    for acq in acquisitions:
        # print(acq.label + ': ' + str(acq.timestamp))
        # find the acquisition in the template table
        select_row = template[template['AcquisitionLabel'] == acq.label]
        if not select_row.empty:
            select_row = select_row.iloc[0]
        # get the expected count of images
        if select_row.empty:
            # print("Acquisition doesn't exist in template")
            expected_count = np.nan
        else:
            expected_count = select_row['ExpectedLength']
            # print("Expected Length: " + str(expected_count))
        # get the dicom from the acquisition and check the zip member count
        for ff in acq.files:
            if ff['type'] == 'dicom':
                zip_count = ff['zip_member_count']
                # print("Zip count: " + str(zip_count))
        # if zip count equals expected count, then 100 percent complete. Else report percent complete
        if zip_count and not np.isnan(expected_count):
            # print("calculating percent complete")
            percent_complete = (zip_count / expected_count) * 100
        elif zip_count:
            # print("zip count exists but no expected count: problem in template")
            percent_complete = 100
        elif not np.isnan(expected_count):
            # print("zip count does not exist, but expected count does: problem in dicom")
            percent_complete = 0
        else:
            # print("Single dcm not zipped")
            percent_complete = 100

        # Store expected and percent complete in dictionary
        out_dict[acq.label + " expected count"] = expected_count
        out_dict[acq.label + " actual count"] = zip_count
        out_dict[acq.label + " percent complete"] = percent_complete

        if percent_complete < 100:
            flag_incomplete_acqs = True
            incomplete_acqs_list.append(acq.label)

    out_dict["Incomplete Acqs"] = flag_incomplete_acqs
    out_dict["Incomplete Acqs List"] = incomplete_acqs_list

    return out_dict


def image_modality_count(full_session: flywheel.Session, out_dict):
    t1_count = 0
    t2_count = 0
    resting_count = 0
    task_count = 0
    dwi_count = 0
    spec_count = 0
    fmap_count = 0
    acquisitions = full_session.acquisitions.find(sort='timestamp:asc')
    for acq in acquisitions:
        if "ignore-BIDS" in acq.label:
            continue
        # print(acq.label + ': ' + str(acq.timestamp))
        if "T1w" in acq.label:
            t1_count += 1
        if "T2w" in acq.label:
            t2_count += 1
        if "task-rest" in acq.label:
            resting_count += 1
        if "task" in acq.label and "rest" not in acq.label and "SBRef" not in acq.label:
            task_count += 1
        if "dwi" in acq.label:
            dwi_count += 1
        if "press" in acq.label:
            spec_count += 1
        if "fmap" in acq.label:
            fmap_count += 1
    out_dict["T1 count"] = t1_count
    out_dict["T2 count"] = t2_count
    out_dict["Resting state count"] = resting_count
    out_dict["Task count"] = task_count
    out_dict["DWI count"] = dwi_count
    out_dict["Spectroscopy count"] = spec_count
    out_dict["Fieldmap count"] = fmap_count
    return out_dict


def detect_duplicates(fw_client, full_session: flywheel.Session, out_dict):
    structurals = ['anat', 'T1w', 'T2w']
    functionals = ['func']
    fieldmaps = ['fmaps']
    diffusion = ['dwi']
    dup_struct = 0
    dup_func = 0
    dup_fmaps = 0
    dup_dwi = 0
    duplicates_detected = False
    acquisitions = full_session.acquisitions.find(sort='timestamp:asc')
    new_acq_list = []  # empty list to hold unique elements from the list
    duplist = []  # empty list to hold the duplicate elements from the list
    for acq in acquisitions:
        actual_acq = fw_client.get_acquisition(acq.id)
        for idx, ff in enumerate(actual_acq.files):
            if ff.type and ff.type in 'dicom':
                index_of_nifti_file = idx
                series_description = (actual_acq.files[index_of_nifti_file].info).get('SeriesDescription')
                # if no nifti (ie spec data) then skip

        if series_description:
            if series_description not in new_acq_list:
                new_acq_list.append(series_description)
            else:
                duplist.append(series_description)
                # print("Duplicates detected: " + acq.label)
                duplicates_detected = True
                # what kind of duplicates: struct, func, dwi?
                if any(name_check in acq.label for name_check in structurals):
                    dup_struct += 1
                if any(name_check in acq.label for name_check in functionals):
                    dup_func += 1
                if any(name_check in acq.label for name_check in fieldmaps):
                    dup_fmaps += 1
                if any(name_check in acq.label for name_check in diffusion):
                    dup_dwi += 1
    out_dict["Duplicates Detected"] = duplicates_detected
    out_dict["Number of Structural Duplicates"] = dup_struct
    out_dict["Number of Funcational Duplicates"] = dup_func
    out_dict["Number of Fieldmap Duplicates"] = dup_fmaps
    out_dict["Number of DWI Duplicates"] = dup_dwi
    out_dict["Duplicates List"] = duplist
    return out_dict


def check_phase_encoding_dir(fw_client, template, full_session: flywheel.Session, out_dict):
    any_bad_pe = False
    pe_error_list = []
    acquisitions = full_session.acquisitions.find(sort='timestamp:asc')
    for acq in acquisitions:
        actual_acq = fw_client.get_acquisition(acq.id)
        # print(acq.label + ': ' + str(acq.timestamp))
        # find the acquisition in the template table
        select_row = template[template['AcquisitionLabel'] == acq.label]
        if not select_row.empty:
            select_row = select_row.iloc[0]
        # get the expected count of images
        if select_row.empty:
            # print("Acquisition doesn't exist in template")
            expected_dir = np.nan
        else:
            expected_dir = select_row['ExpectedPEDir']
            # print("Expected PE Dir: " + str(expected_dir))

        for idx, ff in enumerate(actual_acq.files):
            actual_pe_dir = None
            if ff.type and ff.type in 'nifti':
                index_of_nifti_file = idx
                actual_pe_dir = actual_acq.files[index_of_nifti_file].info.get('PhaseEncodingDirection')
        # print("Actual PE Dir: " + str(actual_pe_dir))

        if actual_pe_dir and not pd.isnull(expected_dir):
            if actual_pe_dir == expected_dir:
                pe_match = True
            else:
                # print("adding acquisition to problem list")
                pe_match = False
                pe_error_list.append(acq.label)
        else:
            # print("Either no actual PE direction or no expected PE direction or both")
            pe_match = True
        # If any phase encoding discrepancydetected
        if not pe_match:
            any_bad_pe = True
    out_dict["Any Phase Encoding Discrepancy"] = any_bad_pe
    out_dict["Phase Encoding Error List"] = pe_error_list
    return out_dict


def missing_and_extra_acqs(template, full_session: flywheel.Session, out_dict):
    # TO DO: just pull the corresponding session from the template

    acquisitions = full_session.acquisitions.find(sort='timestamp:asc')
    extra_scans = []
    for acq in acquisitions:
        # print(acq.label + ': ' + str(acq.timestamp))
        # find the acquisition in the template table and delete that row.
        # Any rows remaining are missing from acquisitions
        # Using drop() to delete rows based on column value
        select_row = template[template['AcquisitionLabel'] == acq.label]
        template.drop(select_row.index, inplace=True)
        if select_row.empty:
            # print("Acquisition doesn't exist in template")
            extra_scans.append(acq.label)
    # whatever is left in template is not accounted for and therefore missing
    missing_scans = template["AcquisitionLabel"].values.tolist()
    out_dict["Missing Scans List"] = missing_scans
    out_dict["Extra Scans List"] = extra_scans
    return out_dict


def human_eyes(out_dict):
    human_eyes = True
    # no missing scans
    # no extra scans
    # no duplicates
    # no phase encoding errors
    if not out_dict["Missing Scans List"] and not out_dict["Extra Scans List"] and not out_dict[
        "Duplicates Detected"] and not out_dict["Any Phase Encoding Discrepancy"]:
        human_eyes = False
    # having spec data in Extra Scans List shouldn't count as needing human eyes because all PL imports lack spec data. However there cannot be any other extra scans in the list (ie all extra scans must be press data)
    if all('press' in extras for extras in out_dict["Extra Scans List"]):
        human_eyes = False
    out_dict["Human Eyes"] = human_eyes
    return out_dict


def session_complete(out_dict):
    session_complete = False
    percent_complete = True
    # no missing scans, all scans at 100% of expected count
    search_key = 'percent complete'
    all_perc_complete_values = [val for key, val in out_dict.items() if search_key in key]
    if any(int(perc_comp) < 100 for perc_comp in all_perc_complete_values):
        percent_complete = False
    # no missing scans and all 100s
    if not out_dict["Missing Scans List"] and percent_complete:
        session_complete = True
    out_dict["Session Complete"] = session_complete
    return out_dict


def run_downstream_analyses(out_dict):
    downstream_analyses = False
    # session complete
    # no duplicates
    # no phase encoding errors
    if out_dict["Session Complete"] and not out_dict["Duplicates Detected"] and not out_dict[
        "Any Phase Encoding Discrepancy"]:
        downstream_analyses = True
    out_dict["Run Downstream Analyses"] = downstream_analyses
    return out_dict


def events_complete(fw_client, full_session: flywheel.Session, out_dict):
    # all tasks (not rest) have "recordings" file
    acquisitions = full_session.acquisitions.find(sort='timestamp:asc')
    for acq in acquisitions:
        actual_acq = fw_client.get_acquisition(acq.id)
        if "task" in acq.label and "rest" not in acq.label and "SBRef" not in acq.label:
            # check for recordings file
            flag=False
            for idx, ff in enumerate(actual_acq.files):
                if "_stim" in ff.name:
                    flag=True
            if not flag:
                out_dict["Stimulus Complete"] = False
                return out_dict
    
    # if you have gotten here, return complete events flag
    out_dict["Stimulus Complete"] = True
    return out_dict


def robust_upload(parent, filepath):
    parent.upload_file(filepath)


class Curator(HierarchyCurator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Stop at session level since we don't need to curate anything under that.
        self.config.stop_level = "session"
        self.config.report = True

    def curate_session(self, session: flywheel.Session):
        log.info("Curating session %s", session.id)
        log.debug("Session label %s", session.label)
        # set the return code
        return_code = 0
        try:
            # get the template file
            if self.additional_input_one:
                # template = pd.read_csv(self.additional_input_one)
                template = pd.read_csv(self.additional_input_one,
                                       dtype={'Session': str, 'Modality': str, 'SeriesDescription': str,
                                              'AcquisitionLabel': str, 'ExpectedLength': float, 'ExpectedPEDir': str})
                # only extract the part of the template that corresponds to the desired/current session
                print(template.dtypes)
                session_label = session.label
                # template['Session'] = template['Session'].astype(str)
                # print(template['Session'])
                modified_template = template[template['Session'] == session_label]
                # raise error if no template exists for the current session
                if modified_template.empty:
                    log.error("No template exists for this session")
                    raise ValueError("No template exists for this session")
                    # sys.exit(1)
                    return_code = 1
                # initialize the output dictionaries: output_short is what goes into the sesssion info, output_long is what is uploaded as an attachment
                output_short = {}
                output_long = {}
                # run the completeness checks
                log.info("Running image count check")
                output_long = image_counts(modified_template, session, output_long)
                log.info("Running modality check")
                output_long = image_modality_count(session, output_long)
                # for checks that require detailed acquisition info like PE direction, need to pass the client to get to the actual acquisition (not a summary of the acquisition)
                fw_client = self.context.client
                log.info("Running duplicate check")
                output_long = detect_duplicates(fw_client, session, output_long)
                log.info("Running phase encoding check")
                output_long = check_phase_encoding_dir(fw_client, modified_template, session, output_long)
                log.info("Running missing and extra scan check")
                output_long = missing_and_extra_acqs(modified_template, session, output_long)
                log.info("Running human eyes check")
                output_long = human_eyes(output_long)
                log.info("Running completeness check")
                output_long = session_complete(output_long)
                log.info("Running downstream analyses check")
                output_long = run_downstream_analyses(output_long)
                log.info("Running events upload check")
                output_long = events_complete(fw_client, session, output_long)

                # # concatenate the two dictionaries so the long output has everything
                # log.debug("concatenating dictionaries")
                # output_long.update(output_short)

                # update the output to include the destination ID of the analysis that generated the data
                analysis_id = self.context.destination["id"]
                output_long["Analysis ID"] = analysis_id

                # copy select outputs to short output, which goes in the metadata to be indexed
                log.debug("Copying over items to short dictionary")
                output_short["Analysis ID"] = output_long["Analysis ID"]
                output_short["Any Phase Encoding Discrepancy"] = output_long["Any Phase Encoding Discrepancy"]
                output_short["Duplicates Detected"] = output_long["Duplicates Detected"]
                output_short["Duplicates List"] = output_long["Duplicates List"]
                output_short["DWI count"] = output_long["DWI count"]
                output_short["Extra Scans List"] = output_long["Extra Scans List"]
                output_short["Fieldmap count"] = output_long["Fieldmap count"]
                output_short["Human Eyes"] = output_long["Human Eyes"]
                output_short["Missing Scans List"] = output_long["Missing Scans List"]
                output_short["Phase Encoding Error List"] = output_long["Phase Encoding Error List"]
                output_short["Resting state count"] = output_long["Resting state count"]
                output_short["Session Complete"] = output_long["Session Complete"]
                output_short["Run Downstream Analyses"] = output_long["Run Downstream Analyses"]
                output_short["Spectroscopy count"] = output_long["Spectroscopy count"]
                output_short["T1 count"] = output_long["T1 count"]
                output_short["T2 count"] = output_long["T2 count"]
                output_short["Task count"] = output_long["Task count"]
                output_short["Incomplete Acqs"] = output_long["Incomplete Acqs"]
                output_short["Incomplete Acqs List"] = output_long["Incomplete Acqs List"]
                output_short["Stimulus Complete"] = output_long["Stimulus Complete"]

                # upload the short output as info data onto the session
                # current session info (make sure not to overwrite)
                upload_metadata = session.info
                upload_metadata["COMPLETENESS"] = output_short
                # upload the metadata
                log.info("Uploading metadata to session")
                session.update_info(upload_metadata)
                # #run the reporter
                # upload the full data (output_long) to the session attachment
                with tempfile.TemporaryDirectory() as temp:
                    name_of_output = "completeness_ignore-BIDS.json"
                    file_path = os.path.join(temp, name_of_output)
                    json_object = json.dumps(output_long, indent=4)
                    with open(file_path, "w") as outfile:
                        outfile.write(json_object)
                    # upload the json file
                    log.info("Uploading file to session")
                    robust_upload(session, file_path)
                    # move output file to output folder
                    shutil.move(file_path, os.path.join('/flywheel/v0/output/', name_of_output))
            else:
                raise ValueError("no csv template file found")
        except Exception as exc:
            return_code = 1
            self.reporter.append_log(
                err=str(exc),
                subject_label=session.subject.id,
                subject_id=session.subject.id,
                session_label=session.label,
                session_id=session.id,
                resolved=False,
            )
        log.info("Return code: " + str(return_code))
        return return_code
