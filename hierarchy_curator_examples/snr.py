"""
A script to generate snr plots for preprocessed 

Project: YEARS
Platform: Flywheel or standalone
Author: Amy Hegarty
Modified: 2024-10-10
"""

import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
import argparse
from functools import partial
from pathlib import Path
import json
import re
import time

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')

__version__ = "0.0.1"


years_all_labels=[
    "Cue.look",
    "Cue.decrease",
    "ImagePos.look",
    "ImagePos.decrease",
    "ImageNeut.look",
    "ImageNeg.look",
    "ImageNeg.decrease",
    "AffectratingPos.look",
    "AffectratingPos.decrease",
    "AffectratingNeg.look",
    "AffectratingNeg.decrease",
    "iti"
]

mid_all_labels=[
    "instructions",
    "E.cue",
    "E.target",
    "E.failure",
    "P.cue",
    "P.target",
    "P.failure",
    "iti" 
]

dummyVols = 22
tr = 0.460


def years_events(df, image_dict):
    # create stimulus related events
    events = pd.DataFrame()

    # get the waiting for scanner time (actual start of the data)
    time0 = df.iloc[0]["AfterTrig.OnsetTime"] - df.iloc[0]["AfterTrig.OnsetDelay"]

    log.info("Creating stimulus based events...")
    log.info("Using timing offest set by AfterTrig.OnsetTime: %s secs", str(time0 / 1000))

    # experiment design: (stablization fixation --> (events loop: cue --> fixation --> image --> affect rating --> fixation: repeat) --> final fixation)
    #  desired events for:
    #     (1) instructions: cue+fixation
    #     (2) image (valence from supporting dict)
    #     (3) affect rating (Pos/Neg)
    #     (5) fixation

    # group each event by:
    #   - instruction (LOOK|CHANGE)

    # Set up a "key" for event names and matching experiment log entrys
    keys = pd.DataFrame({"name": ["Cue", "cue-fixation", "image", "affectrating", "iti"],
                         "onset": ["Cue.?.OnsetTime", "Fixation(2|3).OnsetTime", "Image.?.OnsetTime",
                                   "AffectRating.*\.OnsetTime", "Fixation(1|4).OnsetTime", ],
                         "duration": ["Cue.?.Duration$", "Fixation(2|3).Duration$", "Image.?.Duration$",
                                      "AffectRating.*.Duration$", "Fixation(1|4).Duration$", ],
                         })

    # create simple coding for Neg / Pos Trial Procedure
    df.loc[df['Procedure[Trial]'] == 'NegTrialProc', 'trialtype'] = 'neg'
    df.loc[df['Procedure[Trial]'] == 'PosTrialProc', 'trialtype'] = 'pos'

    for index, row in df.iterrows():

        try:
            image_valence = image_dict["coding"].loc[image_dict["filename"] == row["Picture"]].values[0]
        except:
            log.warning("typicality rating not found for word: %s", str(row["Picture"]))
            image_valence = None

        # for each entry, look for valid column ids
        for index2, key in keys.iterrows():
            col_onset = findvalidId(row.to_frame().T, key["onset"])
            col_duration = findvalidId(row.to_frame().T, key["duration"])

            instances = len(col_onset)
            for i in range(len(col_onset)):
                try:
                    if key["name"] == "image":
                        trial_type = key["name"].capitalize() + image_valence.lower().capitalize() + "." + row[
                            "Instruction"].lower()
                    elif key["name"] == "affectrating":
                        trial_type = key["name"].capitalize() + row["trialtype"].lower().capitalize() + "." + row[
                            "Instruction"].lower()
                    elif key["name"] == "iti":
                        trial_type = key["name"]
                    else:
                        trial_type = key["name"] + "." + row["Instruction"].lower()
                    log.debug("using: " + col_onset[i] + ", " + col_duration[i] + ": " + str(
                        row[col_onset[i]] - time0) + " " + str(row[col_duration[i]]))
                    tmp = pd.DataFrame({
                        "onset": row[col_onset[i]] - time0,
                        "duration": row[col_duration[i]],
                        "trial_type": trial_type}, index=[0])
                    events = pd.concat([events, tmp], axis=0, ignore_index=True)
                except:
                    log.warning("Warning: row iter " + str(row["PracticeList"]) + " encountered a problem")

    # combine events cue and cue-fixation
    rows_to_drop = []
    for index, row in events.iterrows():
        if re.match('Cue\..*', events["trial_type"].loc[index]):
            events["duration"].loc[index] = events["duration"].loc[index] + events["duration"].loc[index + 1]
            rows_to_drop.append(index + 1)

    events.drop(rows_to_drop, inplace=True)
    events["onset"] = events["onset"] / 1000
    events["duration"] = events["duration"] / 1000
    #     events["offset"] = events["onset"]+events["duration"]
    events = events.sort_values("onset", ignore_index=True)
    
    # look for first cue of the run and set refine timing so it matches exactly for afni purposes...
    first_occurrence_id = events[events['trial_type'].str.contains("Cue")].index[0]

    if abs(events.loc[first_occurrence_id, "onset"] - dummyVols*tr) < 0.5:
        events.loc[first_occurrence_id, "onset"] = round(dummyVols*tr, 3)
    # check if any of the preset events are missing from list, if so add placeholders for the missing ones
    events = add_missing_events(events,years_all_labels)
    
    log.info("Complete")
    return events, df


