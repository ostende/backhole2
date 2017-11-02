#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>

// #define FUZZING 1

#if FUZZING
		/* change every 1:FUZZING_PROPABILITY byte */
#define FUZZING_PROPABILITY 100
#endif

#include <linux/dvb/dmx.h>

#ifndef DMX_ADD_PID
#define DMX_ADD_PID		_IOW('o', 51, __u16)
#define DMX_REMOVE_PID		_IOW('o', 52, __u16)
#endif

#include "crc32.h"

#include <lib/base/eerror.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/decoder.h>

eDVBDemux::eDVBDemux(int adapter, int demux): adapter(adapter), demux(demux)
{
	m_dvr_busy = 0;
}

eDVBDemux::~eDVBDemux()
{
}

int eDVBDemux::openDemux(void)
{
	char filename[128];
	snprintf(filename, 128, "/dev/dvb/adapter%d/demux%d", adapter, demux);
	return ::open(filename, O_RDWR);
}

int eDVBDemux::openDVR(int flags)
{
	char filename[128];
	snprintf(filename, 128, "/dev/dvb/adapter%d/dvr%d", adapter, demux);
	return ::open(filename, flags);
}

DEFINE_REF(eDVBDemux)

RESULT eDVBDemux::setSourceFrontend(int fenum)
{
	int fd = openDemux();
	if (fd < 0) return -1;
	int n = DMX_SOURCE_FRONT0 + fenum;
	int res = ::ioctl(fd, DMX_SET_SOURCE, &n);
	if (res)
		eDebug("DMX_SET_SOURCE failed! - %m");
	else
		source = fenum;
	::close(fd);
	return res;
}

RESULT eDVBDemux::setSourcePVR(int pvrnum)
{
	int fd = openDemux();
	if (fd < 0) return -1;
	int n = DMX_SOURCE_DVR0 + pvrnum;
	int res = ::ioctl(fd, DMX_SET_SOURCE, &n);
	source = -1;
	::close(fd);
	return res;
}

RESULT eDVBDemux::createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader)
{
	RESULT res;
	reader = new eDVBSectionReader(this, context, res);
	if (res)
		reader = 0;
	return res;
}

RESULT eDVBDemux::createPESReader(eMainloop *context, ePtr<iDVBPESReader> &reader)
{
	RESULT res;
	reader = new eDVBPESReader(this, context, res);
	if (res)
		reader = 0;
	return res;
}

RESULT eDVBDemux::createTSRecorder(ePtr<iDVBTSRecorder> &recorder)
{
	if (m_dvr_busy)
		return -EBUSY;
	recorder = new eDVBTSRecorder(this);
	return 0;
}

RESULT eDVBDemux::getMPEGDecoder(ePtr<iTSMPEGDecoder> &decoder, int index)
{
	decoder = new eTSMPEGDecoder(this, index);
	return 0;
}

RESULT eDVBDemux::getSTC(pts_t &pts, int num)
{
	int fd = openDemux();
	
	if (fd < 0)
		return -ENODEV;

	struct dmx_stc stc;
	stc.num = num;
	stc.base = 1;
	
	if (ioctl(fd, DMX_GET_STC, &stc) < 0)
	{
		eDebug("DMX_GET_STC failed!");
		::close(fd);
		return -1;
	}
	
	pts = stc.stc;
	
	eDebug("DMX_GET_STC - %lld", pts);
	
	::close(fd);
	return 0;
}

RESULT eDVBDemux::flush()
{
	// FIXME: implement flushing the PVR queue here.
	
	m_event(evtFlush);
	return 0;
}

RESULT eDVBDemux::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

void eDVBSectionReader::data(int)
{
	__u8 data[4096]; // max. section size
	int r;
	r = ::read(fd, data, 4096);
#if FUZZING
	int j;
	for (j = 0; j < r; ++j)
	{
		if (!(rand()%FUZZING_PROPABILITY))
			data[j] ^= rand();
	}
#endif	
	if(r < 0)
	{
		eWarning("ERROR reading section - %m\n");
		return;
	}
	if (checkcrc)
	{
			// this check should never happen unless the driver is crappy!
		unsigned int c;
		if ((c = crc32((unsigned)-1, data, r)))
		{
			eDebug("crc32 failed! is %x\n", c);
			return;
		}
	}
	if (active)
		read(data);
	else
		eDebug("data.. but not active");
}

