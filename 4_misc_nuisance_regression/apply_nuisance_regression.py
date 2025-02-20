import os, sys
import numpy as np
import pandas as pd
import nibabel as nib
from sklearn.linear_model import LinearRegression
from nilearn import image, masking
from sklearn.preprocessing import StandardScaler
import argparse
from functools import partial

# add performance timer
import time
start_time = time.perf_counter()

def main(fmri_file, confounds_file, mask_file):

    print("Using file: "+fmri_file)
    img = image.load_img(fmri_file)
    
    print("Using file: "+confounds_file)
    data = pd.read_csv(confounds_file, sep='\t').fillna(value = 0)

    print("Using file: "+mask_file)
    mask = image.load_img(mask_file)

    img_2d = masking.apply_mask(img, mask)


    # Step 2: Nuisance Regression (Using Linear Regression)

    columns_to_select = [ 'trans_x', 'trans_x_derivative1', 'trans_x_derivative1_power2', 'trans_x_power2', 'trans_y', 'trans_y_derivative1', 'trans_y_power2', 'trans_y_derivative1_power2', 'trans_z', 'trans_z_derivative1', 'trans_z_power2', 'trans_z_derivative1_power2', 'rot_x', 'rot_x_derivative1', 'rot_x_power2', 'rot_x_derivative1_power2', 'rot_y', 'rot_y_derivative1', 'rot_y_derivative1_power2', 'rot_y_power2', 'rot_z', 'rot_z_derivative1', 'rot_z_power2', 'rot_z_derivative1_power2', 'a_comp_cor_00', 'a_comp_cor_01', 'a_comp_cor_02', 'a_comp_cor_03', 'a_comp_cor_04', 'a_comp_cor_05']

    # Standardize nuisance variables
    scaler = StandardScaler()
    nuisance_vars_scaled = scaler.fit_transform(data[columns_to_select])

    # Fit the regression model
    regressor = LinearRegression()
    nuisance_regressed_data = np.zeros_like(img_2d)

    for voxel in range(img_2d.shape[1]):
        voxel_time_series = img_2d[:, voxel]
        regressor.fit(nuisance_vars_scaled, voxel_time_series)
        nuisance_regressed_data[:, voxel] = voxel_time_series - regressor.predict(nuisance_vars_scaled)

    # add back the mean value (dropped in regression)
    nuisance_regressed_data += img_2d.mean(axis=0)

    # Step 3: Reshape back to the 3D volume
    cleaned_fmri_img = masking.unmask(nuisance_regressed_data, mask_img=mask)
    nib.save(cleaned_fmri_img, fmri_file.replace('_bold.nii.gz','nr_bold.nii.gz'))
    print("Saved file: "+fmri_file.replace('_bold.nii.gz','nr_bold.nii.gz'))


    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time} seconds")
    
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
    
    args = parser.parse_args()

    # add all args to context
    args_dict = args.__dict__
    context.update(args_dict)
    


if __name__ == "__main__":

    # Welcome message
    welcome_str = '{} {}'.format('apply_nuisance_regression.py ', __version__)
    welcome_decor = '=' * len(welcome_str)
    log.info('\n{}\n{}\n{}'.format(welcome_decor, welcome_str, welcome_decor))

    # run main
    pycontext = dict()
    parser(pycontext)

    main(pycontext["fmri_file"], pycontext["confounds_file"], pycontext["mask_file"])