def findvalidId(df, pattern):
    # find non-zero columns
    non_zero_columns = df.columns[(df != 0).any()]
    result_df = df[non_zero_columns]

    # drop nan columns
    result1_df = result_df.dropna(axis=1, inplace=False)

    # filter for desired
    df_filter = result1_df.filter(regex=pattern)

    return list(df_filter.columns)


def add_missing_events(df,all_labels):
    # special case when using afni workflow to ensure each event file records all possible events (missing are listed -1:1 ). Permits use of afni's 1d_timing.py tool
    existing_labels = set(df["trial_type"])
    
    for l in all_labels:
        if l not in existing_labels:
            tmp = pd.DataFrame({
                        "onset": -1,
                        "duration": 1,
                        "trial_type": l}, index=[0])
            df = pd.concat([df, tmp], axis=0, ignore_index=True)
            log.debug("Added missing event type %s: -1:1", l)
    df = df.sort_values("onset", ignore_index=True)
    
    return df


def mid_events(df):
    # get the waiting for scanner time (actual start of the data)
    idx = df["Wait4Trigger.RTTime"].first_valid_index()
    time0 = df["Wait4Trigger.RTTime"][idx]

    log.info("Creating stimulus based events...")
    log.info("Using timing offest set by Wait4Trigger.RTTime: %s secs", str(time0 / 1000))

    # experiment design: (stablization fixation + instructions --> (events loop: cue --> target --> delay --> failure/sucess --> ITI --> target --> delay --> failure/sucess: repeat) --> final fixation)
    #  desired events for:
    #     (1) instructions
    #     (2) cue
    #     (3) target
    #     (4) delay
    #     (5) failure/sucess
    #     (6) ITI

    # group each event by:
    #   - trialtype      (Even Scream | Even Safe | Pos Scream | Pos Safe)

    # Set up a "key" for event names and matching experiment log entrys
    keys = pd.DataFrame({
        "name": ["{}.cue", "delay", "{}.target", "delay2", "result", "iti"],
        "onset": [".*Cue.*\.OnsetTime$", ".*Delay.?\.OnsetTime$", ".*Target.?\.OnsetTime$", ".*Delay2.*\.OnsetTime$",
                  "(PT|ET|PS|ES)(Success|Failure).OnsetTime$", ".*(Success|Failure)ITI.OnsetTime$"],
        "duration": [".*Cue.*\.Duration$", ".*Delay.?\.Duration$", ".*Target.?\.Duration$", ".*Delay2.*\.Duration$",
                     "(PT|ET|PS|ES)(Success|Failure).Duration$", ".*(Success|Failure)ITI.Duration$"],
    })

    # inital blocks:
    idx1 = df["instruct1.OnsetTime"].first_valid_index()
    events = pd.DataFrame({
        "onset": df["instruct1.OnsetTime"][idx1] - time0,
        "duration": df["instruct1.Duration"][idx1],
        "trial_type": "instructions"
    }, index=[0])

    # create simple coding for Neg / Pos Trial Procedure
    df.loc[df['Procedure'] == 'EvenTrialScream', 'trialtype'] = 'E'
    df.loc[df['Procedure'] == 'PosTrialScream', 'trialtype'] = 'P'
    df.loc[df['Procedure'] == 'EvenTrialSafe', 'trialtype'] = 'E'
    df.loc[df['Procedure'] == 'PosTrialSafe', 'trialtype'] = 'P'

    for index, row in df[idx1:].iterrows():

        # for each entry, look for valid column ids
        for index2, key in keys.iterrows():
            col_onset = findvalidId(row.to_frame().T, key["onset"])
            col_duration = findvalidId(row.to_frame().T, key["duration"])

            instances = len(col_onset)

            for i in range(len(col_onset)):
                # special case... change generic name to row specific results
                if key["name"] == "result":
                    key["name"] = "{}.success" if "Success" in col_onset[0] else "{}.failure"

                try:
                    log.debug("using: " + col_onset[i] + ", " + col_duration[i] + ": " + str(
                        row[col_onset[i]] - time0) + " " + str(row[col_duration[i]]))
                    tmp = pd.DataFrame({
                        "onset": row[col_onset[i]] - time0,
                        "duration": row[col_duration[i]],
                        "trial_type": key["name"].format(row["trialtype"])}, index=[0])
                    events = pd.concat([events, tmp], axis=0, ignore_index=True)
                except:
                    log.warning("Warning: row iter " + str(row["Block"]) + " encountered a problem")

    # combine events cue and cue-fixation
    rows_to_drop = []
    for index, row in events.iterrows():
        if re.match('.*\.cue', events["trial_type"].loc[index]):
            events["duration"].loc[index] = events["duration"].loc[index] + events["duration"].loc[index + 1]
            rows_to_drop.append(index + 1)

    events.drop(rows_to_drop, inplace=True)

    rows_to_drop = []
    for index, row in events.iterrows():
        if re.match('.*\.target', events["trial_type"].loc[index]):
            events["duration"].loc[index] = events["duration"].loc[index] + events["duration"].loc[index + 1]
            rows_to_drop.append(index + 1)

    events.drop(rows_to_drop, inplace=True)


    events["onset"] = events["onset"] / 1000
    events["duration"] = events["duration"] / 1000
    events = events.sort_values("onset", ignore_index=True)
    
    # check if any of the preset events are missing from list, if so add placeholders for the missing ones
    events = add_missing_events(events,mid_all_labels)
    
    log.info("Complete")
    return events, df