eDVBSectionReader::eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res): demux(demux)
{
	char filename[128];
	fd = demux->openDemux();
	
	if (fd >= 0)
	{
		notifier=eSocketNotifier::create(context, fd, eSocketNotifier::Read, false);
		CONNECT(notifier->activated, eDVBSectionReader::data);
		res = 0;
	} else
	{
		perror(filename);
		res = errno;
	}
}

DEFINE_REF(eDVBSectionReader)

eDVBSectionReader::~eDVBSectionReader()
{
	if (fd >= 0)
		::close(fd);
}

RESULT eDVBSectionReader::setBufferSize(int size)
{
	int res=::ioctl(fd, DMX_SET_BUFFER_SIZE, size);
	if (res < 0)
		eDebug("eDVBSectionReader DMX_SET_BUFFER_SIZE failed(%m)");
	return res;
}

RESULT eDVBSectionReader::start(const eDVBSectionFilterMask &mask)
{
	RESULT res;
	if (fd < 0)
		return -ENODEV;

	notifier->start();
	dmx_sct_filter_params sct;
	sct.pid     = mask.pid;
	sct.timeout = 0;
	sct.flags   = DMX_IMMEDIATE_START;
#if !FUZZING
	if (mask.flags & eDVBSectionFilterMask::rfCRC)
	{
		sct.flags |= DMX_CHECK_CRC;
		checkcrc = 1;
	} else
#endif
		checkcrc = 0;
	
	memcpy(sct.filter.filter, mask.data, DMX_FILTER_SIZE);
	memcpy(sct.filter.mask, mask.mask, DMX_FILTER_SIZE);
	memcpy(sct.filter.mode, mask.mode, DMX_FILTER_SIZE);
	setBufferSize(8192*8);
	
	res = ::ioctl(fd, DMX_SET_FILTER, &sct);
	if (!res)
	{
		active = 1;
	}
	return res;
}

RESULT eDVBSectionReader::stop()
{
	if (!active)
		return -1;

	active=0;
	::ioctl(fd, DMX_STOP);
	notifier->stop();

	return 0;
}

RESULT eDVBSectionReader::connectRead(const Slot1<void,const __u8*> &r, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, read.connect(r));
	return 0;
}

void eDVBPESReader::data(int)
{
	while (1)
	{
		__u8 buffer[16384];
		int r;
		r = ::read(m_fd, buffer, 16384);
		if (!r)
			return;
		if(r < 0)
		{
			if (errno == EAGAIN || errno == EINTR) /* ok */
				return;
			eWarning("ERROR reading PES (fd=%d) - %m", m_fd);
			return;
		}

		if (m_active)
			m_read(buffer, r);
		else
			eWarning("PES reader not active");
		if (r != 16384)
			break;
	}
}

eDVBPESReader::eDVBPESReader(eDVBDemux *demux, eMainloop *context, RESULT &res): m_demux(demux)
{
	char filename[128];
	m_fd = m_demux->openDemux();
	
	if (m_fd >= 0)
	{
		setBufferSize(64*1024);
		::fcntl(m_fd, F_SETFL, O_NONBLOCK);
		m_notifier = eSocketNotifier::create(context, m_fd, eSocketNotifier::Read, false);
		CONNECT(m_notifier->activated, eDVBPESReader::data);
		res = 0;
	} else
	{
		perror(filename);
		res = errno;
	}
}

RESULT eDVBPESReader::setBufferSize(int size)
{
	int res = ::ioctl(m_fd, DMX_SET_BUFFER_SIZE, size);
	if (res < 0)
		eDebug("eDVBPESReader DMX_SET_BUFFER_SIZE failed(%m)");
	return res;
}

DEFINE_REF(eDVBPESReader)

eDVBPESReader::~eDVBPESReader()
{
	if (m_fd >= 0)
		::close(m_fd);
}

