#!/usr/bin/env python

import xml.dom.minidom as minidom
from copy import deepcopy
from glob import glob

import os

class JobConfig(object):
    def __init__(self,node):
        for item in node.attributes.items():
            if(item[0]=='JobName'): self.JobName = item[1]
            if(item[0]=='OutputLevel'):  self.OutputLevel = item[1]
        self.Libs = []
        for child in node.getElementsByTagName('Library'):
            for lib in child.attributes.items():
                self.Libs.append(lib[1])
        self.Packs = []
        for child in node.getElementsByTagName('Package'):
            for pack in child.attributes.items():
                self.Packs.append(lib[1])
        self.Job_Cylce = []
        for item in node.getElementsByTagName('Cycle'):
            self.Job_Cylce.append(Cycle(item))

class Cycle(object):
    def __init__(self,node):       
        self.cacheData = 0
        for item in node.attributes.items():
            if(item[0]=='Name'): self.Cyclename = item[1]
            #if(item[0]=='RunMode'):  self.RunMode = item[1]
            #if(item[0]=='ProofServer'): self.ProofServer = item[1]
            #if(item[0]=='ProofWorkDir'):  self.ProofWorkDir = item[1]
            if(item[0]=='OutputDirectory'): self.OutputDirectory = item[1]
            if(item[0]=='PostFix'):  self.PostFix = item[1]
            if(item[0]=='TargetLumi'):  self.TargetLumi = item[1]
        
        self.Cycle_InputData =[]
        for item in node.getElementsByTagName('InputData'):
            self.Cycle_InputData.append(InputData(item,self.cacheData))
            if self.Cycle_InputData[-1].Cacheable=='True': self.cacheData = True

        self.Cycle_UserConf = []
        for child in node.getElementsByTagName('UserConfig'):
            for item in child.getElementsByTagName('Item'):
                name =  None
                value = None
                for attr in item.attributes.items():
                    if(attr[0]=='Name'): name=attr[1]
                    if(attr[0]=='Value'): value=attr[1]
                self.Cycle_UserConf.append(UserConfig(name,value))
            
        #print self.Cycle_UserConf

class InputData(object):
    def __init__(self,node,cacheMe):
        self.NEventsSkip = 0        
        for item in node.attributes.items():
            if(item[0]=='Lumi'): self.Lumi = item[1]
            if(item[0]=='NEventsMax'): self.NEventsMax = item[1]
            if(item[0]=='Type'): self.Type = item[1]
            if(item[0]=='Version'): self.Version = item[1]
            if(item[0]=='Cacheable'): 
                if item[1]=='True' and not cacheMe:
                    res = raw_input('Cacheable is set to True. Are you sure you want to continue? Y/[N] ')
                    if res.lower() != 'y':
                        exit(0)
                    else: cacheMe = True
                self.Cacheable = item[1]
            if(item[0]=='NEventsSkip'): self.NEventsSkip = item[1]
        #print self.Version
        self.io_list =InputList()
        for item in node.childNodes:
            #print item.nodeValue
            if not item.nodeType == 3:
                help_list = []
                #print item.nodeName
                help_list.append(item.nodeName)
                for entry in item.attributes.items():
                    for y in entry:
                        help_list.append(y)
                if item.nodeName == "In":
                    self.io_list.FileInfoList.append(help_list)
                elif item.nodeName == "InputTree":
                    if len(self.io_list.InputTree)==0: 
                        self.io_list.InputTree=help_list
                    elif self.io_list.InputTree != help_list:
                        print 'not using the same InputTree, strange prefere to exit'
                        exit(0)
                else:
                    self.io_list.other.append(help_list)
            
                
        expanded_list = []
        for help_list in self.io_list.FileInfoList:
            expanded_list += _expand_help_list_filenames(help_list)
        self.io_list.FileInfoList = expanded_list

    def split_NEvents(self,NEventsBreak,LastBreak):
        self.NEventsBreak = NEventsBreak
        self.LastBreak = LastBreak   
        
    
class UserConfig(object):
    def __init__(self,Name,Value):
        self.Name = Name
        self.Value = Value

class InputList(object):
    def __init__(self):
        self.FileInfoList =[]
        self.InputTree = []
        self.other =[]


def _expand_help_list_filenames(help_list):
    filenames = filter(lambda s: '*' in s, help_list)
    if not filenames:
        return [help_list]
    assert(len(filenames) == 1)
    pattern = filenames[0]
    real_filenames = glob(pattern)
    if not real_filenames:
        raise RuntimeError('No files found for pattern: %s'%pattern)
    new_help_list = []
    for new_file in real_filenames:
        new_list = deepcopy(help_list)
        new_help_list.append(new_list)
        for i in xrange(len(new_list)):
            if new_list[i] == pattern:
                new_list[i] = new_file
    return new_help_list
