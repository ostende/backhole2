import os, mimetypes

from twisted.internet import reactor
from twisted.mail import smtp, relaymanager

from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart

g_config_after_file_status = ""

def getMailExchange(H):
    def cbMX(mxRecord):
        return str(mxRecord.name)
    return relaymanager.MXCalculator().getMX(H).addCallback(cbMX)

def getLogList(d):
    l = []
    if d is None or d == "":
        return l
    try:
        for f in os.listdir(d):
            if f.startswith("enigma2_crash_") and f.endswith(".log"):
                print "[CrashReport] found : ", os.path.basename(f)
                l.append(d + '/' + f)
    except:
        pass
    return l

def sendEmail(F, T, M, S="", FL=[]):
    def cbError(e):
        print "[CrashReport] Error >> \n", e.getErrorMessage()
        reactor.stop()

    def cbSuccess(r):
        print "[CrashReport] Success >> after action : [%s], success message : [%s]" % (g_config_after_file_status, r)
        global g_config_after_file_status
        for f in FL:
            if f.startswith("/tmp/"):
		continue
            if g_config_after_file_status == "rename":
		n = "%s/%s.summited" % (os.path.dirname(f), os.path.basename(f))
		print "[CrashReport] rename : [%s] to [%s]" % (f,n)
                os.rename(f, n)
            elif g_config_after_file_status == "delete":
		print "[CrashReport] remove : [%s]" % (f)
                os.remove(f)
        reactor.stop()

    def cbSend(H):
        context = MIMEMultipart('alternative')
        context['From']    = F
        context['To']      = T
        context['Subject'] = S
	#context['Date']    = smtp.rfc822date()
	context['MIME-Version'] = '1.0'
        context.attach(MIMEText(M, 'plain'))

        for f in FL:
            ctype, encoding = mimetypes.guess_type(f)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            tmp = MIMEBase(maintype, subtype)
            tmp.set_payload(file(f).read())
            Encoders.encode_base64(tmp)
    
            tmp.add_header("Content-Transfer-Encoding", 'base64')
            tmp.add_header('Content-Disposition', 'attachment', filename=os.path.basename(f))
            tmp.add_header('Content-Description', 'vuplus crashlog')
            context.attach(tmp)

        print "[CrashReport] host:[%s], from:[%s], to:[%s]" % (H, F, T)
        sending = smtp.sendmail(str(H), F, T, context.as_string())
        sending.addCallback(cbSuccess).addErrback(cbError)
    return getMailExchange(T.split("@")[1]).addCallback(cbSend)

def doSummit(summitTo, summitFrom, summitName, afterFileStatus="rename"):
    fileList = getLogList('/media/hdd')
    if len(fileList) == 0:
        return

    fileListLen = len(fileList)
    if os.path.exists("/tmp/machine.info"):
        fileList.append("/tmp/machine.info")

    global g_config_after_file_status
    g_config_after_file_status = afterFileStatus
    summitText  = "There are %d crash logs found for you.\n" % (fileListLen)
    if summitName is not None or summitName != "":
        summitText += "\nSubmitter : %s (%s)\n" % (summitName, summitFrom)
    summitText += "\nThis is an automatically generated email from the CrashlogReport-Plugin.\nGood luck.\n"
    summitSubject = "Submit automatically generated crashlog."
    sendEmail(summitFrom, summitTo, summitText, summitSubject, fileList)
    reactor.run()

import sys
print "[CrashReport] argvs : ", sys.argv
if len(sys.argv) == 4:
	doSummit(summitTo='vuplus@code.vuplus.com', summitFrom=sys.argv[1], summitName=sys.argv[2], afterFileStatus=sys.argv[3])

