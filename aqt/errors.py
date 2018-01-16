# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import sys, traceback
import html

from anki.lang import _
from aqt.qt import *
from aqt.utils import showText, showWarning

if not os.environ.get("DEBUG"):
    def excepthook(etype,val,tb):
        sys.stderr.write("Caught exception:\n%s%s\n" % (
            ''.join(traceback.format_tb(tb)),
            '{0}: {1}'.format(etype, val)))
    sys.excepthook = excepthook

class ErrorHandler(QObject):
    "Catch stderr and write into buffer."
    ivl = 100

    errorTimer = pyqtSignal()

    def __init__(self, mw):
        QObject.__init__(self, mw)
        self.mw = mw
        self.timer = None
        self.errorTimer.connect(self._setTimer)
        self.pool = ""
        self._oldstderr = sys.stderr
        sys.stderr = self

    def unload(self):
        sys.stderr = self._oldstderr
        sys.excepthook = None

    def write(self, data):
        # dump to stdout
        sys.stdout.write(data)
        # save in buffer
        self.pool += data
        # and update timer
        self.setTimer()

    def setTimer(self):
        # we can't create a timer from a different thread, so we post a
        # message to the object on the main thread
        self.errorTimer.emit()

    def _setTimer(self):
        if not self.timer:
            self.timer = QTimer(self.mw)
            self.timer.timeout.connect(self.onTimeout)
        self.timer.setInterval(self.ivl)
        self.timer.setSingleShot(True)
        self.timer.start()

    def tempFolderMsg(self):
        return _("""\
The permissions on your system's temporary folder are incorrect, and Anki is \
not able to correct them automatically. Please search for 'temp folder' in the \
Anki manual for more information.""")

    def onTimeout(self):
        error = html.escape(self.pool)
        self.pool = ""
        self.mw.progress.clear()
        if "abortSchemaMod" in error:
            return
        if "10013" in error:
            return showWarning(_("Your firewall or antivirus program is preventing Anki from creating a connection to itself. Please add an exception for Anki."))
        if "Pyaudio not" in error:
            return showWarning(_("Please install PyAudio"))
        if "install mplayer" in error:
            return showWarning(_("Sound and video on cards will not function until mpv or mplayer is installed."))
        if "no default input" in error.lower():
            return showWarning(_("Please connect a microphone, and ensure "
                                 "other programs are not using the audio device."))
        if "invalidTempFolder" in error:
            return showWarning(self.tempFolderMsg())
        if "Beautiful Soup is not an HTTP client" in error:
            return
        if "disk I/O error" in error:
            return showWarning(_("""\
An error occurred while accessing the database.

Possible causes:

- Antivirus, firewall, backup, or synchronization software may be \
  interfering with Anki. Try disabling such software and see if the \
  problem goes away.
- Your disk may be full.
- The Documents/Anki folder may be on a network drive.
- Files in the Documents/Anki folder may not be writeable.
- Your hard disk may have errors.

It's a good idea to run Tools>Check Database to ensure your collection \
is not corrupt.
"""))

        stdText = _("""\
<h1>Error</h1>

<p>An error occurred. Please use <b>Tools &gt; Check Database</b> to see if \
that fixes the problem.</p>

<p>If problems persist, please report the problem on our \
<a href="https://help.ankiweb.net">support site</a>. Please copy and paste \
 the information below into your report.</p>""")

        pluginText = _("""\
<h1>Error</h1>

<p>An error occurred. Please start Anki while holding down the shift \
key, which will temporarily disable the add-ons you have installed.</p>

<p>If the issue only occurs when add-ons are enabled, please use the \
Tools&gt;Add-ons menu item to disable some add-ons and restart Anki, \
repeating until you discover the add-on that is causing the problem.</p>

<p>When you've discovered the add-on that is causing the problem, please \
report the issue on the <a href="https://help.ankiweb.net/discussions/add-ons/">\
add-ons section</a> of our support site.

<p>Debug info:</p>
""")
        if self.mw.addonManager.dirty:
            txt = pluginText
        else:
            txt = stdText
        # show dialog
        error = self._supportText() + "\n" + error

        txt = txt + "<div style='white-space: pre-wrap'>" + error + "</div>"
        showText(txt, type="html")

    def _supportText(self):
        import platform
        from aqt import appVersion

        if isWin:
            platname = "Windows " + platform.win32_ver()[0]
        elif isMac:
            platname = "Mac " + platform.mac_ver()[0]
        else:
            platname = "Linux"

        return """\
Anki {} Python {} Qt {} PyQt {}
Platform: {}
Flags: frz={} ao={}        
""".format(appVersion, platform.python_version(), QT_VERSION_STR, PYQT_VERSION_STR, platname,
           getattr(sys, "frozen", False), self.mw.addonManager.dirty)
