#!/usr/bin/python
# -*- encoding: utf-8 -*-

VERSION = 'UniversalBackup.py v0.2'
#
# Usage:    UniversalBackup.py [options]
# Options:
#   -d          - turn on debugging output
#   -l [file]   - redirect stdout to the [file]
#
# This program acts as an universal backup utility, which intends
# to copy selected files from one place to another. Files to be copied,
# are specified in exterior configuration file, where user can also specify
# which extension files must contain, or file/directorie masks with
# wildcards applied. In fact, every file/dir/mask specifier will
# be treated as an regular expression pushing off the posibilities.
# The code is highly platform-independent. 
#
# Script may be converted to an 'exe' form using py2exe on windows.
#
# Configuration file must obey following format:
# ------------------------------
# backup_dir: Drive:\Default\backup\dir
# after_backup: cmd-line-to-execute-after-backup
# # comment
# [label]
# recursive
# dst: \path\relative\to\backup_dir
# path: Drive:\Path\to\the\files
# +exts: c cpp h txt
# -files: omit.txt exclude.dat
# -dirs: \dir1\dir2\do_not_backup
# +masks: file* alternative_mask*
# ------------------------------
# 
# Each field can be preceded with + (default) or - which
# tells the script to filter or unfilter by specified criterias.
# There cannot occure inclusion as well as exclusion specifier of 
# the same type in a one section (e.g. +exts and -exts concurrent).
# Inclusion/exclusion filters are case-insensitive.
# Only `label`, as well as `path` specifiers are mandatory for a section.
# Where:
#   backup_dir - default destination directory where files
#           will be copied, unless indicated otherwise inside a section     
#   after_backup - command line / program commands to execute after
#           successful backup. User can specify 
#           more then one of those fields.
#   comment - stands for a regular comment, that will be skipped
#   label - files section name, separetes files groups
#   [no]recursive - specifies wheter to backup files recursively.
#           When 'norecursive' is met, then group will not be scanned
#           recursively. This is by default.
#   dst - supersedes backup_dir or acts as a relative path to the backup_dir
#   path - specifies file/directory path to file/files that need
#           to be backed up. Path can be relative to the current script's
#           directory, or absolute with drive letter. 
#           Wildcards *, ? allowed. There can be more then one path
#           field. This will specify more then one files for example.
#   [+/-]exts - preceding plus tells the script to include in backup
#           files with specified extension which occured in this list.
#           +exts - include files with following extenstions
#           -exts - exclude ditto
#   [+/-]files - explicit file names to be included/excluded. It is not
#           a necessity for this names to contain an extension.
#   [+/-]dirs - same as in files field, but concerns directories.
#   [+/-]masks - mask to be used as an include/exclude filter.
#
# Mariusz B., 2013

import os
import sys
import re
import shutil
from subprocess import Popen
from datetime import datetime

# ========================
#
# globals
#

DEBUG_VERSION = 0

if DEBUG_VERSION == 1:
    import pprint


# Path to the file which will contain files
# specifiactions / script configuration.
g_PathsFile = "configuration.ini"


# Will handle imported files groups.
# This is LIST of DICTONARIES.
g_Sections = []
g_BackupDir = ""

# Commands line to execute after backup
g_AfterBackup = []

# DO NOT ALTER ELEMENTS POSITION INSIDE THIS TUPLE!
# Further code strongly depends on those positions.
g_ValidFields = ("path", "dst", "recursive", 
                "exts", "files", "dirs", "masks",
                "+exts", "-exts", "-files", "+files", 
                "+dirs", "-dirs", "+masks", "-masks")

# ========================
#
# routines
#

def dbg( x):
    x = x.replace("\r", "").replace("\n","")
    if DEBUG_VERSION == 1:
        print "[dbg]", x #[:70]

def err( x):
    x = x.replace("\r", "").replace("\n","")
    print "\n[!]", x[:70]
    sys.exit(1)

# ========================