def main(file, outputpath, image_dict_file):
    log.info('Deriving Events for file: %s', str(file))
    if not outputpath:
        outputpath = file.parents[0]

    # organize eprime file to needed columns only
    if "csv" in file.suffix:
        delim = ","
    elif "tsv" in file.suffix or "txt" in file.suffix:
        delim = '\t'

    # read in eprime file - check for extra header information first
    pos = 0
    oldpos = None

    with open(file) as fp:
        while pos != oldpos:  # make sure we stop reading, in case we reach EOF
            line = fp.readline()
            if line.startswith("ExperimentName"):
                # set the read position to the start of the line
                # so pandas can read the header
                fp.seek(pos)
                break
            oldpos = pos
            pos = fp.tell()  # remember this position as the start of the next line

        stimlogs = pd.read_csv(fp, delimiter=delim)

    if image_dict_file:
        image_dict = pd.read_csv(image_dict_file, delimiter=",")
    else:
        log.warning("Image dictionary not provided.")
        image_dict = pd.DataFrame()

    # build and save stimulus events file
    if "mid" in str(file):
        events, data = mid_events(stimlogs)
    elif "years" in str(file):
        events, data = years_events(stimlogs, image_dict)

    # save outputs
    outname = os.path.join(outputpath, str(file.name).replace("_stim" + file.suffix, "_events.tsv"))
    events.to_csv(outname, sep='\t', header=True, index=False, mode='w')
    log.info("Outputs written: %s", outname)