RESULT eDVBPESReader::start(int pid)
{
	RESULT res;
	if (m_fd < 0)
		return -ENODEV;

	m_notifier->start();

	dmx_pes_filter_params flt;
	
	flt.pes_type = DMX_PES_OTHER;
	flt.pid     = pid;
	flt.input   = DMX_IN_FRONTEND;
	flt.output  = DMX_OUT_TAP;
	
	flt.flags   = DMX_IMMEDIATE_START;

	res = ::ioctl(m_fd, DMX_SET_PES_FILTER, &flt);
	
	if (res)
		eWarning("PES filter: DMX_SET_PES_FILTER - %m");
	if (!res)
		m_active = 1;
	return res;
}

RESULT eDVBPESReader::stop()
{
	if (!m_active)
		return -1;

	m_active=0;
	::ioctl(m_fd, DMX_STOP);
	m_notifier->stop();

	return 0;
}

RESULT eDVBPESReader::connectRead(const Slot2<void,const __u8*,int> &r, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_read.connect(r));
	return 0;
}

eDVBRecordFileThread::eDVBRecordFileThread()
	:eFilePushThread(IOPRIO_CLASS_RT, 7), m_ts_parser(m_stream_info)
{
	m_current_offset = 0;
}

void eDVBRecordFileThread::setTimingPID(int pid, int type)
{
	m_ts_parser.setPid(pid, type);
}

void eDVBRecordFileThread::startSaveMetaInformation(const std::string &filename)
{
	m_stream_info.startSave(filename.c_str());
}

void eDVBRecordFileThread::stopSaveMetaInformation()
{
	m_stream_info.stopSave();
}

void eDVBRecordFileThread::enableAccessPoints(bool enable)
{
	m_ts_parser.enableAccessPoints(enable);
}

int eDVBRecordFileThread::getLastPTS(pts_t &pts)
{
	return m_ts_parser.getLastPTS(pts);
}

int eDVBRecordFileThread::filterRecordData(const unsigned char *data, int len, size_t &current_span_remaining)
{
	m_ts_parser.parseData(m_current_offset, data, len);
	
	m_current_offset += len;
	
	return len;
}

DEFINE_REF(eDVBTSRecorder);

eDVBTSRecorder::eDVBTSRecorder(eDVBDemux *demux): m_demux(demux)
{
	m_running = 0;
	m_target_fd = -1;
	m_thread = new eDVBRecordFileThread();
	CONNECT(m_thread->m_event, eDVBTSRecorder::filepushEvent);
}

eDVBTSRecorder::~eDVBTSRecorder()
{
	stop();
	delete m_thread;
}

RESULT eDVBTSRecorder::start()
{
	std::map<int,int>::iterator i(m_pids.begin());

	if (m_running)
		return -1;
	
	if (m_target_fd == -1)
		return -2;

	if (i == m_pids.end())
		return -3;

	char filename[128];
	snprintf(filename, 128, "/dev/dvb/adapter%d/demux%d", m_demux->adapter, m_demux->demux);

	m_source_fd = ::open(filename, O_RDONLY);
	
	if (m_source_fd < 0)
	{
		eDebug("FAILED to open demux (%s) in ts recoder (%m)", filename);
		return -3;
	}

	setBufferSize(1024*1024);

	dmx_pes_filter_params flt;
	flt.pes_type = DMX_PES_OTHER;
	flt.output  = DMX_OUT_TSDEMUX_TAP;
	flt.pid     = i->first;
	++i;
	flt.input   = DMX_IN_FRONTEND;
	flt.flags   = 0;
	int res = ::ioctl(m_source_fd, DMX_SET_PES_FILTER, &flt);
	if (res)
	{
		eDebug("DMX_SET_PES_FILTER: %m");
		::close(m_source_fd);
		m_source_fd = -1;
		return -3;
	}
	
	::ioctl(m_source_fd, DMX_START);

	if (m_target_filename != "")
		m_thread->startSaveMetaInformation(m_target_filename);
	
	m_thread->start(m_source_fd, m_target_fd);
	m_running = 1;

	while (i != m_pids.end()) {
		startPID(i->first);
		++i;
	}

	return 0;
}

