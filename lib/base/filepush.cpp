#include <lib/base/filepush.h>
#include <lib/base/eerror.h>
#include <lib/base/nconfig.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/vfs.h>
#if 0
#include <dirent.h>
#else
#include <sys/types.h>
#endif

#define PVR_COMMIT 1

#define MAJORSD_	8
#define MAJORMMCBLK	179
#define LIMIT_FILESIZE_NOHDD	2*1024*1024*1024LL	// 2GBytes

//FILE *f = fopen("/log.ts", "wb");
static bool g_is_diskfull = false;

eFilePushThread::eFilePushThread(int io_prio_class, int io_prio_level, int blocksize)
	:prio_class(io_prio_class), prio(io_prio_level), m_messagepump(eApp, 0)
{
	m_stop = 0;
	m_sg = 0;
	m_send_pvr_commit = 0;
	m_stream_mode = 0;
	m_blocksize = blocksize;
	flush();
	enablePVRCommit(0);
	CONNECT(m_messagepump.recv_msg, eFilePushThread::recvEvent);
	m_is_timeshift = false;
	m_hdd_connected = true;
}

static void signal_handler(int x)
{
}

void eFilePushThread::thread()
{
	setIoPrio(prio_class, prio);

	off_t dest_pos = 0;
	size_t bytes_read = 0;
	
	off_t current_span_offset = 0;
	size_t current_span_remaining = 0;
	
	size_t written_since_last_sync = 0;

#if 0
	DIR *tsdir_info;
	struct dirent *tsdir_entry;
	tsdir_info = opendir("/sys/block");
	if (tsdir_info != NULL) {
		m_hdd_connected = false;
		while (tsdir_entry = readdir(tsdir_info)) {
			if (strncmp(tsdir_entry->d_name, "sd", 2) == 0) {
				eDebug("HDD found: %s", tsdir_entry->d_name);
				m_hdd_connected = true;
				break;
			}
		}
	}
#else
	if (m_tspath.empty())
		defaultTSPath(m_is_timeshift);

	struct stat tspath_st;
	if (stat(m_tspath.c_str(), &tspath_st) == 0) {
		if (major(tspath_st.st_dev) == MAJORSD_) {
			eDebug("%s location on HDD!", m_tspath.c_str());
			m_hdd_connected = true;
		} else if (major(tspath_st.st_dev) == MAJORMMCBLK) {
			eDebug("%s location on eMMC!", m_tspath.c_str());
			m_hdd_connected = false;
		} else {
			eDebug("%s location on other device", m_tspath.c_str());
		}
	} else {
		eDebug("stat failed!");
	}
#endif

	eDebug("FILEPUSH THREAD START");
	
		/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
	
	hasStarted();

		/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
			/* first try flushing the bufptr */
		if (m_buf_start != m_buf_end)
		{
				/* filterRecordData wants to work on multiples of blocksize.
				   if it returns a negative result, it means that this many bytes should be skipped
				   *in front* of the buffer. Then, it will be called again. with the newer, shorter buffer.
				   if filterRecordData wants to skip more data then currently available, it must do that internally.
				   Skipped bytes will also not be output.

				   if it returns a positive result, that means that only these many bytes should be used
				   in the buffer. 
				   
				   In either case, current_span_remaining is given as a reference and can be modified. (Of course it 
				   doesn't make sense to decrement it to a non-zero value unless you return 0 because that would just
				   skip some data). This is probably a very special application for fast-forward, where the current
				   span is to be cancelled after a complete iframe has been output.

				   we always call filterRecordData with our full buffer (otherwise we couldn't easily strip from the end)
				   
				   we filter data only once, of course, but it might not get immediately written.
				   that's what m_filter_end is for - it points to the start of the unfiltered data.
				*/
			
			int filter_res;
			
			do
			{
				filter_res = filterRecordData(m_buffer + m_filter_end, m_buf_end - m_filter_end, current_span_remaining);

				if (filter_res < 0)
				{
					eDebug("[eFilePushThread] filterRecordData re-syncs and skips %d bytes", -filter_res);
					m_buf_start = m_filter_end + -filter_res;  /* this will also drop unwritten data */
					ASSERT(m_buf_start <= m_buf_end); /* otherwise filterRecordData skipped more data than available. */
					continue; /* try again */
				}
				
					/* adjust end of buffer to strip dropped tail bytes */
				m_buf_end = m_filter_end + filter_res;
					/* mark data as filtered. */
				m_filter_end = m_buf_end;
			} while (0);
			
			ASSERT(m_filter_end == m_buf_end);
			
			if (m_buf_start == m_buf_end)
				continue;

				/* now write out data. it will be 'aligned' (according to filterRecordData). 
				   absolutely forbidden is to return EINTR and consume a non-aligned number of bytes. 
				*/
			int w = write(m_fd_dest, m_buffer + m_buf_start, m_buf_end - m_buf_start);
//			fwrite(m_buffer + m_buf_start, 1, m_buf_end - m_buf_start, f);
//			eDebug("wrote %d bytes", w);
			if (w <= 0)
			{
				if (w < 0 && (errno == EINTR || errno == EAGAIN || errno == EBUSY))
					continue;
				eDebug("eFilePushThread WRITE ERROR");
				sendEvent(evtWriteError);

				struct statfs fs;
				if (statfs(m_tspath.c_str(), &fs) < 0) {
					eDebug("statfs failed!");
				}
				if ((off_t)fs.f_bavail < 1) {
					eDebug("not enough diskspace!");
					g_is_diskfull = true;
				}
				break;
				// ... we would stop the thread
			}

			written_since_last_sync += w;

			if (written_since_last_sync >= 512*1024)
			{
				int toflush = written_since_last_sync > 2*1024*1024 ?
					2*1024*1024 : written_since_last_sync &~ 4095; // write max 2MB at once
				dest_pos = lseek(m_fd_dest, 0, SEEK_CUR);
				dest_pos -= toflush;
				posix_fadvise(m_fd_dest, dest_pos, toflush, POSIX_FADV_DONTNEED);
				written_since_last_sync -= toflush;
			}

//			printf("FILEPUSH: wrote %d bytes\n", w);
			m_buf_start += w;
			continue;
		}

		if (!m_hdd_connected) {
			struct stat limit_filesize;
			if (fstat(m_fd_dest, &limit_filesize) == 0) {
				if (limit_filesize.st_size > LIMIT_FILESIZE_NOHDD) {
					eDebug("eFilePushThread %lld > %lld LIMIT FILESIZE", limit_filesize.st_size, LIMIT_FILESIZE_NOHDD);
					sendEvent(evtWriteError);

					g_is_diskfull = true;
					break;
				}
			}
		}

			/* now fill our buffer. */
			
		if (m_sg && !current_span_remaining)
		{
			m_sg->getNextSourceSpan(m_current_position, bytes_read, current_span_offset, current_span_remaining);
			ASSERT(!(current_span_remaining % m_blocksize));
			m_current_position = current_span_offset;
			bytes_read = 0;
		}

		size_t maxread = sizeof(m_buffer);
		
			/* if we have a source span, don't read past the end */
		if (m_sg && maxread > current_span_remaining)
			maxread = current_span_remaining;

			/* align to blocksize */
		maxread -= maxread % m_blocksize;

		m_buf_start = 0;
		m_filter_end = 0;
		m_buf_end = 0;

		if (maxread)
			m_buf_end = m_source->read(m_current_position, m_buffer, maxread);

		if (m_buf_end < 0)
		{
			m_buf_end = 0;
			if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
				continue;
			if (errno == EOVERFLOW)
			{
				eWarning("OVERFLOW while recording");
				continue;
			}
			eDebug("eFilePushThread *read error* (%m) - not yet handled");
		}

			/* a read might be mis-aligned in case of a short read. */
		int d = m_buf_end % m_blocksize;
		if (d)
			m_buf_end -= d;

		if (m_buf_end == 0)
		{
				/* on EOF, try COMMITting once. */
			if (m_send_pvr_commit)
			{
				struct pollfd pfd;
				pfd.fd = m_fd_dest;
				pfd.events = POLLIN;
				switch (poll(&pfd, 1, 250)) // wait for 250ms
				{
					case 0:
						eDebug("wait for driver eof timeout");
						continue;
					case 1:
						eDebug("wait for driver eof ok");
						break;
					default:
						eDebug("wait for driver eof aborted by signal");
						continue;
				}
			}
			
				/* in stream_mode, we are sending EOF events 
				   over and over until somebody responds.
				   
				   in stream_mode, think of evtEOF as "buffer underrun occured". */
			sendEvent(evtEOF);

			if (m_stream_mode)
			{
				eDebug("reached EOF, but we are in stream mode. delaying 1 second.");
				sleep(1);
				continue;
			}
			break;
		} else
		{
			m_current_position += m_buf_end;
			bytes_read += m_buf_end;
			if (m_sg)
				current_span_remaining -= m_buf_end;
		}
//		printf("FILEPUSH: read %d bytes\n", m_buf_end);

		if (g_is_diskfull) {
			sendEvent(evtUser+3);
			g_is_diskfull = false;
		}
	}
	fdatasync(m_fd_dest);

	eDebug("FILEPUSH THREAD STOP");
}

