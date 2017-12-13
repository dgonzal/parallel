#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
# import multiprocessing
from Manager import *
from gridstarter import gridstart
from LumiCalcAutoBuilder import *


def SFrameBatchMain(input_options):
    parser = OptionParser(usage="usage: %prog [options] filename",
                          version="%prog 0.2")
    parser.add_option("-w", "--workdir",
                      action="store",
                      dest="workdir",
                      default="",
                      help="Overwrite the place where to store overhead.")
    parser.add_option("-o", "--outputdir",
                      action="store",
                      dest="outputdir",
                      default="",
                      help="Overwrite the place where to store the output.")
    parser.add_option("-s", "--submit",
                      action="store_true",  # optional because action defaults to "store"
                      dest="submit",
                      default=False,
                      help="Submit Jobs to the grid")
    parser.add_option("-r", "--resubmit",
                      action="store_true",  # optional because action defaults to "store"
                      dest="resubmit",
                      default=False,
                      help="Resubmit Jobs were no files are found in the OutputDir/workdir .")
    parser.add_option("-l", "--loopCheck",
                      action="store_true",  # optional because action defaults to "store"
                      dest="loop",
                      default=False,
                      help="Look which jobs finished and where transfered to your storage device.")
    parser.add_option("-a", "--addFiles",
                      action="store_true",
                      dest="add",
                      default=False,
                      help="hadd files to one")
    parser.add_option("-T", "--addFilesNoTree",
                      action="store_true",
                      dest="addNoTree",
                      default=False,
                      help="hadd files to one, without merging TTrees. Can be combined with -f.")
    parser.add_option("-f", "--forceMerge",
                      action="store_true",  # optional because action defaults to "store"
                      dest="forceMerge",
                      default=False,
                      help="Force to hadd the root files from the workdir into the ouput directory.")
    parser.add_option("-c", "--continueMerge",
                      action="store_true",
                      dest="waitMerge",
                      default=False,
                      help="Wait for all merging subprocess to finish before exiting program. All the subprocesses that finish in the meantime become zombies until the main program finishes.")
    parser.add_option("-k", "--keepGoing",
                      action="store_true",
                      dest="keepGoing",
                      default=False,
                      help="Never ask for user input, but keep going on.")
    parser.add_option("-x", "--exitOnQuestion",
                      action="store_true",
                      dest="exitOnQuestion",
                      default=False,
                      help="Never ask for user input, but exit instead. (Overwrites keepGoing)")
    parser.add_option("-g", "--gridControl_HTC",
                      action="store_true",
                      dest="gridc",
                      default=False,
                      help="Submit jobs via grid-control to HTCondor.")

    (options, args) = parser.parse_args()
    parser.add_option("--ReplaceUserItem",
                      action="append",
                      dest="useritemlist",
                      default=[],
                      help="Replace Items in UserConfig, for more then one just add as many times the command as you need. Nice for uncertainties. Usage --ReplaceUserItem \"Name,Value\""
                      )
    parser.add_option("--addTree",
                      action="append",
                      dest="sframeTreeInfo",
                      default=[],
                      help="This is used if you need to add something to all the InputData Childs (e.g an OutputTree) in the Result.xml file. If only one argument is passed it is assumed to be the name of the OutputTree."
                      )
    parser.add_option("--RemoveEmptyFiles",
                      action="store_true",
                      dest="FileSplitFileCheck",
                      help="Force to remove empty files in FileSplit mode. This is only necessary after a Selection where there many Files with no entries at all or only very few. This might lead to sframe crashing."
                      )
    parser.add_option("--XMLDatabase",
                      action="store",
                      dest="xmldatabaseDir",
                      help="This command creates from a data file the new sframe_main xml file calculating the lumi from the number of events and a given cross section. You can specify the number of events (weighted). Else it will try to find the number of events at the end of the xml Files (stored in the dateset directory) or use a small python script to read the number of entries from the trees. If it has to read the number of entries from the trees you need to specify how many cores it should use and also the method to be used. True == Fast / False == weights. Example can be found as DatabaseExample. USERCONFIG is not filled and needs to be done manually. Usage: sframe_batch --XMLDatabase DATABASE_DIR FILENAME_TO_STORE."
                      )

    (options, args) = parser.parse_args(input_options)

    start = timeit.default_timer()

    # global header
    if len(args) != 1:
        parser.error(
            "wrong number of arguments. Help can be invoked with --help")

    xmlfile = args[0]
    if options.xmldatabaseDir:
        XMLBuilder = lumicalc_autobuilder(options.xmldatabaseDir)
        XMLBuilder.write_to_toyxml(xmlfile)
        stop = timeit.default_timer()
        print "SFrame Batch was running for", round(stop - start, 2), "sec"
        print "SFrame Batch just build", xmlfile, "for you. Fill the USERCONFIG yourself."
        return 0

    if os.path.islink(xmlfile):
        xmlfile = os.path.abspath(os.readlink(xmlfile))
    # softlink JobConfig.dtd into current directory
    # the len(arg) makes it undependet if the .py or .pyc is used
    scriptpath = os.path.realpath(
        __file__)[:-len(os.path.realpath(__file__).split("/")[-1])]
    if not os.path.exists('JobConfig.dtd'):
        os.system('ln -sf %s/JobConfig.dtd .' % scriptpath)

    # print xmlfile, os.getcwd
    proc_xmllint = subprocess.Popen(
        ['xmllint', '--noent', xmlfile], stdout=subprocess.PIPE)
    xmlfile_strio = StringIO.StringIO(proc_xmllint.communicate()[0])
    sax_parser = xml.sax.make_parser()
    xmlparsed = parse(xmlfile_strio, sax_parser)
    header = fileheader(xmlfile)
    if options.FileSplitFileCheck:
        header.RemoveEmptyFileSplit = True
    else:
        header.RemoveEmptyFiles = False
    if header.RemoveEmptyFileSplit and header.FileSplit:
        print "Removing all empty files in FileSplit mode."

    node = xmlparsed.getElementsByTagName('JobConfiguration')[0]
    Job = JobConfig(node)

    workdir = header.Workdir
    if options.workdir:
        print "Overwriting workdir:", workdir, "with", options.workdir
        workdir = options.workdir
    if not workdir:
        workdir = "workdir"
    # if not workdir.endswith("/"): workdir += "/"
    currentDir = os.getcwd()
    if not os.path.exists(workdir + '/'):
        os.makedirs(workdir + '/')
        print workdir, 'has been created'
        shutil.copy(scriptpath + "JobConfig.dtd", workdir)
        shutil.copy(args[0], workdir)
    # print header.Version[0]

    for cycle in Job.Job_Cylce:
        if len(options.outputdir) > 0:
            print 'Overwriting', cycle.OutputDirectory, 'with', options.outputdir
            cycle.OutputDirectory = options.outputdir
            if not cycle.OutputDirectory.endswith(
                    "/"):
                cycle.OutputDirectory += "/"
        if cycle.OutputDirectory.startswith('./'):
            cycle.OutputDirectory = currentDir + cycle.OutputDirectory[1:]
        if len(options.useritemlist) > 0:
            print 'Searching to replace UserConfig Values'
            for item in options.useritemlist:
                if ',' not in item:
                    print 'No , found in the substitution:', item
                    continue
                else:
                    pair_name_value = item.split(",")
                    item_name = pair_name_value[0]
                    item_value = pair_name_value[1]
                    for cycle_item in cycle.Cycle_UserConf:
                        if item_name == cycle_item.Name:
                            print "Replacing", item_name, "Value:", cycle_item.Value, "with", item_value
                            cycle_item.Value = item_value
        print 'starting manager'
        manager = JobManager(options, header, workdir)
        manager.process_jobs(cycle.Cycle_InputData, Job)
        nameOfCycle = cycle.Cyclename.replace('::', '.')
        # this small function creates a xml file with the expected files
        if result_info(Job, workdir, header, options.sframeTreeInfo) == 1:
            print ' Result.xml created for further jobs'
        # submit jobs if asked for
        if options.gridc:
            gridstart(workdir, cycle.OutputDirectory, currentDir)
            return 0
        if options.submit:
            manager.submit_jobs(
                cycle.OutputDirectory, nameOfCycle)
        manager.check_jobstatus(cycle.OutputDirectory,
                                nameOfCycle, False, False)
        if options.resubmit:
            manager.resubmit_jobs()
        # get once into the loop for resubmission & merging

        if not options.loop and options.forceMerge and not options.waitMerge:
            manager.check_jobstatus(cycle.OutputDirectory, nameOfCycle)
            manager.merge_files(cycle.OutputDirectory,
                                nameOfCycle, cycle.Cycle_InputData)
            return 0
        loop_check = True
        while loop_check == True:
            if not options.loop:
                loop_check = False
                # This is necessary since qstat sometimes does not find the jobs it should monitor.
                # So it checks that it does not find the job 5 times before
                # auto resubmiting it.
                for i in range(6):
                    manager.check_jobstatus(cycle.OutputDirectory, nameOfCycle)
            else:
                manager.check_jobstatus(cycle.OutputDirectory, nameOfCycle)

            manager.merge_files(cycle.OutputDirectory,
                                nameOfCycle, cycle.Cycle_InputData)
            if manager.get_subInfoFinish() or (not manager.merge.get_mergerStatus() and manager.missingFiles == 0):
                print 'if grid pid information got lost root Files could still be transferring'
                break
            if options.loop:
                manager.print_status()
                time.sleep(5)
        # print 'Total progress', tot_prog
        manager.merge_wait()
        manager.check_jobstatus(cycle.OutputDirectory,
                                nameOfCycle, False, False)
        print '-' * 80
        manager.print_status()
    stop = timeit.default_timer()
    print "SFrame Batch was running for", round(stop - start, 2), "sec"
    # exit gracefully

    if all(si.status == 1 for si in manager.subInfo):
        return 0
    else:
        return -1


if __name__ == "__main__":
    # print 'Arguments',sys.argv[1:]
    status = SFrameBatchMain(sys.argv[1:])
    exit(status)
