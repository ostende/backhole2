AC_INIT([enigma2],[3.0.0],[enigma2-devel@lists.elitedvb.net])
AM_INIT_AUTOMAKE([dist-bzip2 no-define tar-pax -Wno-portability])
AC_CONFIG_HEADERS([enigma2_config.h])

# Silent rules are available since 1.11, but older versions
# are still in use. So don't use them unconditionally.
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

AC_USE_SYSTEM_EXTENSIONS
AC_SYS_LARGEFILE

AC_PROG_CC
AC_PROG_CXX
m4_ifdef([LT_INIT], [LT_INIT], [AC_PROG_LIBTOOL])
AC_CONFIG_MACRO_DIR([m4])

AC_CHECK_HEADERS([dbox/fp.h dbox/lcd-ks0713.h])

AC_PATH_PROG(MSGFMT, msgfmt, AC_MSG_ERROR(Could not find msgfmt))

AM_PATH_PYTHON
AX_PYTHON_DEVEL
AX_PKG_SWIG
AX_SWIG_ENABLE_CXX
AX_SWIG_PYTHON
AX_PTHREAD

TUXBOX_APPS_DVB

AM_CONDITIONAL(HAVE_GIT_DIR, test -d "$srcdir/.git")
AM_CONDITIONAL(HAVE_FAKE_GIT_DIR, test -f "$srcdir/.git/last_commit_info")

dnl versions of gstreamer and plugins-base
AC_ARG_WITH(gstversion,
        AS_HELP_STRING([--with-gstversion],[use gstreamer version (major.minor)]),
        [GST_MAJORMINOR=$withval],[GST_MAJORMINOR=0.10])

PKG_CHECK_MODULES(BASE, [freetype2 fribidi gstreamer-$GST_MAJORMINOR gstreamer-pbutils-$GST_MAJORMINOR libdvbsi++ libpng libxml-2.0 sigc++-1.2 libssl libcrypto])
PKG_CHECK_MODULES(LIBDDVD, libdreamdvd, HAVE_LIBDDVD="yes", HAVE_LIBDDVD="no")
AM_CONDITIONAL(HAVE_LIBDDVD, test "$HAVE_LIBDDVD" = "yes")

AC_CHECK_LIB([dl], [dlopen], [LIBDL_LIBS="-ldl"], [AC_MSG_ERROR([Could not find libdl])])
AC_SUBST(LIBDL_LIBS)
AC_CHECK_LIB([jpeg], [jpeg_set_defaults], [LIBJPEG_LIBS="-ljpeg"], [AC_MSG_ERROR([Could not find libjpeg])])
AC_SUBST(LIBJPEG_LIBS)
AC_CHECK_LIB([ungif], [DGifOpen], [LIBGIF_LIBS="-lungif"], [AC_CHECK_LIB([gif], [DGifOpen], [LIBGIF_LIBS="-lgif"], [AC_MSG_ERROR([Could not find libgif or libungif])])])
AC_SUBST(LIBGIF_LIBS)

AC_LANG_PUSH([C++])
AC_CHECK_LIB([xmlccwrap], [exit], [LIBXMLCCWRAP_LIBS="-lxmlccwrap"], [AC_MSG_ERROR([Could not find libxmlccwrap])])
AC_SUBST(LIBXMLCCWRAP_LIBS)
AC_LANG_POP

AC_ARG_WITH(remote-keyboard,
        AC_HELP_STRING([--with-remote-keyboard], [use remote keyboard on dvbapp, yes or no]),
        [[withrckbd=$withval]],
        [[withrckbd=no]]
)
if test x"$withrckbd" != xno ; then
        AC_DEFINE(VUPLUS_USE_RCKBD, 1,[Define when using a rc-keyboard on dvbapp])
fi

AC_ARG_WITH(set-right-half-vfd-skin,
        AC_HELP_STRING([--with-set-right-half-vfd-skin], [display right_half_vfd_icons from skin(for ultimo), yes or no]),
        [[setrighthalfvfdskin=$withval]],
        [[setrighthalfvfdskin=no]]
)
if test x"$setrighthalfvfdskin" != xno ; then
        AC_DEFINE(SET_RIGHT_HALF_VFD_SKIN, 1,[Define when display right_half_vfd_icons from skin, for ultimo])
fi
AM_CONDITIONAL(SET_RIGHT_HALF_VFD_SKIN, test x"$setrighthalfvfdskin" != xno)

AC_ARG_WITH(libvugles2,
	AS_HELP_STRING([--with-libvugles2],[use libvugles2, yes or no]),
	[with_libvugles2=$withval],[with_libvugles2=no])
