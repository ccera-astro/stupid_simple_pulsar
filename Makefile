PYFILES=Stupid_folder.py process_profiles.py st_psr_helper.py psr_display_helper.py
TARGETS=stupid_simple_pulsar_uhd.py stupid_simple_pulsar.py $(EXTRA_TARGET) profile_display.py
BASESOURCE=stupid_simple_pulsar
SOURCE=$(BASESOURCE).grc
PREFIX=/usr/local
GRCC_CMD=grcc -d .

all: $(TARGETS)

ata: stupid_simple_pulsar.grc
# Such ugly wow
	sed -e 's/value>string/value>str/' < $(SOURCE) >$(SOURCE).tmp
	mv $(SOURCE).tmp $(SOURCE)
	grcc stupid_simple_pulsar.grc
	grcc profile_display.grc

ata_install:
	cp stupid_simple_pulsar.py $(PYFILES) profile_display.py /usr/local/bin
	ln -s -f /usr/local/bin/stupid_simple_pulsar.py /usr/local/bin/stupid_simple_pulsar
	ln -s -f /usr/local/bin/process_profiles.py /usr/local/bin/process_profiles
	ln -s -f /usr/local/bin/profile_display.py /usr/local/bin/profile_display

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

profile_display.py: profile_display.grc
	$(GRCC_CMD) profile_display.grc

install: $(TARGETS)
	cp $(TARGETS) $(PYFILES) $(PREFIX)/bin
	chmod 755 $(PREFIX)/bin/stupid_simple_pulsar*.py
	chmod 755 $(PREFIX)/bin/process_profiles.py
	chmod 755 $(PREFIX)/bin/profile_display.py
	-ln -s -f $(PREFIX)/bin/stupid_simple_pulsar_uhd.py $(PREFIX)/bin/stupid_simple_pulsar_uhd
	-ln -s -f $(PREFIX)/bin/stupid_simple_pulsar_osmo.py $(PREFIX)/bin/stupid_simple_pulsar_osmo
	-ln -s -f $(PREFIX)/bin/stupid_simple_pulsar.py $(PREFIX)/bin/stupid_simple_pulsar
	-ln -s -f $(PREFIX)/bin/profile_display.py $(PREFIX)/bin/profile_display
	ln -s -f $(PREFIX)/bin/process_profiles.py $(PREFIX)/bin/process_profiles