RESULT eDVBTSRecorder::setBufferSize(int size)
{
	int res = ::ioctl(m_source_fd, DMX_SET_BUFFER_SIZE, size);
	if (res < 0)
		eDebug("eDVBTSRecorder DMX_SET_BUFFER_SIZE failed(%m)");
	return res;
}

RESULT eDVBTSRecorder::addPID(int pid)
{
	if (m_pids.find(pid) != m_pids.end())
		return -1;
	
	m_pids.insert(std::pair<int,int>(pid, -1));
	if (m_running)
		startPID(pid);
	return 0;
}

RESULT eDVBTSRecorder::removePID(int pid)
{
	if (m_pids.find(pid) == m_pids.end())
		return -1;
		
	if (m_running)
		stopPID(pid);
	
	m_pids.erase(pid);
	return 0;
}

RESULT eDVBTSRecorder::setTimingPID(int pid, int type)
{
	m_thread->setTimingPID(pid, type);
	return 0;
}

RESULT eDVBTSRecorder::setTargetFD(int fd)
{
	m_target_fd = fd;
	return 0;
}

RESULT eDVBTSRecorder::setTargetFilename(const char *filename)
{
	m_target_filename = filename;

	std::string target_path = m_target_filename;
	std::string::size_type filePos = target_path.rfind('/');
	m_thread->setTSPath(target_path.erase(filePos));

	return 0;
}

RESULT eDVBTSRecorder::enableAccessPoints(bool enable)
{
	m_thread->enableAccessPoints(enable);
	return 0;
}

RESULT eDVBTSRecorder::setBoundary(off_t max)
{
	return -1; // not yet implemented
}

RESULT eDVBTSRecorder::setTimeshift(bool enable)
{
	m_thread->setTimeshift(enable);
}

RESULT eDVBTSRecorder::stop()
{
	int state=3;

	for (std::map<int,int>::iterator i(m_pids.begin()); i != m_pids.end(); ++i)
		stopPID(i->first);

	if (!m_running)
		return -1;

	/* workaround for record thread stop */
	if (m_source_fd >= 0)
	{
		if (::ioctl(m_source_fd, DMX_STOP) < 0)
			perror("DMX_STOP");
		else
			state &= ~1;

		if (::close(m_source_fd) < 0)
			perror("close");
		else
			state &= ~2;
		m_source_fd = -1;
	}

	m_thread->stop();

	if (state & 3)
	{
		if (m_source_fd >= 0)
		{
			::close(m_source_fd);
			m_source_fd = -1;
		}
	}

	m_running = 0;
	m_thread->stopSaveMetaInformation();
	return 0;
}

RESULT eDVBTSRecorder::getCurrentPCR(pts_t &pcr)
{
	if (!m_running)
		return 0;
	if (!m_thread)
		return 0;
		/* XXX: we need a lock here */

			/* we don't filter PCR data, so just use the last received PTS, which is not accurate, but better than nothing */
	return m_thread->getLastPTS(pcr);
}

RESULT eDVBTSRecorder::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

RESULT eDVBTSRecorder::startPID(int pid)
{
	while(true) {
		__u16 p = pid;
		if (::ioctl(m_source_fd, DMX_ADD_PID, &p) < 0) {
			perror("DMX_ADD_PID");
			if (errno == EAGAIN || errno == EINTR) {
				eDebug("retry!");
				continue;
			}
		} else
			m_pids[pid] = 1;
		break;
	}
	return 0;
}

void eDVBTSRecorder::stopPID(int pid)
{
	if (m_pids[pid] != -1)
	{
		while(true) {
			__u16 p = pid;
			if (::ioctl(m_source_fd, DMX_REMOVE_PID, &p) < 0) {
				perror("DMX_REMOVE_PID");
				if (errno == EAGAIN || errno == EINTR) {
					eDebug("retry!");
					continue;
				}
			}
			break;
		}
	}
	m_pids[pid] = -1;
}

void eDVBTSRecorder::filepushEvent(int event)
{
	switch (event)
	{
	case eFilePushThread::evtWriteError:
		m_event(eventWriteError);
		break;
	}
}