void eFilePushThread::start(int fd, int fd_dest)
{
	eRawFile *f = new eRawFile();
	ePtr<iTsSource> source = f;
	f->setfd(fd);
	start(source, fd_dest);
}

int eFilePushThread::start(const char *file, int fd_dest)
{
	eRawFile *f = new eRawFile();
	ePtr<iTsSource> source = f;
	if (f->open(file) < 0)
		return -1;
	start(source, fd_dest);
	return 0;
}

void eFilePushThread::start(ePtr<iTsSource> &source, int fd_dest)
{
	m_source = source;
	m_fd_dest = fd_dest;
	m_current_position = 0;
	resume();
}

void eFilePushThread::stop()
{
		/* if we aren't running, don't bother stopping. */
	if (!sync())
		return;

	m_stop = 1;

	eDebug("stopping thread."); /* just do it ONCE. it won't help to do this more than once. */
	sendSignal(SIGUSR1);
	kill(0);
}

void eFilePushThread::pause()
{
	stop();
}

void eFilePushThread::resume()
{
	m_stop = 0;
	run();
}

void eFilePushThread::flush()
{
	m_buf_start = m_buf_end = m_filter_end = 0;
}

void eFilePushThread::enablePVRCommit(int s)
{
	m_send_pvr_commit = s;
}

