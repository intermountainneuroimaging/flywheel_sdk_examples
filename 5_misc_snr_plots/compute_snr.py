
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
from support_functions import get_snr, plot_events
import scipy.ndimage as ndi
import argparse
from functools import partial

__version__ = "0.0.1"

# functions
def get_spacing(n_slice, n_subplots = 9):
    step_size = n_slice // n_subplots
    plot_range = n_subplots * step_size
    start_stop = int((n_slice - plot_range) / 2)

    return start_stop, plot_range, step_size


# main
files = glob.glob('/scratch/alpine/amhe4269/unipain/analysis/fmriprep/sub-*/ses-*/func/*_desc-confounds_timeseries.tsv')
colnames=['trans_x', 'trans_x_derivative1', 'trans_x_derivative1_power2', 'trans_x_power2', 'trans_y', 'trans_y_derivative1', 'trans_y_power2', 'trans_y_derivative1_power2', 'trans_z', 'trans_z_derivative1', 'trans_z_power2', 'trans_z_derivative1_power2', 'rot_x', 'rot_x_derivative1', 'rot_x_power2', 'rot_x_derivative1_power2', 'rot_y', 'rot_y_derivative1', 'rot_y_derivative1_power2', 'rot_y_power2', 'rot_z', 'rot_z_derivative1', 'rot_z_power2', 'rot_z_derivative1_power2', 'a_comp_cor_00', 'a_comp_cor_01', 'a_comp_cor_02', 'a_comp_cor_03', 'a_comp_cor_04', 'a_comp_cor_05', '^motion_outlier[a-zA-Z0-9]*$']


def main(fmri_file, confounds_file, mask_file, dummyVols, tsnr_threshold):
    
    # convert from PosixPath to string (more generic handeling)
    fmri_file = str(fmri_file)
    confounds_file = str(confounds_file)
    mask_file = str(mask_file)
    # log inputs...
    print("Using file: "+fmri_file)
    print("Using file: "+confounds_file)
    print("Using file: "+mask_file)
    
    # load confounds file to memory
    confounds = pd.read_csv(confounds_file, sep='\t').fillna(value = 0)

    row = {
        "subject": "_".join([a for a in Path(confounds_file).name.split(".")[0].split("_") if any(b in a for b in ["sub-"])]), 
        "session": "_".join([a for a in Path(confounds_file).name.split(".")[0].split("_") if any(b in a for b in ["ses-"])]), 
        "acq": "_".join([a for a in Path(confounds_file).name.split(".")[0].split("_") if any(b in a for b in ["task-","acq-","rec-","dir-","run-","echo-","part-","chunk-"])]), 
        "outlier_count": sum('motion_outlier' in s for s in confounds.columns), 
        "dvars_count": sum(confounds["std_dvars"] > 1.5), 
        "fd_count": sum(confounds["framewise_displacement"] > 0.5),
        "nvols": len(confounds["framewise_displacement"]),
        "perc": sum('motion_outlier' in s for s in confounds.columns) / len(confounds["framewise_displacement"]) * 100,
        "filename": confounds_file
    }

        
    subject=row["subject"]
    session=row["session"]
    acq=row["acq"]
    # ------------------------------
    
    # don't rerun if file already exists...
    if os.path.exists("snr_plots/"+subject+"_"+session+"_"+acq+"_max"+str(tsnr_threshold)+"_qc.png"):
        print("SNR plot already exists... exiting.")
