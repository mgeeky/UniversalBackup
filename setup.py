from distutils.core import setup
import py2exe
setup(
	#console = ["UniversalBackup.py"],
	windows = ["UniversalBackup.py"],
	zipfile = None,	# we don't need a `library.zip` file.
	options = { 
		"py2exe" : { 
			'optimize':2, 
			"bundle_files":1
		},
	}
)
