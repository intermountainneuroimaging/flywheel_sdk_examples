# Welcome to INC’s Example Jupyter Notebooks!

Contained in this repo are several example code snippets to work with neuroimaging data stored in Flyhweel.io data management platform or standalone. We use Flywheel.io Python [SDK](https://flywheel-io.gitlab.io/product/backend/sdk/index.html) to showcase common tasks that can be scripted for data management and data analysis.

## How to Get Started
The accompanying notebooks rely on Python >=3.9 and several publicly available python packages:
- Flywheel-sdk
- seaborn
- sklearn
- Nibabel
- Nilearn 
- jupyter

1. We highly recommend using a conda environment to install python and relevant python packages.
Start by creating a new environment with desired base python version...
```
conda create -n examples python=3.11
```
Install requirements for this repo...
```
pip install -e requirements
```

2. You will also need to install the Flywheel.io CLI. Follow instructions here to install Flywheel CLI. ([Link](https://docs.flywheel.io/CLI/))


__IF you are a CU Boulder user with access to PetaLibrary, skip steps 1 and 2. Instead you can use an already created conda environment for `ics` users.__

  - Follow instructions here to update condarc file, and activate conda ‘incenv’

3. All users should log into the flywheel CLI to store their Flywheel credentials on the working machine ([here](https://docs.flywheel.io/CLI/start/install/#step-4-log-in-from-the-cli))

4. Finally, create a Jupyter kernel for the conda environment so you can use jupyterlab to run example notebooks.

That’s it! You are ready to get started!

## Why Use Flywheel SDK in Python? 
SDK are pre-built functions we can use to easily interact with a third party software like Flywheel. Flywheel is an efficient data management platform that promotes flexibility in data storage in analysis. In many circumstances we may need to perform repetitive actions within flywheel like running the same gears for all sessions in a project. These repetitive actions are the perfect opportunity for scripting to improve the speed and accuracy of our actions. 
Here are a couple common use cases we have seen at INC:
1. Rename the labels for all acquisitions in a project to meet a reproin naming convention
2. Run the same gears for every session in a project. When gears depend on one another, hold execution until prerequisite gears have completed successfully
3. Locate metadata for a project and extract for flexible reporting and data visualization 

This is just a small list of tasks you can accomplish using scripting with Flywheel. For more ideas and details about Flywheel SDK functions, visit their documentation here.

## Introduction to Flywheel SDK 
Start with Flywheel’s examples and basics ([here](https://flywheel-io.gitlab.io/product/backend/sdk/tags/20.0.0/python/getting_started.html#)). Once you are comfortable with the example section of Flywheel’s documentation, you are ready to get started with our example notebooks!

## Flywheel Data Object IDs
A key cornerstone of Flywheel’s data management platform is the use of object storage. Each data object and “container” are identifiable by a single persistent identifier. We can use Flywheel sdk functions to locate containers by it’s id. 

As an example, say I have a subject-101 in a project ’sandbox’. I can   interact with that container using the flywheel sdk by either:
1. Locating by ‘path’ fw.lookup(‘ics/sandbox/sub-101’)
2. Locating by id fw.get_container(‘<id>’)

Both options return a ‘subject’ container object that we can use to complete any available actions such as:
- renaming the subject label 
fw.update()
- Upload a file stored in the subject
- fw.upload_file
- Other ideas….

Understanding the cornerstone feature of object persistent identifiers makes your work with the Flywheel SDK quick and easy!

## Examples In Repo
We have provided 8 example tasks using Flywheel SDK in Python (and standalone workflows).
1. Metadata and curator
2. Run AutoWorkflow
3. Analysis Tables and Downloads
4. …

## Looking for More!
Check out some of the other useful resources:
- flywheel gitlab hierarchy curator examples ([here](https://gitlab.com/flywheel-io/scientific-solutions/gears/hierarchy-curator/-/tree/main/examples?ref_type=heads))
- INC's gethub repository with custom flywheel gears ([here](https://github.com/intermountainneuroimaging)),
- INC's flanker tutorial ([here](https://github.com/intermountainneuroimaging/flanker-tutorial))


## To Come! Hierarchy Curator Examples!
Looking to integrate some of your Flywheel SDK scripts into Flywheel? Consider using the Hierarchy Curator.

Hierarchy Curator Examples!



