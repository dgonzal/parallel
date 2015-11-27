#!/usr/bin/env python

#python classes
#import xml.dom.minidom

#import glob
#import getopt

from xml.dom.minidom import parse, parseString
from xml.dom.minidom import Document
import xml.sax

import math
import time
import ROOT

#my classes
from Inf_Classes import *
from batch_classes import *

def write_job(Job,Version=-1,SkipEvents=0,MaxEvents=-1,NFile=None, FileSplit=-1,workdir="workdir",LumiWeight=1):
    doc = Document()
    root = doc.createElement("JobConfiguration")
    root.setAttribute( 'JobName', Job.JobName)
    root.setAttribute( 'OutputLevel', Job.OutputLevel)
    
    for lib in Job.Libs:
        # Create Element
        tempChild = doc.createElement('Library')
        root.appendChild(tempChild)
        # Set Attr.
        tempChild.setAttribute( 'Name', lib)
    
    for pack in Job.Packs:
        # Create Element
        tempChild = doc.createElement('Package')
        root.appendChild(tempChild)
        # Set Attr.
        tempChild.setAttribute( 'Name', pack)
        
    for cycle in Job.Job_Cylce:
        # Create Element
        tempChild = doc.createElement('Cycle')
        root.appendChild(tempChild)
        # Set Attr.
        tempChild.setAttribute( 'Name', cycle.Cyclename)
        if not os.path.exists(cycle.OutputDirectory+workdir+'/'):
            os.makedirs(cycle.OutputDirectory+workdir+'/')
        tempChild.setAttribute('OutputDirectory', cycle.OutputDirectory+workdir+'/')
        tempChild.setAttribute('PostFix', cycle.PostFix+'_'+str(NFile))
        tempChild.setAttribute('TargetLumi', cycle.TargetLumi)
        
        for p in range(len(cycle.Cycle_InputData)):
            version_check = True
            if(Version!=-1): 
                version_check = False
                for entry in Version:
                    if(cycle.Cycle_InputData[p].Version==entry):
                        version_check = True

            if not version_check: continue;
            # Create Element
            InputGrandchild= doc.createElement('InputData')
            tempChild.appendChild(InputGrandchild)
            
            InputGrandchild.setAttribute('Lumi', str(float(cycle.Cycle_InputData[p].Lumi)*LumiWeight))
            InputGrandchild.setAttribute('Type', cycle.Cycle_InputData[p].Type)
            InputGrandchild.setAttribute('Version', cycle.Cycle_InputData[p].Version)
            if FileSplit!=-1:
                InputGrandchild.setAttribute('Cacheable', 'False')
            else:
                InputGrandchild.setAttribute('Cacheable', cycle.Cycle_InputData[p].Cacheable)
                InputGrandchild.setAttribute('NEventsSkip', str(SkipEvents))
                InputGrandchild.setAttribute('NEventsMax', str(MaxEvents))
        
            count_i =-1
            #print len(cycle.Cycle_InputData[p].io_list)
            for entry in cycle.Cycle_InputData[p].io_list.FileInfoList:
                count_i +=1
                if FileSplit > 0:
                    if not (count_i<(NFile+1)*FileSplit and count_i>= NFile*FileSplit):
                        continue
                Datachild= doc.createElement(entry[0])
                InputGrandchild.appendChild(Datachild)
                for it in range(1,len(entry),2):
                    #print entry[it],entry[it+1]
                    Datachild.setAttribute(entry[it],entry[it+1])
                
            for entry in cycle.Cycle_InputData[p].io_list.other:
                Datachild= doc.createElement(entry[0])
                InputGrandchild.appendChild(Datachild)
                for it in range(1,len(entry),2):
                    #print entry[it],entry[it+1]
                    Datachild.setAttribute(entry[it],entry[it+1])
            if len(cycle.Cycle_InputData[p].io_list.InputTree)!=3:
                print 'something wrong with the InputTree, lenght',len(cycle.Cycle_InputData[p].io_list.InputTree)
                print cycle.Cycle_InputData[p].io_list.InputTree
                print 'going to exit'
                exit(0)
            
            Datachild= doc.createElement(cycle.Cycle_InputData[p].io_list.InputTree[0])
            InputGrandchild.appendChild(Datachild)
            Datachild.setAttribute(cycle.Cycle_InputData[p].io_list.InputTree[1],cycle.Cycle_InputData[p].io_list.InputTree[2])
           
                

        #InGrandGrandchild= doc.createElement('In')
        ConfigGrandchild  = doc.createElement('UserConfig')
        tempChild.appendChild(ConfigGrandchild)

        for item in cycle.Cycle_UserConf:
            ConfigGrandGrandchild = doc.createElement('Item')
            ConfigGrandchild.appendChild(ConfigGrandGrandchild)
            ConfigGrandGrandchild.setAttribute('Name',item.Name)
            ConfigGrandGrandchild.setAttribute('Value',item.Value)

    return root.toprettyxml()


