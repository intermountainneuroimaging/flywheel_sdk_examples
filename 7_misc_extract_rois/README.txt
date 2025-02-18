# Methods to Extract values from 3D nifti using ROI boundaries

# USE THIS METHOD!

# Step 1: generate contrast specific csv files for all *.feat models
sbatch 1_EXTRACT_ROI_BATCH.sh

# Step 2: combine results to one master spreadsheet
source 2_COMBINE_OUTPUTS.txt