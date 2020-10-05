import yaml
import sys
import os

#
# List of named blocks that need a type-spec update
#
blklist = sys.argv[2]
blklist = blklist.split(",")

#
# Open the input file
#
fn = sys.argv[1]
fp = open(fn, 'r')

# Check for not-XML
#
first=fp.readline()
fp.close()

if ("?xml" in first):
	sys.stdout.write("Input file: %s is likely XML--doing nothing\n" % sys.argv[1])
	os.exit(0)

#
# Re-open, load YAML
#
fp= open(fn, "r")
top = yaml.load(fp)
fp.close()

#
# Iterate through the "blocks" section
#
for blk in top['blocks']:
	#
	# Name of block matches? Update
	#
    if blk['name'] in blklist:
		blk['parameters']['type'] = 'str'

#
# Open outfile file and dump
#    
newfp = open(sys.argv[3], "w")
yaml.dump(top, newfp)
newfp.close()
