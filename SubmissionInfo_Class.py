#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import json
import time

# class for the submission information


class SubInfo(object):
    def __init__(self, name='', numberOfFiles=0, data_type='', resubmit=0):
        self.name = name
        self.numberOfFiles = numberOfFiles  # number of expected files
        self.data_type = data_type
        self.rootFileCounter = 0  # number of expected files
        self.status = 0   # 0: init, 1: data on disk
        self.missingFiles = []
        self.pids = [''] * numberOfFiles
        self.notFoundCounter = [0] * numberOfFiles
        self.reachedBatch = [False] * numberOfFiles
        self.jobsRunning = [False] * numberOfFiles
        self.jobsDone = [False] * numberOfFiles
        self.arrayPid = -1
        self.resubmit = [resubmit] * numberOfFiles
        self.startingTime = 0

    def reset_resubmit(self, value):
        self.resubmit = [value] * self.numberOfFiles

    def to_JSON(self):
        # print json.dumps(self, default=lambda o: o.__dict__, sort_keys=True,
        # indent=4)
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def load_Dict(self, data):
        self.__dict__ = data

    def process_batchStatus(self, batch, it):
        self.jobsRunning[it] = False
        self.notFoundCounter[it] += 1
        if batch == 1:
            # Safeguard, no action is taken if a job is not found once.
            self.notFoundCounter[it] = 0
            # Use to understand when a job reached the batch before taking any
            # action
            self.reachedBatch[it] = True
            self.jobsRunning[it] = True
        # kill jobs with have an error state
        if batch == 2:
            if self.pids[it]:
                print 'going to kill job', self.pids[it]
                time.sleep(5)
                subprocess.Popen(['qdel', str(self.pids[it])],
                                 stdout=subprocess.PIPE)
                self.pids[it] = ''  # just got killed
                self.reachedBatch[it] = False
                return -2
            else:
                print 'going to kill job', str(self.arrayPid) + '.' + str(it + 1)
                time.sleep(5)
                subprocess.Popen(
                    ['qdel', str(self.arrayPid) + '.' + str(it + 1)], stdout=subprocess.PIPE)
                self.reachedBatch[it] = False
                return -2
        return batch