void eFilePushThread::setStreamMode(int s)
{
	m_stream_mode = s;
}

void eFilePushThread::setTimeshift(bool s)
{
	m_is_timeshift = s;
}

void eFilePushThread::setTSPath(const std::string s)
{
	m_tspath = s;
}

void eFilePushThread::setScatterGather(iFilePushScatterGather *sg)
{
	m_sg = sg;
}

void eFilePushThread::sendEvent(int evt)
{
	m_messagepump.send(evt);
}

void eFilePushThread::recvEvent(const int &evt)
{
	m_event(evt);
}

void eFilePushThread::defaultTSPath(bool s)
{
	std::string tspath;

	if (s) {
		if (ePythonConfigQuery::getConfigValue("config.usage.timeshift_path", tspath) == -1)
			eDebug("could not query ts path from config");
	} else {
		if (ePythonConfigQuery::getConfigValue("config.usage.instantrec_path", tspath) == -1) {
			eDebug("could not query ts path from config");
		} else {
			if (tspath == "<default>") {
				if (ePythonConfigQuery::getConfigValue("config.usage.default_path", tspath) == -1)
					eDebug("could not query ts path from config");
			} else if (tspath == "<current>") {
				if (ePythonConfigQuery::getConfigValue("config.movielist.last_videodir", tspath) == -1)
					eDebug("could not query ts path from config");
			} else if (tspath == "<timer>") {
				if (ePythonConfigQuery::getConfigValue("config.movielist.last_timer_videodir", tspath) == -1)
					eDebug("could not query ts path from config");
			}
		}
	}

	if (!tspath.empty())
		tspath.append("/");

	m_tspath = tspath;
}

int eFilePushThread::filterRecordData(const unsigned char *data, int len, size_t &current_span_remaining)
{
	return len;
}