def parse_file( lines):
    """ 
    Parses configuration file in order to build
    entire dictonary with files groups which
    script will be backing up.
    """

    global g_Sections
    global g_BackupDir
    global g_AfterBackup
    global g_ValidFields

    # files group to be added to g_Sections
    group = {}
    valid_fields = g_ValidFields


    for i in range(len( lines)):
        lines[i] = lines[i].strip()
        m = []

        if re.match( "^\s*#.*", lines[i]) != None or len(lines[i]) < 3:
            # Skip comments and empty lines.
            continue

        # check for label
        m = re.match( "\s*(\[\s?.+\s?\])\s*", lines[i])
        if m != None:
            m = m.groups()
            if len(group):
                # recursive flag does not occur, and one and set to zero.
                if "recursive" not in group.keys():
                    group["recursive"] = 0

                # append just parsed group to sections list.
                g_Sections.append(group)
                group = {}

            group["label"] = m[0]
            dbg( "Parsing '%s' section..." % group["label"])
            continue

    
        # checking for other fields
        try:
            m = re.match( "\s*(\+|-?\w+)\s*[:=]?\s*(.*)\s*", \
                    lines[i]).groups()
        except:
            print "[?] Line %d: '%s' is invalid. Skipping..." \
                    % (i,lines[i][:45])
            continue

        if m :
            if m[0] == "recursive":
                # set recursive flag
                group["recursive"] = 1
            
            elif m[0] == "norecursive":
                continue

            elif m[0] == "backup_dir":
                if g_BackupDir != "":
                    print "Already got backup_dir. "\
                            "Skipping another declaration.."
                    continue

                try:
                    g_BackupDir = m[1]
                except IndexError:
                    err( "Configuration file must specify backup_dir path!")

            elif m[0] == "after_backup":
                try:
                    g_AfterBackup.append( m[1])
                except IndexError:
                    print "[?] Conf. file must specify "\
                            "after_backup cmd line!"
                    print "Skipping after_backup declaration..."
                    continue

            elif len(m) == 2:
                field = m[0].lower()
                data = ""

                # check for occurence of another specifier of the same type,
                # but with different declaration (for example, having
                # inclusion specifier - check for existence of 
                # exclusion specifier). When found, skip it.
                if (field[0] == '+' and \
                        ('-'+field[1:] in group.keys()) ) or \
                    ( field[0] == '-' and ('+'+field[1:] in group.keys()) ):
                    err( "Mutually exclusive specifiers: '%s' in"\
                            " section '%s'" % (field[1:], group["label"]) )

                data = m[1]

                if field in valid_fields:
                    if field == "path":
                        try:
                            group[field].append(data)
                        except:
                            group[field] = [data]
                    else:
                        values = []

                        # Check if there are values surrounded by `"` chars.
                        if data.find('"') == -1:
                            values = data.split(" ")
                        else:
                            # If so, then we have to "extract" 
                            # them specially.
                            _v = [f for f in re.split( '(".+")', data) if f]
                            for v in _v:
                                if '"' not in v:
                                    values.extend( v.split(" "))
                                else:
                                    values.append( v.strip('"'))

                        # adding new field to the group.
                        # But firstly, check if the field already exists
                        # in a dictonary.
                        if field in group.keys():
                            if m[0][0] != '-':
                                group[field].extend(values)
                            else:
                                # user specified -field:
                                for a in values:
                                    if a in group[field]:
                                        group[field].remove(a)
                                    else:
                                        group[field].append(a)
                        else:
                            group[field] = values
                else:
                    if len(m) == 1 and \
                        (lines[i].find(":") != -1 \
                        or lines[i].find("=") != -1):
                            err( "Specifier: '%s' requires a value!")


    if g_BackupDir == "":
        err( "Configuration file hasn't specified a "\
                "valid backup_dir. Quitting.")

    if len(group.keys() ):
        if "recursive" not in group.keys():
            group["recursive"] = 0
        g_Sections.append( group)
    
    if len(g_Sections) == 0:
        err( "There is no sections in configuration file. Quitting...")
    else:
        for g in g_Sections:
            if "path" not in g.keys():
                err("Section '%s' does not have a valid 'path' specifier!" \
                        % g["label"])



# ========================

