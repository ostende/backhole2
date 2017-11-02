AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

AM_CXXFLAGS = \
	$(LIBXINE_CFLAGS)

noinst_LIBRARIES = libenigma_service.a

libenigma_service_a_SOURCES = \
	event.cpp \
	listboxservice.cpp \
	service.cpp \
	servicedvb.cpp \
	servicedvbrecord.cpp \
	servicedvbfcc.cpp \
	servicefs.cpp \
	servicemp3.cpp \
	servicem2ts.cpp \
	servicehdmi.cpp

serviceincludedir = $(pkgincludedir)/lib/service
serviceinclude_HEADERS = \
	event.h \
	iservice.h \
	listboxservice.h \
	service.h \
	servicedvb.h \
	servicedvbrecord.h \
	servicedvbfcc.h \
	servicefs.h \
	servicemp3.h \
	servicem2ts.h \
	servicehdmi.h

if HAVE_LIBXINE
libenigma_service_a_SOURCES += \
	servicexine.cpp
serviceinclude_HEADERS += \
	servicexine.h
endif
