#!/usr/bin/env python

from subprocess import call
from subprocess import Popen
import os

from tree_checker import *
# from fhadd import fhadd


def write_script(name,workdir,header):
    myfile = open(workdir+'/split_script_'+name+'.sh','w')
    
    myfile.write(
    """#!/bin/bash

##This is a simple example of a SGE batch script
##Use home server with scientific linux 6 
#$ -l os=sld6 
#$ -l site=hh 
#$ -cwd
##You need to set up sframe
#$ -V 
##email Notification
#$ -m """+header.Notification+"""
#$ -M """+header.Mail+"""
##running in local mode with 8-12 cpu slots
##$ -pe local 8-12
##CPU memory
#$ -l h_vmem="""+header.RAM+"""G
##DISK memory
#$ -l h_fsize="""+header.DISK+"""G   
cd """+workdir+"""
sframe_main """+name+"""_${SGE_TASK_ID}.xml
""")
    
    myfile.close()


def resub_script(name,workdir,header):
    myfile = open(workdir+'/split_script_'+name+'.sh','w')
    
    myfile.write(
    """#!/bin/bash

##This is a simple example of a SGE batch script
##Use home server with scientific linux 6 
#$ -l os=sld6 
#$ -l site=hh 
#$ -cwd
##You need to set up sframe
#$ -V 
##email Notification
#$ -m """+header.Notification+"""
#$ -M """+header.Mail+"""
##running in local mode with 8-12 cpu slots
##$ -pe local 8-12
##CPU memory
#$ -l h_vmem="""+header.RAM+"""G
##DISK memory
#$ -l h_fsize="""+header.DISK+"""G   
cd """+workdir+"""
sframe_main """+name+""".xml

""")    
    myfile.close()



def submit_qsub(NFiles,Stream,name,workdir):
    #print '-t 1-'+str(int(NFiles))
    #call(['ls','-l'], shell=True)

    if not os.path.exists(Stream):
        os.makedirs(Stream)
        print Stream+' has been created'
 
    call(['qsub'+' -t 1-'+str(NFiles)+' -o '+Stream+'/'+' -e '+Stream+'/'+' '+workdir+'/split_script_'+name+'.sh'], shell=True)

def resubmit(Stream,name,workdir,header):
    #print Stream ,name
    resub_script(name,workdir,header)	
    if not os.path.exists(Stream):
        os.makedirs(Stream)
        print Stream+' has been created'
 
    call(['qsub'+' -o '+Stream+'/'+' -e '+Stream+'/'+' '+workdir+'/split_script_'+name+'.sh'], shell=True)


def add_histos(directory,name,NFiles,workdir,outputTree) :
    
    if os.path.exists(directory+name+'.root'):
        call(['rm '+directory+name+'.root'], shell=True)
    string =" "
    fileContainer=[]
    proc = None
    for i in range(NFiles):
        if(outputTree):
            if not check_TreeExists(directory+workdir+'/'+name+'_'+str(i)+'.root',outputTree):
                continue
        string += directory+workdir+'/'+name+'_'+str(i)+'.root'
        string += " "
        fileContainer.append(directory+workdir+'/'+name+'_'+str(i)+'.root')

    #print string
    if not string.isspace():
        #fhadd(directory+name+'.root',fileContainer,"TH1")
        print 'Merging',name+'.root'
        proc = Popen(['nice -n 10 hadd '+'-v 1 '+directory+name+'.root'+string], shell=True)
    else:
        print 'Nothing to merge for',name+'.root'
    return proc 
