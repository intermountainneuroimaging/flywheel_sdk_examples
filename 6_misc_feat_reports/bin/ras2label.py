#!/projects/ics/software/anaconda/envs/incenv/bin/python3

# temp first for pandas import warnings
import warnings
warnings.filterwarnings("ignore")

import xml.etree.ElementTree as ET 
import nilearn.datasets, nilearn.image
from nibabel.affines import apply_affine
import pandas as pd
import numpy as np
import os
import sys

os.environ["FSLDIR"] = '/projects/ics/software/fsl/6.0.7'

__doc__ = """What this file does"""

def ras2label_HarvardOxfordCortical(x,y,z):
    atlas=nilearn.image.load_img(os.environ["FSLDIR"]+'/data/atlases/HarvardOxford/HarvardOxford-cort-maxprob-thr25-1mm.nii.gz')
    ras2vox = np.linalg.inv(atlas.affine)
    vox = apply_affine(ras2vox, [x,y,z]).astype(int)
    value = atlas.get_fdata()[vox[0],vox[1],vox[2]].astype(int)
    tree = ET.parse(os.environ["FSLDIR"]+'/data/atlases/HarvardOxford-Cortical.xml')
    elem = tree.find('.//data/label[@index="'+str(value-1)+'"]')  # note - indexing starts at zero but maxprob atlas counter starts at 1
    return elem.text if elem is not None else None

def ras2label_HarvardOxfordSubCortical(x,y,z):
    atlas=nilearn.image.load_img(os.environ["FSLDIR"]+'/data/atlases/HarvardOxford/HarvardOxford-sub-maxprob-thr25-1mm.nii.gz')
    ras2vox = np.linalg.inv(atlas.affine)
    vox = apply_affine(ras2vox, [x,y,z]).astype(int)
    value = atlas.get_fdata()[vox[0],vox[1],vox[2]].astype(int)
    tree = ET.parse(os.environ["FSLDIR"]+'/data/atlases/HarvardOxford-Subcortical.xml')
    elem = tree.find('.//data/label[@index="'+str(value-1)+'"]')  # note - indexing starts at zero but maxprob atlas counter starts at 1
    return elem.text if elem is not None else None

def ras2label_Talairach(x,y,z):
    atlas=nilearn.image.load_img(os.environ["FSLDIR"]+'/data/atlases/Talairach/Talairach-labels-1mm.nii.gz')
    ras2vox = np.linalg.inv(atlas.affine)
    vox = apply_affine(ras2vox, [x,y,z]).astype(int)
    value = atlas.get_fdata()[vox[0],vox[1],vox[2]].astype(int)
    tree = ET.parse(os.environ["FSLDIR"]+'/data/atlases/Talairach.xml')
    elem = tree.find('.//data/label[@index="'+str(value)+'"]')  # note - indexing starts at 1 - no offset needed
    return elem.text if elem is not None else None

if __name__ == "__main__":
    x = int(sys.argv[1])
    y = int(sys.argv[2])
    z = int(sys.argv[3])
    atlas=sys.argv[4]
    if atlas == "HO_cort":
        print(str(ras2label_HarvardOxfordCortical(x,y,z)))
    if atlas == "HO_sub":
        print(str(ras2label_HarvardOxfordSubCortical(x,y,z)))
    else:
        print(str(ras2label_Talairach(x,y,z)))
    