if test "$with_libvugles2" = "yes"; then
	PKG_CHECK_MODULES(LIBVUGLES2, [libvugles2])
	GLES_CFLAGS="-DUSE_LIBVUGLES2"
fi
AM_CONDITIONAL(HAVE_LIBVUGLES2, test "$with_libvugles2" = "yes")

AC_ARG_WITH(libsdl,
	AS_HELP_STRING([--with-libsdl],[use libsdl, yes or no]),
	[with_libsdl=$withval],[with_libsdl=no])
if test "$with_libsdl" = "yes"; then
	PKG_CHECK_MODULES(LIBSDL, sdl)
fi
AM_CONDITIONAL(HAVE_LIBSDL, test "$with_libsdl" = "yes")

AC_ARG_WITH(libxine,
	AS_HELP_STRING([--with-libxine],[use libxine, yes or no]),
	[with_libxine=$withval],[with_libxine=no])
if test "$with_libxine" = "yes"; then
	PKG_CHECK_MODULES(LIBXINE, libxine)
	AC_DEFINE([WITH_XINE],[1],[Define to 1 if you have libxine])
fi
AM_CONDITIONAL(HAVE_LIBXINE, test "$with_libxine" = "yes")

AC_ARG_WITH(debug,
	AS_HELP_STRING([--without-debug],[disable debugging code]),
	[with_debug="$withval"],[with_debug="yes"])
if test "$with_debug" = "yes"; then
	DEBUG_CFLAGS="-ggdb3"
	AC_DEFINE([DEBUG],[1],[Define to 1 to enable debugging code])
fi

AC_ARG_WITH(memcheck,
	AS_HELP_STRING([--with-memcheck],[enable memory leak checks]),
	[with_memcheck="$withval"],[with_memcheck="no"])
if test "$with_memcheck" = "yes"; then
	AC_DEFINE([MEMLEAK_CHECK],[1],[Define to 1 to enable memory leak checks])
fi

AC_ARG_WITH(po,
	AS_HELP_STRING([--with-po],[enable updating of po files]),
	[with_po="$withval"],[with_po="no"])
if test "$with_po" = "yes"; then
	AC_PATH_PROG(MSGINIT, msginit)
	AC_PATH_PROG(MSGMERGE, msgmerge)
	AC_PATH_PROG(MSGUNIQ, msguniq)
	AC_PATH_PROG(XGETTEXT, xgettext)
	if test -z "$MSGINIT" -o -z "$MSGMERGE" -o -z "$MSGUNIQ" -o -z "$XGETTEXT"; then
		AC_MSG_ERROR([Could not find required gettext tools])
	fi
fi
AM_CONDITIONAL(UPDATE_PO, test "$with_po" = "yes")

ENIGMA2_CFLAGS="-fno-rtti -fno-exceptions"
AC_SUBST(ENIGMA2_CFLAGS)

CPPFLAGS="$CPPFLAGS $PYTHON_CPPFLAGS"
CFLAGS="$CFLAGS $DEBUG_CFLAGS -Wall"
CXXFLAGS="$CXXFLAGS $DEBUG_CFLAGS -Wall $BASE_CFLAGS $ENIGMA2_CFLAGS $PTHREAD_CFLAGS $GLES_CFLAGS"

