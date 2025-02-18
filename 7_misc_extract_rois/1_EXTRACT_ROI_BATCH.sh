#!/bin/bash
#
#SBATCH --job-name=extract_rois_feat
#SBATCH --qos=blanca-ics
#SBATCH --partition=blanca-ics
#SBATCH --account=blanca-ics
#SBATCH --time=6:00:00
#SBATCH --array=1-291
#SBATCH --output=logs/extract_rois_feat_%A_%a.out
#SBATCH --error=logs/extract_rois_feat_%A_%a.err
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

umask g+w

module use /projects/ics/modules
module load fsl/6.0.7

module load anaconda
conda activate incenv

maskfile=/path/to/atlas/gordon_plus_subcortical_347parcels_MNI152_2mm.nii
studypath=/path/to/analysis/feat/sub-*/ses-*

# get feat folder for analysis
session=`ls -d $studypath | sed -n "$SLURM_ARRAY_TASK_ID p"`

for infile in `ls $session/*.feat/reg_standard/stats/cope*.nii.gz` ; do
    python extract_roi_values_3D.py --infile $infile --maskfile $maskfile --count --percent
done
