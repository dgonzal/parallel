#!/usr/bin/env python

import sys
import subprocess

gridconfig_base = """

[global]
backend = condor
task = UserTask          
workdir       = /nfs/dust/cms/user/garbersc/forBaconJets/workdirs/
duration= -1

[workflow]
report = GUIReport

[jobs]
memory = 8000 ; this is not tuned
jobs = 5                 ; Submit script two times
wall time = 24:00              
in flight = -1  
max retry = 5
in queue = 1500
monitor job = dashboard
continous = True

[UserTask]
executable = /nfs/dust/cms/user/garbersc/UHH2_17/SFrame/bin/sframe_main ; Name of the script
;arguments = @XML_NR@.xml ; Arguments for the executable
files per job = 1
dataset provider = scan                  ; change default dataset provider to "scan"
;dataset =  %s/*.xml      ; list of directories to scan for files
;se path = %s
se output files = *.root
se output pattern = JOB_OUTPUT_@GC_JOBID@_@X@
"""
# ;[parameters]
# ;parameters   = XML_NR
# ;XML_NR =
# """


class gridstart(object):
    def __init__(self, workdir, outdir, currentdir):  # , xml_base, n_xml):
        gridconfig = gridconfig_base
        with open("temp.conf", 'w') as file_:
            file_.write(gridconfig)
        print "grid-control config was written, starting grid-control..."

        if 'Settings' in locals():
            raise Exception(
                'This file is supposed to be run directly by python - not by go.py!')
        try:
            from grid_control_api import gc_create_config, gc_create_workflow
        except ImportError:
            raise Exception('grid-control is not correctly installed ' +
                            'or the gc package directory is not part of the PYTHONPATH.')
        from grid_control.utils import abort

        gcconfig = gc_create_config(
            config_file="temp.conf",
            config_dict={'global':
                         {'workdir': '/nfs/dust/cms/user/garbersc/forBaconJets/workdirs/' + workdir},
                         'UserTask':
                         {'dataset': currentdir + "/" + workdir + "/*.xml"},
                         'storage': {'se path': outdir + "/" + workdir, }
                         }
        )
        workflow = gc_create_workflow(gcconfig)
        workflow.run()
        abort(False)
        print "grid-control was closed"
