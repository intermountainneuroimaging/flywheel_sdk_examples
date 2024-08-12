#!/bin/bash
#SBATCH --job-name=fw-download
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --nodes=1
#SBATCH --output log.txt
#SBATCH --partition=blanca-ics
#SBATCH --qos=blanca-ics
#SBATCH --account=blanca-ics
#SBATCH --time=600
#SBATCH --export=NONE

module load anaconda
conda activate flywheel

python download_from_analysis_table.py --analysis-table [TABLE-FILE] --download-path [PATH]
