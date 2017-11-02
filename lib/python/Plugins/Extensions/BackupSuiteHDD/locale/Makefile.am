PLUGIN = BackupSuiteHDD
LANGS = de es fr it nl pl ru tr

CATEGORY ?= "Extensions"

plugindir = $(libdir)/enigma2/python/Plugins/$(CATEGORY)/$(PLUGIN)

LANGMO = $(LANGS:=.mo)
LANGPO = $(LANGS:=.po)

.po.mo:
	$(MSGFMT) -o $@ $<

BUILT_SOURCES = $(LANGMO)
CLEANFILES = $(LANGMO) $(PLUGIN)-py.pot $(PLUGIN)-xml.pot $(PLUGIN).pot

dist-hook: $(LANGPO)

install-data-local: $(LANGMO)
	for lang in $(LANGS); do \
		$(mkinstalldirs) $(DESTDIR)$(plugindir)/locale/$$lang/LC_MESSAGES; \
		$(INSTALL_DATA) $$lang.mo $(DESTDIR)$(plugindir)/locale/$$lang/LC_MESSAGES/BackupSuite.mo; \
	done

uninstall-local:
	for lang in $(LANGS); do \
		$(RM) $(DESTDIR)$(plugindir)/locale/$$lang/LC_MESSAGES/$$lang.mo; \
	done