def validate_sections():
    """
    This procedure will check if specified paths exists in the system,
    then validate specified extensions if they meets extensions criterias.
    Nextly will try to evaluate possible 'dst' paths that are relative to
    'backup_dir'.
    """
    
    global g_Sections
    global g_BackupDir
    global g_ValidFields

    # Firstly have to check if backup_dir exists. If not, will try to
    # create this directory
    if not os.path.exists(g_BackupDir):
        try:
            os.makedirs(g_BackupDir)
            print "[?] Successfully created directory backup_dir."
        except:
            err("It was not possible to create backup_dir. ")

    # validating sections
    for sect in g_Sections:
        copy = sect
        if len(sect["path"]) > 1:
            for p in range(len(sect["path"])):
                sect["path"][p] = sect["path"][p].strip('\"')
        else:
            sect["path"][0] = sect["path"][0].strip('\"')
        paths = sect["path"]

        if len( paths) == 0:
            print "[?] There is no 'path' specifier in '%s'"\
                    " section. Skipping..." % (sect["label"])

        # firstly check occurring paths
        for path in paths:
            if not os.path.exists(path):
                if len(paths) == 1:
                    print "[?] Path from '%s' section does not exists. "\
                            "Skipping..." % sect["label"]
                    g_Sections.remove(sect)
                else:
                    # this path does not exists, how 
                    # about the others in this section?
                    print "[?] Path: '%s' does not exists. "\
                            "Skipping..." % path[:25]
                    paths.remove(path)

        # attempt to validating other fields
        val = {}
        for k in sect.keys():
            if k in g_ValidFields[3:]:
                val[k] = sect[k]

        if len( val):
            for v in val.keys():
                ill = "<>:/\\|"
                for e in val[v]:
                    for illegal in ill:
                        if illegal in e:
                            print "[!] Invalid entry in %s.%s: '%s'. "\
                                    "Skipping..." % (sect["label"], v, e)
                            sect[v].remove(e)
                            break
                        elif len( e) == 0:
                            sect[v].remove(e)
                            break

        # evaluate 'dst' fields relatively to backup_dir.

        if "dst" in sect.keys():
            if type(sect["dst"]) == type([]):
                sect["dst"] = sect["dst"][0]

            sect["dst"] = sect["dst"].strip('\"')

            if not os.path.isabs(sect["dst"]):
                if not os.path.exists( os.path.join( \
                        g_BackupDir, sect["dst"])):
                    print "[?] Directory: '%s' doesn't exists."\
                            " Creating..." % sect["dst"]
                    os.makedirs( os.path.join( g_BackupDir, sect["dst"]))
            else:
                if not os.path.exists( sect["dst"]):
                    print "[?] Directory: '%s' doesn't exists."\
                            " Creating..." % sect["dst"]
                    os.makedirs( sect["dst"])

        # alter modified dictonary
        try:
            g_Sections[ g_Sections.index(copy)] = sect
        except:
            # I know, that it is not a good way to handle an
            # exception, but this kind of exception shouldn't 
            # be handled more properly.
            print "[!] Section: %s will not be backed up." % copy["label"]
            pass


# ========================

def check_it( entry, sect):
    """
    Cross checks an entry with section's filter specifiers,
    to determine wheter to filter-out the entry or leave it
    to back up.
    """

    global g_ValidFields
    flag = 0
    desc = ""

    for v in g_ValidFields[4:7]:
        if v in sect.keys():
            for e in sect[v]:
                if e == "": continue
                if re.search( e, entry, re.I) == None:
                    desc = "incl. '%s' because of +%s='%s'"\
                            % (os.path.basename(entry), v, e)
                    flag = 1
        elif "+"+v in sect.keys():
            for e in sect["+"+v]:
                if e == "": continue
                if re.search( e, entry, re.I) == None:
                    desc = "incl. '%s' because of +%s='%s'"\
                            % (os.path.basename(entry), v, e)
                    flag = 1
        elif "-"+v in sect.keys():
            for e in sect["-"+v]:
                if e == "": continue
                if re.search( e, entry, re.I) != None:
                    desc = "excl. '%s' because of -%s='%s'"\
                            % (os.path.basename(entry), v, e)
                    flag = 1

        if flag: break

    if flag == 1:
        # Output inclusion/exclusion result.
        #dbg( desc)
        pass

    return (flag, desc)

# ========================

def traverse_paths():
    """
    This procedure will traverse paths from g_Sections dictonaries.
    Then will scan/walk entire path trees in order to build a list
    of files that should be backed up. At every file will perform sort
    of checking (MD5 hashing) with existing in backup_dir file. This 
    will help omitting files already up-to-date in backup_dir.
    """

    global g_Sections
    global g_BackupDir
    global g_ValidFields

    src_files = []
    dst_files = []
    raw_list = []

    for sect in g_Sections:
        paths = sect["path"]
        sdst = ""

        exts = []
        inc = 1     # inclusion flag
        if "+exts" in sect.keys() or "exts" in sect.keys(): 
            exts = sect["+exts"]
        elif "-exts" in sect.keys():
            exts = sect["-exts"]
            inc = 0

        for path in paths:

            # walk through entire path tree and gather files.
            dir = 0
            try:
                sdst = sect["dst"]
            except:
                # there was no 'dst' specifier
                sdst = ""

            if os.path.isdir( path):
                _raw_list = set(walk_path( path, sect["recursive"]))
                dir = 1

                # Adding last dir from path to the dstpath.
                if "/" in sdst:
                    sdst = os.path.join(sdst, path.strip("/").\
                            split("/")[-1])
                else:
                    sdst = os.path.join(sdst, path.strip("\\").\
                            split("\\")[-1])
            else:
                _raw_list = [path,]

            # filtering extensions
            raw_list = []
            for e in _raw_list:
                flag = 0

                if inc == 0:
                    for ex in exts:
                        if e[e.find(".")+1:].lower() == ex.lower():
                            flag = 1
                            break
                elif len(exts):
                    ex = [ _e.lower() for _e in exts]
                    if e[e.find(".")+1:].lower() not in ex:
                        flag = 1

                filter_out = check_it( e, sect)
                if filter_out[0] == 0 and flag == 0:
                    raw_list.append(e)
                else:
                    pass

            # Gathering files
            for e in raw_list:

                # Now generate dst path based on src path
                assert e.find(path) != -1, \
                        "File path does not contain src path!"

                # CREATE dst path for a file.
                if dir:
                    p = e[len(path):]
                    p = p.strip("/\\")
                else:
                    p = os.path.basename(e)

                if "dst" not in sect.keys():
                    p = os.path.join(g_BackupDir, p)
                else:
                    tail = os.path.join(sdst, p)
                    if type([]) == type(tail):
                        tail = "".join(tail)
                    p = os.path.join(g_BackupDir, tail)

                
                # Now check file's modification time, in order of omitting
                # files already backed up in their last versions.
                srcMtime = 0
                dstMtime = -1
                try:
                    srcMtime = os.path.getmtime( e)
                    dstMtime = 0
                    if os.path.exists( p):
                        dstMtime = os.path.getmtime( p)
                except WindowsError as er:
                    if er.errno == 2:
                        pass
                except:
                    # if for some reason files couldn't be queried, 
                    # then just skip them out
                    dstMtime = 0

                if int(dstMtime) == int(srcMtime):
                    dbg( "File '%s' is already up-to-date." % p)
                else:
                    src_files.append(e)
                    dst_files.append(p)

    return (src_files, dst_files)


