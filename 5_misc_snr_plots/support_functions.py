import glob
import pandas as pd
import re
from pathlib import Path
import os
import sys
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from nilearn import masking, plotting, image
from matplotlib.patches import Rectangle


def get_snr(fmri_file, mask_file, dummyVols = 0):
    img = image.load_img(fmri_file)
    cropped_img = img.slicer[..., dummyVols:]
    mask = image.load_img(mask_file)

    img_2d = masking.apply_mask(cropped_img, mask)
    
    # Compute TSNR
    tsnr = np.mean(img_2d, axis=0) / np.std(img_2d, axis=0)
    
    # Replace NaN values with 0
    tsnr[np.isnan(tsnr)] = 0
    
    mean_tsnr = np.mean(tsnr[tsnr != 0])
    
    # Compute the global signal
    global_signal = img_2d.mean(axis=1)

    # Recreate 3D nifti + plot with Nilearn
    tsnr_img = masking.unmask(tsnr, mask_img=mask)
    del tsnr, img_2d
    
    # grab tr to share with computing downstream
    tr = img.header["pixdim"][4]
    return tsnr_img, img, global_signal, tr


def plot_events(events, ax):

    # set y value by event type
    def colors(name):
        if "instruction" in name:
            return "blue"
        elif "image" in name:
            return "orange"
        elif "affectresp" in name:
            return "tab:green"
        elif "tacticresp" in name:
            return "tab:red"
        elif "fixation" in name:
            return "tab:purple"
        else:
            return 0

    def yvalues(name):
        tactic_conditions = ["Not", "Current", "Acceptance", "Future", "Other","null"]
        inst_conditions = ["LOOK","CHANGE"]
        if "look.not" in name:
            return 12
        elif "look.current" in name:
            return 11
        elif "look.acceptance" in name:
            return 10
        elif "look.future" in name:
            return 9
        elif "look.other" in name:
            return 9
        elif "look.null" in name:
            return 7
        if "change.not" in name:
            return 6
        elif "change.current" in name:
            return 5
        elif "change.acceptance" in name:
            return 4
        elif "change.future" in name:
            return 3
        elif "change.other" in name:
            return 2
        elif "change.null" in name:
            return 1
        else:
            return 0


    patches=[]
    for idg, g in enumerate(events['trial_type'].unique()):
        df = events[events['trial_type'] == g]
        df = df.reset_index(drop=True)

        for index, row in df.iterrows():
            ax.add_patch(Rectangle((row["onset"], yvalues(g)-0.35), row["duration"], 0.7, color=colors(g)))

    ax.set_yticks(range(1,13));
    ax.set_yticklabels(["change.null","change.other","change.future","change.acceptance","change.current","change.not",
                        "look.null","look.other","look.future","look.acceptance","look.current","look.not"]);


#     ax.set_title("Block Events");
    ax.set_xlim((0, 650));
    ax.set_ylim((0.25, 12.75));
    # Hide the right and top spines
    ax.spines[['right','top','bottom']].set_visible(False)

    #legend
    ax.add_patch(Rectangle((600, 10), 45, 0.7, color=colors("instruction")))
    plt.text(650, 10, 'instruction', horizontalalignment='left',verticalalignment='bottom')

    ax.add_patch(Rectangle((600, 9), 45, 0.7, color=colors("image")))
    plt.text(650, 9, 'image', horizontalalignment='left',verticalalignment='bottom')

    ax.add_patch(Rectangle((600, 8), 45, 0.7, color=colors("affectresp")))
    plt.text(650, 8, 'affectresp', horizontalalignment='left',verticalalignment='bottom')

    ax.add_patch(Rectangle((600, 7), 45, 0.7, color=colors("tacticresp")))
    plt.text(650, 7, 'tacticresp', horizontalalignment='left',verticalalignment='bottom')

    ax.add_patch(Rectangle((600, 6), 45, 0.7, color=colors("fixation")))
    plt.text(650, 6, 'fixation', horizontalalignment='left',verticalalignment='bottom')