Usage
------------------------------

    UniversalBackup.py [options]
Options:
  -d          - turn on debugging output
  -l [file]   - redirect stdout to the [file]

Description 
------------------------------

This program acts as an universal backup utility, which intends
to copy selected files from one place to another. Files to be copied,
are specified in exterior configuration file, where user can also specify
which extension files must contain, or file/directorie masks with
wildcards applied. In fact, every file/dir/mask specifier will
be treated as an regular expression pushing off the posibilities.
The code is highly platform-independent.

Script may be converted to an 'exe' form using py2exe on windows.

Configuration file
------------------------------
An example of configuration file might be (here using on Windows):

backup_dir: Drive:\Default\backup\dir
after_backup: cmd-line-to-execute-after-backup
# comment
[label]
recursive
dst: \path\relative\to\backup_dir
path: Drive:\Path\to\the\files
+exts: c cpp h txt
-files: omit.txt exclude.dat
-dirs: \dir1\dir2\do_not_backup
+masks: file* alternative_mask*

Each field can be preceded with + (default) or - which
tells the script to filter or unfilter by specified criterias.
There cannot occure inclusion as well as exclusion specifier of
the same type in a one section (e.g. +exts and -exts concurrent).
Inclusion/exclusion filters are case-insensitive.
Only `label`, as well as `path` specifiers are mandatory for a section.
Where:
  backup_dir - default destination directory where files
          will be copied, unless indicated otherwise inside a section
  after_backup - command line / program commands to execute after
          successful backup. User can specify
          more then one of those fields.
  comment - stands for a regular comment, that will be skipped
  label - files section name, separetes files groups
  [no]recursive - specifies wheter to backup files recursively.
          When 'norecursive' is met, then group will not be scanned
          recursively. This is by default.
  dst - supersedes backup_dir or acts as a relative path to the backup_dir
  path - specifies file/directory path to file/files that need
          to be backed up. Path can be relative to the current script's
          directory, or absolute with drive letter.
          Wildcards *, ? allowed. There can be more then one path
          field. This will specify more then one files for example.
  [+/-]exts - preceding plus tells the script to include in backup
          files with specified extension which occured in this list.
          +exts - include files with following extenstions
          -exts - exclude ditto
  [+/-]files - explicit file names to be included/excluded. It is not
          a necessity for this names to contain an extension.
  [+/-]dirs - same as in files field, but concerns directories.
  [+/-]masks - mask to be used as an include/exclude filter.

