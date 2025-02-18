#!/bin/bash
#
#SBATCH --job-name=compute_snr
#SBATCH --qos=blanca-ics
#SBATCH --partition=blanca-ics
#SBATCH --account=blanca-ics
#SBATCH --time=02:00:00
#SBATCH --array=1-100
#SBATCH --output=logs/compute_snr_%A_%a.out
#SBATCH --error=logs/compute_snr_%A_%a.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

umask g+w

module load anaconda
conda activate incenv

# controls the operation of bash array...
master_spreadsheet='<path-to-file>'
dummyVols=0;
tsnr_threshold=125; 


while IFS=',' read -r fmri_file confound_file mask_file; do
  if [ "$i" -eq "$SLURM_ARRAY_TASK_ID" ]; then
    echo "Running Analysis for: " "$fmri_file"
    break
  fi
  ((i++))
done < $master_spreadsheet


cmd="python compute_snr.py ${fmri_file} ${confound_file} ${mask_file} --dummyVols ${dummyVols} --tsnr_threshold ${tsnr_threshold}"

echo $cmd
$cmd