#         return

    # trim confounds data to remove non-steady state volumes
    confounds = confounds[dummyVols:]
    
    # compute snr and global signal (within mask)
    tsnr_img, img, global_signal, tr = get_snr(fmri_file, mask_file, dummyVols)

    # ----- plots ---- #

    # graph some exemplar sessions
    allplot = plt.figure(figsize=(12, 10))
    
    # Add a title to the figure
    allplot.suptitle(os.path.basename(fmri_file),color='w')
    
    
    ax1 = allplot.add_axes((0.15, 0.50, 0.7, 0.1))
    y=confounds["std_dvars"]
    time = np.linspace(0, len(y) * tr, len(y))
    ax1.plot(time, y, linewidth=0.5)
    plt.axhline(y = 1.5,linewidth=0.5, color = 'grey', linestyle = '--');
    ax1.set_ylabel("std_dvars")
    ax1.set_xlim([0, len(y) * tr])
    ax1.spines['right'].set_visible(False)
    ax1.spines['top'].set_visible(False)

    ax2 = allplot.add_axes((0.15, 0.35, 0.7, 0.1))
    y=confounds["framewise_displacement"]
    time = np.linspace(0, len(y) * tr, len(y))
    ax2.plot(time, y, linewidth=0.5,color='coral')
    plt.axhline(y = 0.5, linewidth=0.5, color = 'grey', linestyle = '--');
    # plt.axhline(y = 0.2, color = 'grey', linestyle = '--');
    ax2.set_ylabel("fd")
    ax2.set_xlim([0, len(y) * tr])
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)

    ax3 = allplot.add_axes((0.15, 0.20, 0.7, 0.1))
    y=global_signal
    time = np.linspace(0, len(y) * tr, len(y))
    ax3.plot(time, global_signal, linewidth=0.5,color='slategrey')
    ax3.set_xlabel("seconds")
    ax3.set_xlim([0, len(y) * tr])
    ax3.set_ylabel("global_signal")
    ax3.spines['right'].set_visible(False)
    ax3.spines['top'].set_visible(False)

    ax = allplot.add_axes([0.05, 0.625, 0.9, 0.375])
    ax.set_facecolor('black')
    ax.axis('off')
    ax.add_patch(plt.Rectangle((0,0), 1, 1, facecolor='k',
                           transform=ax.transAxes, zorder=-1))
    
    #first column
    array = tsnr_img.get_fdata()
    tsnrmean = np.mean(array[array>0])
    tsnrmax = np.max(array[array>0])
    array[array>tsnr_threshold] = tsnr_threshold
 
    tmpdata_dropx = array[~np.all(array == 0, axis=(1, 2)),:,:]   # Check for non-zero slices along axis 0 (first axis)
    
    tmpdata_dropy = array[:,~np.all(array == 0, axis=(0, 2)),:]   # Check for non-zero slices along axis 1 (second axis)
    
    tmpdata_dropz = array[:,:,~np.all(array == 0, axis=(0, 1))]  # Check for non-zero slices along axis 2 (third axis)
    
    a, b, c = get_spacing(tmpdata_dropx.shape[0], n_subplots = 9)
    for idx, x in enumerate(range(a, b, c)):
        ax = allplot.add_axes([0.05+0.1*idx, 0.625, 0.1, 0.1])
        ax.imshow(ndi.rotate(tmpdata_dropx[x, :, :], 90), cmap='nipy_spectral', vmin=30, vmax=tsnr_threshold+5)
        ax.axis('off')
    
    a, b, c = get_spacing(tmpdata_dropz.shape[2], n_subplots = 9)
    for idx, z in enumerate(range(a, b, c)):
        ax = allplot.add_axes([0.05+0.1*idx, 0.725, 0.1, 0.15])
        ax.imshow(ndi.rotate(tmpdata_dropz[:, :, z], 90), cmap='nipy_spectral', vmin=30, vmax=tsnr_threshold+5)
        ax.axis('off')
    
    a, b, c = get_spacing(tmpdata_dropy.shape[1], n_subplots = 9)
    for idx, y in enumerate(range(a, b, c)):
        ax = allplot.add_axes([0.05+0.1*idx, 0.875, 0.1, 0.1])
        ax.imshow(ndi.rotate(tmpdata_dropy[:, y, :], 90), cmap='nipy_spectral', vmin=30, vmax=tsnr_threshold+5)
        ax.axis('off')

    ax5 = allplot.add_axes((0.15, 0.005, 0.7, 0.135))
    plotting.plot_carpet(
        img,
        t_r=tr,
        axes=ax5,
    )
    plt.axis('off');
    
    row["tsnr_mean"] = tsnrmean
    row["tsnr_max"] = tsnrmax
    row["globalsignal"] = np.mean(global_signal)
    
    allplot.text(0.05, 0.6275, 'SNR: threshold = '+str(tsnr_threshold)+"; mean: "+"{:.{}f}".format(tsnrmean, 2)+"; max: "+"{:.{}f}".format(tsnrmax, 2), ha='left', color='w')

    os.makedirs("snr_plots", exist_ok = True)
    plt.savefig("snr_plots/"+subject+"_"+session+"_"+acq+"_max"+str(tsnr_threshold)+"_qc.png")
    plt.close(allplot) 

    df = pd.DataFrame.from_dict(row, orient="index")
    df.to_csv("snr_plots/"+subject+"_"+session+"_"+acq+"_metrics.csv",index=False)
    
    return


def parser(context):
    
    parser = argparse.ArgumentParser(
        description="Script applies nuisance regression to preprocessed fMRI dataset.",
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
        "fmri_file",
        action="store",
        metavar="fMRIFILE.nii.gz",
        type=IsFile,
        help="file path to fmri file used to apply nuisance regression."
    )

    parser.add_argument(
        "confounds_file",
        action="store",
        metavar="CONFOUNDSFILE.tsv",
        type=IsFile,
        help="Confounds file generated for accompanying fMRI file. File should in fmriprep output format and naming."
    )
    
    parser.add_argument(
        "mask_file",
        action="store",
        metavar="MASKFILE.nii.gz",
        type=IsFile,
        help="Binary mask file."
    )
    
    ##########################
    #     Named Arguments    #
    ##########################
    
    parser.add_argument(
        "--dummyVols",
        action="store",
        metavar="NUMBER OF FRAMES",
        type=int,
        default=0, 
        help="(Default: 0) Number of non-steady state frames to remove before computing SNR."
    )

    parser.add_argument(
        "--tsnr_threshold",
        action="store",
        metavar="SNR THRESHOLD",
        type=int,
        default=100, 
        help="Default: 100"
    )
    
    
    args = parser.parse_args()

    # add all args to context
    args_dict = args.__dict__
    context.update(args_dict)
    


if __name__ == "__main__":

    # Welcome message
    welcome_str = '{} {}'.format('compute_snr.py ', __version__)
    welcome_decor = '=' * len(welcome_str)
    print('\n{}\n{}\n{}'.format(welcome_decor, welcome_str, welcome_decor))

    # run main
    pycontext = dict()
    parser(pycontext)

    main(pycontext["fmri_file"], pycontext["confounds_file"], pycontext["mask_file"], pycontext["dummyVols"], pycontext["tsnr_threshold"] )
    
    