class header(object):
    def __init__(self,xmlfile):
        f = open(xmlfile)
        line = f.readline()
        self.header = []
        self.Version = []
        while '<JobConfiguration' not in line:
            self.header.append(line)
            line = f.readline()
            if 'ConfigParse' in line:
                self.ConfigParse = parseString(line).getElementsByTagName('ConfigParse')[0]
                self.NEventsBreak = int(self.ConfigParse.attributes['NEventsBreak'].value)
                self.FileSplit = int(self.ConfigParse.attributes['FileSplit'].value)
            if 'ConfigSGE' in line:
                self.ConfigSGE = parseString(line).getElementsByTagName('ConfigSGE')[0]
                self.RAM = self.ConfigSGE.attributes['RAM'].value
                self.DISK = self.ConfigSGE.attributes['DISK'].value
                self.Notification = self.ConfigSGE.attributes['Notification'].value
                self.Mail = self.ConfigSGE.attributes['Mail'].value
                self.Workdir = self.ConfigSGE.attributes['Workdir'].value
        f.close()   

def get_number_of_events(Job, Version):
    InputData = filter(lambda inp: inp.Version==Version[0], Job.Job_Cylce[0].Cycle_InputData)[0]
    NEvents = 0
    for entry in InputData.io_list.FileInfoList:
            for name in entry:
                if name.endswith('.root'):
                    f = ROOT.TFile(name)
                    NEvents += f.Get(InputData.io_list.InputTree[2]).GetEntriesFast()
                    f.Close()
    return NEvents

def write_all_xml(path,datasetName,header,Job,workdir):
    NEventsBreak= header.NEventsBreak
    FileSplit=header.FileSplit

    NFiles=0

    Version =datasetName
    if Version[0] =='-1':Version =-1

    if NEventsBreak!=0 and FileSplit<=0:
        NEvents = get_number_of_events(Job, Version)
        print '%s: %i events' % (Version[0], NEvents)
        NFiles = int(math.ceil(NEvents / float(NEventsBreak)))
        SkipEvents = NEventsBreak
        MaxEvents = NEventsBreak

        for i in xrange(NFiles):
            if i*SkipEvents >= NEvents:
                break 
            if (i+1)*MaxEvents >= NEvents:
                MaxEvents = NEvents-i*SkipEvents
            LumiWeight = float(NEvents)/float(MaxEvents)
            outfile = open(path+'_'+str(i+1)+'.xml','w+')
            for line in header.header:
                outfile.write(line)
            outfile.write(write_job(Job,Version,i*SkipEvents,MaxEvents,i,-1,workdir,LumiWeight))
            outfile.close()
 
    elif FileSplit>0:
        for entry in Version:
            print 'Splitting job by files',entry
            for cycle in Job.Job_Cylce:
                for p in range(len(cycle.Cycle_InputData)):
                    if(cycle.Cycle_InputData[p].Version==entry) or Version ==-1:
                        for it in range(int(math.ceil(float(len(cycle.Cycle_InputData[p].io_list.FileInfoList))/FileSplit))):
                            outfile = open(path+'_'+str(it+1)+'.xml','w+')
                            for line in header.header:
                                outfile.write(line)
                            outfile.write(write_job(Job,Version,0,-1,it,FileSplit,workdir))
                            outfile.close()
                            NFiles+=1
 

    else:
        NFiles+=1
        outfile = open(path+'_OneCore'+'.xml','w+')
        for line in header.header:
            outfile.write(line)
        outfile.write(write_job(Job,Version,0,-1,"",0,workdir))
        outfile.close()

    return NFiles



