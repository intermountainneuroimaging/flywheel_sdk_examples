"""Main module."""

import logging
import os
from pathlib import Path
import numpy as np
import pandas as pd
import nibabel as nib

import argparse

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

import psutil
import os
import time

# Function to log memory usage
def log_memory_usage(step=""):
    # Get the memory info of the current process
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    rss_memory = memory_info.rss / (1024 ** 2)  # Convert from bytes to MB
    vms_memory = memory_info.vms / (1024 ** 2)  # Virtual memory in MB
    
    log.info(f"Memory usage after {step}:")
    log.info(f"  RSS (Resident Set Size) Memory: {rss_memory:.2f} MB")
    log.info(f"  VMS (Virtual Memory Size): {vms_memory:.2f} MB")
    log.info("-" * 40)
    
    
def main(context):
    
    # load input file
    img = nib.load(context["infile"])
    fdata = img.get_fdata()
    log_memory_usage(step="Loaded input cope.")
    
    # load mask file
    mask = nib.load(context["maskfile"])
    mdata = mask.get_fdata()
    log_memory_usage(step="Loaded mask cope.")
    
    # identify number of ids in mask
    unq = np.unique(mdata)
    unq = unq[unq != 0]
    
    log.info("Extracting values from : %s", context["infile"])
    log.info("Apply %s regions of interest from: %s", str(len(unq)), context["maskfile"])
    
    mean, count, percent, colnames = compute(fdata, mdata, unq)
    
    path = Path(context["infile"]); outfile = path
    
    for method in context["methods"]:
    
        outfile = os.path.join(path.parent, strip_suffix(path.name) + "."+strip_suffix(Path(context["maskfile"]).name)+ "." + method + ".csv")
        df = pd.DataFrame(data=locals()[method], columns=colnames)
            
        # store outputs
        log.info("Saving Extracted values (aggregated by %s): %s", method, str(outfile))
        
        df.to_csv(outfile,float_format='%.3f', index=None)

        
def strip_suffix(filename):
    suffix = [".nii.gz", ".nii", ".img"]
    for s in suffix:
        filename = filename.replace(s,"")
    return filename
           
    
def compute(fdata, mdata, mvalues):
    arr_mean = np.zeros([1,len(mvalues)])
    arr_count = np.zeros([1,len(mvalues)])
    arr_percent = np.zeros([1,len(mvalues)])
    print(arr_mean.shape)
    
    log_memory_usage(step="intialized computations... ")
    
    #set column names
    colnames=[]
    for idx, m in enumerate(mvalues):
        colnames.append("roi."+str(int(m)).zfill(2))
        itrm = np.where(mdata == m, 1, 0)
        a = fdata*itrm
        non_zero_elements = a[np.nonzero(a)]
        arr_mean[0,idx] = np.mean(non_zero_elements) 
        arr_count[0,idx] = np.count_nonzero(non_zero_elements)
        arr_percent[0,idx] = np.count_nonzero(non_zero_elements) / np.count_nonzero(itrm) * 100
        if idx/10 == 0:
            log_memory_usage(step="computation loop... ")
    
    return arr_mean, arr_count, arr_percent, colnames


def parser(context):
    
    parser = argparse.ArgumentParser(
        description="""Extract values from input dataset from a suppied atlas. Store all outputs in a csv file.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    ##########################
    #   Required Arguments   #
    ##########################
    parser.add_argument(
        "--infile",
        action="store",
        metavar="INPUT PATH",
        type=str,
        help="Path to 4D input file containing values for extraction"
    )
    
    parser.add_argument(
        "--maskfile",
        action="store",
        metavar="MASK",
        type=str,
        help="Path to 3D/4D mask or atlas for extraction"
    )
    
    parser.add_argument(
        '--count', 
        action='store_true', 
        default=True,
        help="Additional method to aggregate across values within mask. Mean of all voxels is applied by default. Additional method to count voxels in mask added by flag."
    )
    
    parser.add_argument(
        '--percent', 
        action='store_true', 
        default=True,
        help="Additional method to aggregate across values within mask. Mean of all voxels is applied by default. Additional method to compute percent of usable voxels in mask added by flag."
    )

    args = parser.parse_args()

    # add all args to context
    args_dict = args.__dict__
    context.update(args_dict)
    
    if not os.path.exists(context["infile"]):
        log.error("Error in input file path.")
    
    if not os.path.exists(context["maskfile"]):
        log.error("Error in mask file path.")
        
    # record methods for analysis
    methods = ["mean"]
    if "count" in context:
        methods.append("count")
        
    if "percent" in context:
        methods.append("percent")
    context["methods"] = methods
        
    
if __name__ == "__main__":
    
    # parse user inputs and store in context
    context = dict()
    parser(context)
    
    main(context)

    
    
    