TARGETS=Stupid_folder.py process_profiles.py stupid_simple_pulsar.py
SOURCE=stupid_simple_pulsar.grc

all: $(TARGETS)

stupid_simple_pulsar.py: $(SOURCE)
	grcc -d . $(SOURCE)
	
install: $(TARGETS)
	cp $(TARGETS) /usr/local/bin
	chmod 755 /usr/local/bin/stupid_simple_pulsar.py
	chmod 755 /usr/local/bin/process_profiles.py