AC_CONFIG_FILES([
Makefile
data/Makefile
data/fonts/Makefile
data/countries/Makefile
data/defaults/Makefile
data/extensions/Makefile
data/keymaps/Makefile
data/skin_default/Makefile
data/skin_default/menu/Makefile
data/skin_default/icons/Makefile
data/skin_default/buttons/Makefile
data/skin_default/spinner/Makefile
include/Makefile
lib/Makefile
lib/actions/Makefile
lib/base/Makefile
lib/base/eenv.cpp
lib/driver/Makefile
lib/dvb/Makefile
lib/dvb/lowlevel/Makefile
lib/dvb_ci/Makefile
lib/gdi/Makefile
lib/gui/Makefile
lib/mmi/Makefile
lib/nav/Makefile
lib/python/Makefile
lib/python/Blackhole/Makefile
lib/python/Components/Makefile
lib/python/Components/Converter/Makefile
lib/python/Components/Renderer/Makefile
lib/python/Components/Sources/Makefile
lib/python/Screens/Makefile
lib/python/Plugins/Makefile
lib/python/Plugins/Extensions/CutListEditor/Makefile
lib/python/Plugins/Extensions/CutListEditor/meta/Makefile
lib/python/Plugins/Extensions/DVDBurn/Makefile
lib/python/Plugins/Extensions/DVDBurn/meta/Makefile
lib/python/Plugins/Extensions/DVDPlayer/Makefile
lib/python/Plugins/Extensions/DVDPlayer/meta/Makefile
lib/python/Plugins/Extensions/DVDPlayer/src/Makefile
lib/python/Plugins/Extensions/GraphMultiEPG/Makefile
lib/python/Plugins/Extensions/GraphMultiEPG/meta/Makefile
lib/python/Plugins/Extensions/Makefile
lib/python/Plugins/Extensions/MediaPlayer/Makefile
lib/python/Plugins/Extensions/MediaPlayer/meta/Makefile
lib/python/Plugins/Extensions/MediaScanner/Makefile
lib/python/Plugins/Extensions/MediaScanner/meta/Makefile
lib/python/Plugins/Extensions/Modem/Makefile
lib/python/Plugins/Extensions/PicturePlayer/Makefile
lib/python/Plugins/Extensions/PicturePlayer/meta/Makefile
lib/python/Plugins/Extensions/PicturePlayer/data/Makefile
lib/python/Plugins/Extensions/SocketMMI/Makefile
lib/python/Plugins/Extensions/SocketMMI/meta/Makefile
lib/python/Plugins/Extensions/SocketMMI/src/Makefile
lib/python/Plugins/Extensions/TuxboxPlugins/Makefile
lib/python/Plugins/Extensions/TuxboxPlugins/meta/Makefile
lib/python/Plugins/Extensions/WebBrowser/Makefile
lib/python/Plugins/Extensions/WebBrowser/meta/Makefile
lib/python/Plugins/Extensions/WebBrowser/keymap/Makefile
lib/python/Plugins/Extensions/WebBrowser/desc/Makefile
lib/python/Plugins/Extensions/DLNAServer/Makefile
lib/python/Plugins/Extensions/DLNAServer/meta/Makefile
lib/python/Plugins/Extensions/DLNABrowser/Makefile
lib/python/Plugins/Extensions/DLNABrowser/meta/Makefile
lib/python/Plugins/Extensions/HbbTV/Makefile
lib/python/Plugins/Extensions/HbbTV/meta/Makefile
lib/python/Plugins/Extensions/HbbTV/locale/Makefile
lib/python/Plugins/Extensions/BackupSuiteHDD/Makefile
lib/python/Plugins/Extensions/BackupSuiteHDD/meta/Makefile
lib/python/Plugins/Extensions/BackupSuiteHDD/locale/Makefile
lib/python/Plugins/Extensions/BackupSuiteUSB/Makefile
lib/python/Plugins/Extensions/BackupSuiteUSB/meta/Makefile
lib/python/Plugins/Extensions/SatipClient/Makefile
lib/python/Plugins/Extensions/SatipClient/meta/Makefile
lib/python/Plugins/Extensions/MiniTV/Makefile
lib/python/Plugins/Extensions/MiniTV/meta/Makefile
lib/python/Plugins/SystemPlugins/CleanupWizard/Makefile
lib/python/Plugins/SystemPlugins/CleanupWizard/meta/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/meta/Makefile
lib/python/Plugins/SystemPlugins/CrashlogAutoSubmit/Makefile
lib/python/Plugins/SystemPlugins/CrashlogAutoSubmit/meta/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/meta/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/meta/Makefile
lib/python/Plugins/SystemPlugins/FrontprocessorUpgrade/Makefile
lib/python/Plugins/SystemPlugins/FrontprocessorUpgrade/meta/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/meta/Makefile
lib/python/Plugins/SystemPlugins/Makefile
lib/python/Plugins/SystemPlugins/TempFanControl/Makefile
lib/python/Plugins/SystemPlugins/TempFanControl/meta/Makefile
lib/python/Plugins/SystemPlugins/NetworkWizard/Makefile
lib/python/Plugins/SystemPlugins/NetworkWizard/meta/Makefile
lib/python/Plugins/SystemPlugins/NFIFlash/Makefile
lib/python/Plugins/SystemPlugins/NFIFlash/meta/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/meta/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/meta/Makefile
lib/python/Plugins/SystemPlugins/SkinSelector/Makefile
lib/python/Plugins/SystemPlugins/SkinSelector/meta/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/meta/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/meta/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/meta/Makefile
lib/python/Plugins/SystemPlugins/Videomode/Makefile
lib/python/Plugins/SystemPlugins/Videomode/meta/Makefile
lib/python/Plugins/SystemPlugins/WirelessLan/Makefile
lib/python/Plugins/SystemPlugins/WirelessLan/meta/Makefile
lib/python/Plugins/SystemPlugins/Fancontrol/Makefile
lib/python/Plugins/SystemPlugins/Fancontrol/meta/Makefile
lib/python/Plugins/SystemPlugins/FPGAUpgrade/Makefile
lib/python/Plugins/SystemPlugins/FPGAUpgrade/meta/Makefile
lib/python/Plugins/SystemPlugins/WirelessLanSetup/Makefile
lib/python/Plugins/SystemPlugins/WirelessLanSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/ManualFancontrol/Makefile
lib/python/Plugins/SystemPlugins/ManualFancontrol/meta/Makefile
lib/python/Plugins/SystemPlugins/Blindscan/Makefile
lib/python/Plugins/SystemPlugins/Blindscan/meta/Makefile
lib/python/Plugins/SystemPlugins/RemoteControlCode/Makefile
lib/python/Plugins/SystemPlugins/RemoteControlCode/meta/Makefile
lib/python/Plugins/SystemPlugins/UI3DSetup/Makefile
lib/python/Plugins/SystemPlugins/UI3DSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/UIPositionSetup/Makefile
lib/python/Plugins/SystemPlugins/UIPositionSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/HDMICEC/Makefile
lib/python/Plugins/SystemPlugins/HDMICEC/components/Makefile
lib/python/Plugins/SystemPlugins/HDMICEC/meta/Makefile
lib/python/Plugins/SystemPlugins/LEDBrightnessSetup/Makefile
lib/python/Plugins/SystemPlugins/LEDBrightnessSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/FirmwareUpgrade/Makefile
lib/python/Plugins/SystemPlugins/FirmwareUpgrade/meta/Makefile
lib/python/Plugins/SystemPlugins/CrashReport/Makefile
lib/python/Plugins/SystemPlugins/CrashReport/meta/Makefile
lib/python/Plugins/SystemPlugins/3GModemManager/Makefile
lib/python/Plugins/SystemPlugins/3GModemManager/meta/Makefile
lib/python/Plugins/SystemPlugins/3GModemManager/script/Makefile
lib/python/Plugins/SystemPlugins/WirelessAccessPoint/Makefile
lib/python/Plugins/SystemPlugins/WirelessAccessPoint/meta/Makefile
lib/python/Plugins/SystemPlugins/ZappingModeSelection/Makefile
lib/python/Plugins/SystemPlugins/ZappingModeSelection/meta/Makefile
lib/python/Plugins/SystemPlugins/DeviceManager/Makefile
lib/python/Plugins/SystemPlugins/DeviceManager/meta/Makefile
lib/python/Plugins/SystemPlugins/DeviceManager/locale/Makefile
lib/python/Plugins/SystemPlugins/TransCodingSetup/Makefile
lib/python/Plugins/SystemPlugins/TransCodingSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/TransCodingSetup/locale/Makefile
lib/python/Plugins/SystemPlugins/WOLSetup/Makefile
lib/python/Plugins/SystemPlugins/WOLSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/NetDrive/Makefile
lib/python/Plugins/SystemPlugins/NetDrive/meta/Makefile
lib/python/Plugins/SystemPlugins/AudioEffect/Makefile
lib/python/Plugins/SystemPlugins/AudioEffect/meta/Makefile
lib/python/Plugins/SystemPlugins/AnimationSetup/Makefile
lib/python/Plugins/SystemPlugins/AnimationSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/BoxModeConfig/Makefile
lib/python/Plugins/SystemPlugins/BoxModeConfig/meta/Makefile
lib/python/Plugins/SystemPlugins/Solo4kMiscControl/Makefile
lib/python/Plugins/SystemPlugins/Solo4kMiscControl/meta/Makefile
lib/python/Plugins/SystemPlugins/FastChannelChange/Makefile
lib/python/Plugins/SystemPlugins/FastChannelChange/meta/Makefile
lib/python/Plugins/SystemPlugins/Ultimo4kMiscControl/Makefile
lib/python/Plugins/SystemPlugins/Ultimo4kMiscControl/meta/Makefile
lib/python/Plugins/SystemPlugins/PvrDescrambleConvert/Makefile
lib/python/Plugins/SystemPlugins/PvrDescrambleConvert/meta/Makefile
lib/python/Plugins/Extensions/QuadPiP/Makefile
lib/python/Plugins/Extensions/QuadPiP/meta/Makefile
lib/python/Tools/Makefile
lib/service/Makefile
lib/components/Makefile
po/Makefile
main/Makefile
tools/Makefile
tools/enigma2.sh
enigma2.pc
])
AC_DEFINE(BUILD_VUPLUS,1,[Define to 1 for vuplus])
AC_OUTPUT