# ========================

def walk_path( path, recursive):
    """
    This function walks entire path tree and collects every file listed
    Can perform traversing through path recursively or not, depending on 
    a second parameter value (boolean). 
    """

    files = []
    r = [".", ".."]

    print "Walking through '%s'..." % path

    if recursive:
        for (root, dirs, _files) in os.walk( path):
            files.extend( [ os.path.join(root, f) for f in \
                            _files if f not in r] )
    else:
        _files = os.listdir(path)
        _files = [ os.path.join(path, f) for f in _files]
        files.extend( [ f for f in _files if not os.path.isdir(f)] )

    return files


# ========================
# main
#

if __name__ == '__main__':

    # Parse command line.
    log = 0
    if len(sys.argv) >= 2:
        if sys.argv[1] == "-d":
            DEBUG_VERSION = 1
            import pprint
        elif sys.argv[1] == "-l":
            f = "log.txt"
            if len(sys.argv) == 3:
                f = sys.argv[2]
            # redirecting standard output
            sys.stdout = open(f, 'a')
            log = 1
            print "Log opened."

    print """
    --------------------------------------

    """+VERSION+""" - Mariusz B. 2013"""

    dt = datetime.now().timetuple()

    print """    ==  %02d.%02d.%04d, %02d:%2d:%02d ==
    """ % (dt.tm_mday, dt.tm_mon, dt.tm_year,
            dt.tm_hour, dt.tm_min, dt.tm_sec)
    
    
    # Stage 1: parsing configuration file
    f = 0
    try:
        f = open( g_PathsFile)
    except:
        err(    "You must create configuration file: '%s' inside\n"\
                "directory with this program. Quitting.." % g_PathsFile )

    lines = f.readlines()
    f.close()

    print "Parsing configuration file..."
    parse_file( lines)

    # Stage 2: Validating parsed sections
    print "Validating gathered sections..."
    validate_sections()

    print "Done."

    # DEBUG ONLY! Pretty-print gathered sections.
    if DEBUG_VERSION == 1:
        print "[dbg] Dumping g_Sections:"
        pprint.pprint( g_Sections)

    # This will be a huge files list that are supposed to be backed up.
    src_files, dst_files = traverse_paths()

    assert len(src_files) == len(dst_files), \
            "src_files and dst_files are not equal!"

    print ""

    # Perform actual copying...
    for i in range(len(src_files)):

        if os.path.exists(dst_files[i]) == False:
            try:
                os.makedirs( os.path.dirname(dst_files[i]) )
            except WindowsError as err:
                # File already exists error... 
                if err.errno == 183:
                    pass

        if DEBUG_VERSION == 0:
            if len(src_files) <= 64:
                print "Backing up '%s'..." % (src_files[i] )
            else:
                s = "[%3d%%] Copying %d/%d %s...\r" % \
                    (100*(float(i)/len(src_files)), i, len(src_files),
                    src_files[i][:45])
                if log == 0:
                    sys.stdout.write(s)
                    sys.stdout.flush()
        else:
            dbg("COPY '%s' => '%s'" % (src_files[i], dst_files[i] ))

        try:
            shutil.copy2( src_files[i], dst_files[i] )
        except IOError as err:
            if err.errno == 13:
                print "[!] Couldn't copy the file: '%s'" % dst_files[i]
    
    if len(src_files) == 0:
        print "\nThere was nothing to update or back up."
    else:
        print "\nOperation completed. Backed up %d files." % len(src_files)

        if len(g_AfterBackup):
            print "Performing post-backup operations..."
            for e in g_AfterBackup:
                Popen( [e] )

        print "All done. Good bye."