def parser(context):
    parser = argparse.ArgumentParser(
        description="Generates Event Onset and duration files for use in neuroimaging conputational modeling software (e.g. FEAT, CONN, AFNI). For use in YEARS study.",
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
    parser.add_argument(
        "eprimefile",
        action="store",
        metavar="EPRIME.txt",
        type=PathExists,
        help="file path for eprime text file (tab delimited) used to generate events."
    )

    parser.add_argument(
        "--outputpath",
        action="store",
        metavar="PATH",
        type=PathExists,
        help="output path to store generated files (e.g. /flywheel/v0/outputs)"
    )

    parser.add_argument(
        "--images",
        action="store",
        metavar="PATH",
        type=PathExists,
        help="path for normative typicality rating"
    )

    args = parser.parse_args()

    # add all args to context
    args_dict = args.__dict__
    context.update(args_dict)


if __name__ == "__main__":
    # Welcome message
    welcome_str = '{} {}'.format('event_curator', __version__)
    welcome_decor = '=' * len(welcome_str)
    log.info('\n{}\n{}\n{}'.format(welcome_decor, welcome_str, welcome_decor))

    # run main
    pycontext = dict()
    parser(pycontext)

    main(pycontext["eprimefile"], pycontext["outputpath"], pycontext["images"])

# -----------------------------------------------------------------
# Flywheel Curator Functions. Do Not Change! 
#  (Consult INC team for instructions)
# -----------------------------------------------------------------

import os
import tempfile
import subprocess as sp
import backoff
import shutil
from flywheel.rest import ApiException
from flywheel_gear_toolkit.utils.curator import HierarchyCurator


def is_not_500_502_504(exc):
    if hasattr(exc, "status"):
        if exc.status in [504, 502, 500]:
            # 500: Internal Server Error
            # 502: Bad Gateway
            # 504: Gateway Timeout
            return False
    return True


@backoff.on_exception(
    backoff.expo, ApiException, max_time=60, giveup=is_not_500_502_504
)
# will retry for 60s, waiting an exponentially increasing delay between retries
# e.g. 1s, 2s, 4s, 8s, etc, giving up if exception is in 500, 502, 504.

class Curator(HierarchyCurator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, extra_packages=["tqdm==4.59.0", "backoff==1.11.1"])
        # Curate depth first
        #   Important to curate depth first so that all files in curate_file
        #   Are guaranteed to be under the current self.sub_label
        self.config.depth_first = True
        self.data = {}

    def curate_subject(self, subject):
        self.data["sub_label"] = subject.label

    def curate_file(self, file_):
        if ".csv" in file_.name:
            # Get parent of file
            parent_type = file_.parent_ref["type"]
            if parent_type != "acquisition":
                # Only curate acquisition files.
                return
            parent = self.context.client.get(file_.parent_ref.id)

            bids_info = self.get_bids_object(parent, file_)

            # Download EPRIME file, generate events files, and upload back to acquisition
            with tempfile.TemporaryDirectory() as temp:
                file_.reload()
                path = os.path.join(temp, bids_info["Filename"])
                file_.download(path)

                # run main from above...                
                main(Path(path), Path(temp), self.additional_input_one)

                # list of files to upload
                searchfiles = sp.Popen(
                    "cd " + temp + "; ls *.tsv *.zip",
                    shell=True,
                    stdout=sp.PIPE,
                    stderr=sp.PIPE, universal_newlines=True
                )
                stdout, _ = searchfiles.communicate()

                filelist = stdout.strip("\n").split("\n")

                if file_.name in filelist: filelist.remove(file_.name)

                log.info("Uploading files to aquisition %s: \n%s", parent.label, "\n".join(filelist))

                reset_flag = self.context.config['reset']

                for f in filelist:
                    self.robust_upload(parent, os.path.join(temp, f), reset_flag, add_bids_info=True)

                # move output files to outputs folder
                searchfiles = sp.Popen(
                    "cd " + temp + "; ls * ",
                    shell=True,
                    stdout=sp.PIPE,
                    stderr=sp.PIPE, universal_newlines=True
                )
                stdout, _ = searchfiles.communicate()

                filelist = stdout.strip("\n").split("\n")

                if file_.name in filelist: filelist.remove(file_.name)

                for f in filelist:
                    shutil.move(os.path.join(temp, f), os.path.join('/flywheel/v0/output/', f))

    def robust_upload(self, parent, filepath, reset=False, add_bids_info=False):
        if parent.get_file(os.path.basename(filepath)):
            if not reset:
                log.info("file already exists %s \n Do Nothing.", os.path.basename(filepath))
                return
            else:
                log.info("overwriting file: %s \n", os.path.basename(filepath))
        parent.upload_file(filepath)
        log.info("uploaded file:%s to acquisiton: %s", filepath, parent.label)

    def get_bids_object(self, parent, file):
        if "events" in file.name:
            modality = "events"
        elif "stim" in file.name:
            modality = "stim"
        else:
            modality = "stim"

        name, ext = os.path.splitext(file.name)
        res = dict(map(str.strip, sub.split('-', 1))
                   for sub in parent.label.split('_') if '-' in sub)
        folder = parent.label.split('-')[0]
        subject = self.context.client.get(parent.parents.subject).label
        session = self.context.client.get(parent.parents.session).label
        bids_obj = {
            'Sub': subject,
            'Ses': session,
            'Task': res.get('task'),
            'Acq': res.get('acq'),
            'Ce': res.get('ce'),
            'Rec': res.get('rec'),
            'Dir': res.get('dir'),
            'Run': res.get('run'),
            'Recording': res.get('recording'),
            'error_message': None,
            'Filename': None,
            'Folder': folder,
            'ignore': False,
            'Modality': modality,
            'Part': None,
            'Path': f'sub-{subject}/ses-{session}/{folder}',
            'valid': True
        }
        bids_obj["Filename"] = result = '_'.join(f'{key.lower()}-{value}' for key, value in bids_obj.items() if
                                                 key in ["Sub", "Ses", "Acq", "Ce", "Dir", "Rec", "Run", "Task",
                                                         "Recording"] and value) + "_" + bids_obj["Modality"] + ext
        bids_obj.pop('Sub', None);
        bids_obj.pop('Ses', None)  # sub and session not included in final bids file  object
        bids_obj.pop('Recording', None)  # recording not included in final bids file object

        return bids_obj


