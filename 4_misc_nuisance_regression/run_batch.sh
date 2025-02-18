#!/bin/bash
#
#SBATCH --job-name=nuisance_regression
#SBATCH --qos=blanca-ics
#SBATCH --partition=blanca-ics
#SBATCH --account=blanca-ics
#SBATCH --time=02:00:00
#SBATCH --array=1-100
#SBATCH --output=logs/nuisance_regression_%A_%a.out
#SBATCH --error=logs/nuisance_regression_%A_%a.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

umask g+w

module load anaconda
conda activate incenv

# controls the operation of bash array...
master_spreadsheet='<path-to-file>'


while IFS=',' read -r fmri_file confound_file mask_file; do
  if [ "$i" -eq "$SLURM_ARRAY_TASK_ID" ]; then
    echo "Running Analysis for: " "$fmri_file"
    break
  fi
  ((i++))
done < $master_spreadsheet


cmd="python apply_nuisance_regression.py ${fmri_file} ${confound_file} ${mask_file}"

echo $cmd
$cmd
