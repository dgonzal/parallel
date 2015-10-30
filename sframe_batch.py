#!/usr/bin/env python
from optparse import OptionParser
from argparse import ArgumentParser
from xml.dom.minidom import parse, parseString
import xml.sax

import os
import sys
import shutil
import timeit
import StringIO
import subprocess
#import multiprocessing

#from hadd_helper import *
from io_func import *

if __name__ == "__main__":
    parser = OptionParser(usage="usage: %prog [options] filename",
                          version="%prog 0.2")
    parser.add_option("-w", "--workdir",
                      action="store",
                      dest="workdir",
                      default="",
                      help="Overwrite the place where to store overhead")
    parser.add_option("-s", "--submit",
                      action="store_true", # optional because action defaults to "store"
                      dest="submit",
                      default=False,
                      help="Submit Jobs to the grid")
    parser.add_option("-r", "--resubmit",
                      action="store_true", # optional because action defaults to "store"
                      dest="resubmit",
                      default=False,
                      help="Resubmit failed Jobs from missing_files.txt")
    parser.add_option("-l", "--loopCheck",
                      action="store_true", # optional because action defaults to "store"
                      dest="loop",
                      default=False,
                      help="Look which jobs finished and where transfered to your storage device. Creates the missing_files.txt")
    parser.add_option("-a", "--addFiles",
                     action="store_true",
                     dest="add",
                     default=False,
                     help="hadd files to one") 
    parser.add_option("-f", "--forceMerge",
                      action="store_true", # optional because action defaults to "store"
                      dest="forceMerge",
                      default=False,
                      help="Force to hadd the root files from the workdir into the ouput directory")
    """
    parser.add_option("-m","--multiMerge",
                      action="store",
                      dest="worker",
                      type=float,
                      default=0.3,
                      help="Define how many multiple processes are used to hadd the files. Combination with -a or -f needed. Default is to use 30% of the available workers.")
    """
    (options, args) = parser.parse_args()
    #print options
    #print args

    start = timeit.default_timer()
    if len(args) != 1:
        parser.error("wrong number of arguments help can be invoked with --help")
 
    xmlfile = args[0]
    if os.path.islink(xmlfile):
        xmlfile = os.path.abspath(os.readlink(xmlfile))

    # softlink JobConfig.dtd into current directory
    scriptpath = os.path.realpath(__file__)[:-15]
    if not os.path.exists('JobConfig.dtd'):
        os.system('ln -sf %s/JobConfig.dtd .' % scriptpath)

    #print xmlfile, os.getcwd
    proc_xmllint = subprocess.Popen(['xmllint','--noent',xmlfile],stdout=subprocess.PIPE)
    xmlfile_strio = StringIO.StringIO(proc_xmllint.communicate()[0])

    sax_parser = xml.sax.make_parser()
    xmlparsed = parse(xmlfile_strio,sax_parser)
    header = header(xmlfile)
        
    node = xmlparsed.getElementsByTagName('JobConfiguration')[0]
    Job = JobConfig(node)

    workdir = header.Workdir
    if options.workdir : workdir = options.workdir
    if not workdir : workdir="workdir"
    currentDir = os.getcwd()
   
    if not os.path.exists(workdir+'/'):
        os.makedirs(workdir+'/')
        print workdir,'has been created'
        shutil.copy(scriptpath+"JobConfig.dtd",workdir)
        shutil.copy(args[0],workdir)

    #print header.Version[0]
    names =[]
    data_type =[]
    NFiles = []
    active_process =[]

    for cycle in Job.Job_Cylce:
        if cycle.OutputDirectory.startswith('./'):             
            cycle.OutputDirectory = currentDir+cycle.OutputDirectory[1:]
        for process in range(len(cycle.Cycle_InputData)):
            processName = ([cycle.Cycle_InputData[process].Version])
            names.append(cycle.Cycle_InputData[process].Version)
            data_type.append(cycle.Cycle_InputData[process].Type)
            NFiles.append(write_all_xml(workdir+'/'+cycle.Cycle_InputData[process].Version,processName,header,Job,workdir))
            write_script(processName[0],workdir,header)
            if(options.submit):submit_qsub(NFiles[len(NFiles)-1],workdir+'/Stream_'+str(processName[0]),str(processName[0]),workdir)
            
        #get once into the loop for resubmission
        loop_check = True #options.loop
        resubmit_flag =options.resubmit

        if resubmit_flag:
            proc_qstat = subprocess.Popen(['qstat'],stdout=subprocess.PIPE)
            qstat_out = proc_qstat.communicate()[0]
            if qstat_out:
                print '\n' + qstat_out
                res = raw_input('Some jobs are still running (see above). Do you really want to resubmit? Y/[N] ')
                if res.lower() != 'y':
                    exit(0)

        print '%30s: %6s %6s %.6s'% ('Sample Name','#Files','Ready','[%]')

        while loop_check==True:   
            if len(names)==0 or not options.loop: 
                loop_check = False
            del_list =[]    
            tot_prog = 0
            missing = open(workdir+'/missing_files.txt','w+')
            i =0
            for name in names:
                rootCounter = 0                
                #print len(names),names[i]#,cycle.OutputDirectory
                for it in range(NFiles[i]):
                    nameOfCycle = cycle.Cyclename.replace('::','.')
                    if os.path.exists(cycle.OutputDirectory+'/'+workdir+'/'+nameOfCycle+'.'+data_type[i]+'.'+names[i]+'_'+str(it)+'.root'):
                        rootCounter +=1 
                    else:
                        missing.write(workdir+'/'+nameOfCycle+'.'+data_type[i]+'.'+names[i]+'_'+str(it)+'.root\n')
                        if resubmit_flag: resubmit(workdir+'/Stream_'+names[i],names[i]+'_'+str(it+1),workdir,header)
                tot_prog += rootCounter
                print '%30s: %6i %6i %.3i'% (names[i], rootCounter, NFiles[i], 100*rootCounter/float(NFiles[i])), 'Done' if rootCounter == NFiles[i] else ''
                if NFiles[i] == rootCounter: 
                    del_list.append(i)
                i+=1

            missing.close()
            resubmit_flag = 0
            del_list.sort(reverse=True)	
            if options.add or options.forceMerge:
                OutputTreeName = ""
                for inputObj in cycle.Cycle_InputData:
                    for mylist in inputObj.io_list:
                        if "OutputTree" in mylist:
                           OutputTreeName= mylist[2]
                for m in del_list:
                    nameOfCycle = cycle.Cyclename.replace('::','.')
                    if not  os.path.exists(cycle.OutputDirectory+'/'+nameOfCycle+'.'+data_type[m]+'.'+names[m]+'.root') or options.forceMerge:
                        active_process.append(add_histos(cycle.OutputDirectory,nameOfCycle+'.'+data_type[m]+'.'+names[m],NFiles[m],workdir,OutputTreeName))
                    del NFiles[m]
                    del names[m]
                    del data_type[m]

            #print 'Total progress', tot_prog
            print '-'*80
            if options.loop: time.sleep(30)
            if len(NFiles)==0: loop_check = False 
        
            
    if active_process: print'Using nice level 10 for subprocesses'
    for proc in active_process: 
        if proc:
            proc.wait()
            proc.kill()

    filesum =0
    for i in NFiles:
        filesum+=i
    if filesum!=0:
        print "Number of xml Files",filesum

    stop = timeit.default_timer()

    print "SFrame Batch was running for",round(stop - start,2),"sec" 
