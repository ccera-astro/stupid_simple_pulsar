PYFILES=Stupid_folder.py process_profiles.py stupid_simple_pulsar.py
TARGETS=stupid_simple_pulsar.py
SOURCE=stupid_simple_pulsar.grc
PREFIX=/usr/local
GRCC_CMD=grcc -d .

all: $(PYFILES)

clean:
	rm -rf $(TARGETS)

stupid_simple_pulsar.py: $(SOURCE)
	$(GRCC_CMD) $(SOURCE)
	
install: $(TARGETS)
	cp $(TARGETS) $(PREFIX)/bin
	chmod 755 $(PREFIX)/bin/stupid_simple_pulsar.py
	chmod 755 $(PREFIX)/bin/process_profiles.py
	ln -s $(PREFIX)/bin/stupid_simple_pulsar.py $(PREFIX)/bin/stupid_simple_pulsar
	ln -s $(PREFIX)/bin/process_profiles.py $(PREFIX)/bin/process_profiles
