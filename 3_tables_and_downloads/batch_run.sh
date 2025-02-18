#!/bin/bash
#SBATCH --job-name=fw-download
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --nodes=1
#SBATCH --output log.txt
#SBATCH --partition=amilan
#SBATCH --qos=normal
#SBATCH --account=ucb278_asc3
#SBATCH --time=1440
#SBATCH --export=NONE

module load anaconda
conda activate flywheel

python download_analysis_by_id.py 
