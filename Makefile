PYFILES=Stupid_folder.py process_profiles.py st_psr_helper.py
TARGETS=stupid_simple_pulsar_uhd.py stupid_simple_pulsar.py $(EXTRA_TARGET)
BASESOURCE=stupid_simple_pulsar
SOURCE=$(BASESOURCE).grc
PREFIX=/usr/local
GRCC_CMD=grcc -d .

all: $(TARGETS)

clean:
	rm -rf $(TARGETS) $(BASESOURCE)_uhd.grc $(BASESOURCE)_osmo.grc

stupid_simple_pulsar_uhd.py: $(SOURCE)
	./grc_parser.py $(SOURCE) $(BASESOURCE)_uhd.grc uhd_edits.txt
	$(GRCC_CMD) $(BASESOURCE)_uhd.grc

stupid_simple_pulsar_osmo.py: $(SOURCE)
	./grc_parser.py $(SOURCE) $(BASESOURCE)_osmo.grc osmo_edits.txt
	$(GRCC_CMD) $(BASESOURCE)_osmo.grc

stupid_simple_pulsar.py: $(SOURCE)
	$(GRCC_CMD) $(SOURCE)

install: $(TARGETS)
	cp $(TARGETS) $(PYFILES) $(PREFIX)/bin
	chmod 755 $(PREFIX)/bin/stupid_simple_pulsar*.py
	chmod 755 $(PREFIX)/bin/process_profiles.py
	-ln -s -f $(PREFIX)/bin/stupid_simple_pulsar_uhd.py $(PREFIX)/bin/stupid_simple_pulsar_uhd
	-ln -s -f $(PREFIX)/bin/stupid_simple_pulsar_osmo.py $(PREFIX)/bin/stupid_simple_pulsar_osmo
	-ln -s -f $(PREFIX)/bin/stupid_simple_pulsar.py $(PREFIX)/bin/stupid_simple_pulsar
	ln -s -f $(PREFIX)/bin/process_profiles.py $(PREFIX)/bin/process_profiles
