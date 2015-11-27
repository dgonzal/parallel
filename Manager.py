#!/usr/bin/env python

from io_func import *
from batch_classes import *
from Inf_Classes import *

import os
import subprocess



class SubInfo(object):
    def __init__(self,name,numberOfFiles,data_type):
        self.name = name
        self.numberOfFiles =numberOfFiles #number of expected files
        self.data_type = data_type
        self.pid=[]
        self.rootFileCounter=0 #number of expected files 
        self.status = 0
	self.missingFiles = []

class JobManager(object):
    def __init__(self,options,header,workdir):
        self.header = header #how do I split stuff, sframe_batch header in xml file
        self.workdir = workdir #name of the workdir
        self.merge  = MergeManager(options.add,options.forceMerge,options.waitMerge)
        self.subInfo = [] #information about the submission status
        self.deadJobs = 0 #check if no file has been written to disk and nothing is on running on the batch
        self.totalFiles =0

    #read xml file and do the magic 
    def process_jobs(self,InputData,Job):
        for process in range(len(InputData)):
            processName = ([InputData[process].Version])
            self.subInfo.append(SubInfo(InputData[process].Version,write_all_xml(self.workdir+'/'+InputData[process].Version,processName,self.header,Job,self.workdir),InputData[process].Type))
            self.totalFiles += self.subInfo[process].numberOfFiles
            write_script(processName[0],self.workdir,self.header)

    #submit the jobs to the batch as array job
    #the used function should soon return the pid of the job for killing and knowing if something failed
    def submit_jobs(self):
        for process in self.subInfo:
            submit_qsub(process.numberOfFiles,self.workdir+'/Stream_'+str(process.name),str(process.name),self.workdir)
    #resubmit the jobs se above      
    def resubmit_jobs(self):
        proc_qstat = subprocess.Popen(['qstat'],stdout=subprocess.PIPE)
        qstat_out = proc_qstat.communicate()[0]
        if qstat_out:
            print '\n' + qstat_out
            res = raw_input('Some jobs are still running (see above). Do you really want to resubmit? Y/[N] ')
            if res.lower() != 'y':
                exit(0)
        for process in self.subInfo:
	    for it in process.missingFiles:
                resubmit(self.workdir+'/Stream_'+process.name,process.name+'_'+str(it),self.workdir,self.header)

    #see how many jobs finished, were copied to workdir or were merged 
    def check_jobstatus(self, OutputDirectory, nameOfCycle,remove = True):
        missing = open(self.workdir+'/missing_files.txt','w+')
        for i in xrange(len(self.subInfo)-1, -1, -1):
            process = self.subInfo[i]
            rootFiles =0
	    self.subInfo[i].missingFiles = []     
            for it in range(process.numberOfFiles):
                filename = OutputDirectory+'/'+self.workdir+'/'+nameOfCycle+'.'+process.data_type+'.'+process.name+'_'+str(it)+'.root'
                if not os.path.exists(filename) or os.stat(filename).st_mtime < 10:
                    missing.write(self.workdir+'/'+nameOfCycle+'.'+process.data_type+'.'+process.name+'_'+str(it)+'.root\n')
		    self.subInfo[i].missingFiles.append(it+1)		    
                else:
                    rootFiles+=1
            process.rootFileCounter=rootFiles
            if remove:
                if os.path.exists(OutputDirectory+'/'+nameOfCycle+'.'+process.data_type+'.'+process.name+'.root'):
                    del self.subInfo[i]
        missing.close()
                
    #print status of jobs 
    def print_status(self):
        print 'Status of unmerged files'
        print '%30s: %6s %6s %.6s'% ('Sample Name','Ready','#Files','[%]')
        for process in self.subInfo:
            print '%30s: %6i %6i %.3i'% (process.name, process.rootFileCounter,process.numberOfFiles, 100*process.rootFileCounter/float(process.numberOfFiles)), 'Done' if process.rootFileCounter == process.numberOfFiles else ''
        print 'Number of files expected: ',self.totalFiles
    #take care of merging
    def merge_files(self,OutputDirectory,nameOfCycle,InputData):
        self.merge.merge(OutputDirectory,nameOfCycle,self.subInfo,self.workdir,InputData)
    #wait for every process to finish
    def merge_wait(self):
        self.merge.wait_till_finished()
                               
class MergeManager(object):
    def __init__(self,add,force,wait):
        self.add = add
        self.force = force
        self.active_process=[]
        self.wait = wait
        
    def merge(self,OutputDirectory,nameOfCycle,info,workdir,InputData):
        if not self.add and not self.force: return  
        print "Don't worry your are using nice = 10 "
        OutputTreeName = ""
        for inputObj in InputData:
            for mylist in inputObj.io_list.other:
                if "OutputTree" in mylist:
                    OutputTreeName= mylist[2]
        for process in info:
            if not process.numberOfFiles == process.rootFileCounter:
                continue
            if not os.path.exists(OutputDirectory+'/'+nameOfCycle+'.'+process.data_type+'.'+process.name+'.root') or self.force:
                if process.status ==0:
                    self.active_process.append(add_histos(OutputDirectory,nameOfCycle+'.'+process.data_type+'.'+process.name,process.numberOfFiles,workdir,OutputTreeName))
                    process.status = 1
    
    def wait_till_finished(self):
        if not self.wait: return
        for process in self.active_process:
            if not process: continue
            if not process.poll():
                process.wait()
                #os.kill(process.pid,-9)
                
class pidWatcher(object):
    def __init__(pid):
        self.pid = pid
        
    def watch():
        proc_qstat = subprocess.Popen(['qstat -xml'],stdout=subprocess.PIPE)
        qstat_xml = proc_qstat.communicate()[0]
        
        return
