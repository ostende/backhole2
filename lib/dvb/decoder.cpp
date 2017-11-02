#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/dvb/decoder.h>
#include <linux/dvb/audio.h>
#include <linux/dvb/video.h>
#include <linux/dvb/dmx.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>

#include <lib/dvb/fccdecoder.h>

	/* these are quite new... */
#ifndef AUDIO_GET_PTS
#define AUDIO_GET_PTS              _IOR('o', 19, __u64)
#define VIDEO_GET_PTS              _IOR('o', 57, __u64)
#endif

#ifndef VIDEO_SOURCE_HDMI
#define VIDEO_SOURCE_HDMI 2
#endif
#ifndef AUDIO_SOURCE_HDMI
#define AUDIO_SOURCE_HDMI 2
#endif

DEFINE_REF(eDVBAudio);

eDVBAudio::eDVBAudio(eDVBDemux *demux, int dev)
	:m_demux(demux), m_dev(dev)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/audio%d", demux ? demux->adapter : 0, dev);
	m_fd = ::open(filename, O_RDWR);
	if (m_fd < 0)
		eWarning("%s: %m", filename);
	if (demux)
	{
		sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
		m_fd_demux = ::open(filename, O_RDWR);
		if (m_fd_demux < 0)
			eWarning("%s: %m", filename);
	}
	else
	{
		m_fd_demux = -1;
	}

	if (m_fd >= 0)
	{
		::ioctl(m_fd, AUDIO_SELECT_SOURCE, demux ? AUDIO_SOURCE_DEMUX : AUDIO_SOURCE_HDMI);
	}
}

int eDVBAudio::startPid(int pid, int type)
{
	if (m_fd_demux >= 0)
	{
		dmx_pes_filter_params pes;

		pes.pid      = pid;
		pes.input    = DMX_IN_FRONTEND;
		pes.output   = DMX_OUT_DECODER;
		switch (m_dev)
		{
		case 0:
			pes.pes_type = DMX_PES_AUDIO0;
			break;
		case 1:
			pes.pes_type = DMX_PES_AUDIO1;
			break;
		case 2:
			pes.pes_type = DMX_PES_AUDIO2;
			break;
		case 3:
			pes.pes_type = DMX_PES_AUDIO3;
			break;
		}
		pes.flags    = 0;
		eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - audio - ", pid);
		if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
		{
			eDebug("failed (%m)");
			return -errno;
		}
		eDebug("ok");
		eDebugNoNewLine("DEMUX_START - audio - ");
		if (::ioctl(m_fd_demux, DMX_START) < 0)
		{
			eDebug("failed (%m)");
			return -errno;
		}
		eDebug("ok");
	}

	if (m_fd >= 0)
	{
		int bypass = 0;

		switch (type)
		{
		case aMPEG:
			bypass = 1;
			break;
		case aAC3:
			bypass = 0;
			break;
		case aDTS:
			bypass = 2;
			break;
		case aAAC:
			bypass = 8;
			break;
		case aAACHE:
			bypass = 9;
			break;
		case aLPCM:
			bypass = 6;
			break;
		case aDTSHD:
			bypass = 0x10;
			break;
		case aDDP:
			bypass = 0x22;
			break;

		}

		eDebugNoNewLine("AUDIO_SET_BYPASS(%d) - ", bypass);
		if (::ioctl(m_fd, AUDIO_SET_BYPASS_MODE, bypass) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
		freeze();  // why freeze here?!? this is a problem when only a pid change is requested... because of the unfreeze logic in Decoder::setState
		eDebugNoNewLine("AUDIO_PLAY - ");
		if (::ioctl(m_fd, AUDIO_PLAY) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
	}
	return 0;
}

void eDVBAudio::stop()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLine("AUDIO_STOP - ");
		if (::ioctl(m_fd, AUDIO_STOP) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
	}

	if (m_fd_demux >= 0)
	{
		eDebugNoNewLine("DEMUX_STOP - audio - ");
		if (::ioctl(m_fd_demux, DMX_STOP) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
	}
}

void eDVBAudio::flush()
{
	eDebugNoNewLine("AUDIO_CLEAR_BUFFER - ");
	if (::ioctl(m_fd, AUDIO_CLEAR_BUFFER) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBAudio::freeze()
{
	eDebugNoNewLine("AUDIO_PAUSE - ");
	if (::ioctl(m_fd, AUDIO_PAUSE) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBAudio::unfreeze()
{
	eDebugNoNewLine("AUDIO_CONTINUE - ");
	if (::ioctl(m_fd, AUDIO_CONTINUE) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBAudio::setChannel(int channel)
{
	int val = AUDIO_STEREO;
	switch (channel)
	{
	case aMonoLeft: val = AUDIO_MONO_LEFT; break;
	case aMonoRight: val = AUDIO_MONO_RIGHT; break;
	default: break;
	}
	eDebugNoNewLine("AUDIO_CHANNEL_SELECT(%d) - ", val);
	if (::ioctl(m_fd, AUDIO_CHANNEL_SELECT, val) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

int eDVBAudio::getPTS(pts_t &now)
{
	if (::ioctl(m_fd, AUDIO_GET_PTS, &now) < 0)
		eDebug("AUDIO_GET_PTS failed (%m)");
	return 0;
}

eDVBAudio::~eDVBAudio()
{
	unfreeze();  // why unfreeze here... but not unfreeze video in ~eDVBVideo ?!?
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eDVBVideo);

eDVBVideo::eDVBVideo(eDVBDemux *demux, int dev, bool fcc_enable)
	: m_demux(demux), m_dev(dev), m_fcc_enable(fcc_enable),
	m_width(-1), m_height(-1), m_framerate(-1), m_aspect(-1), m_progressive(-1)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/video%d", demux ? demux->adapter : 0, dev);
	m_fd = ::open(filename, O_RDWR);
	if (m_fd < 0)
		eWarning("%s: %m", filename);
	else
	{
		m_sn = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Priority);
		CONNECT(m_sn->activated, eDVBVideo::video_event);
	}
	eDebug("Video Device: %s", filename);



	if (demux)
	{
		sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
		m_fd_demux = ::open(filename, O_RDWR);
		if (m_fd_demux < 0)
			eWarning("%s: %m", filename);
		eDebug("demux device: %s", filename);
	}
	else
	{
		m_fd_demux = -1;
	}

	if (m_fd >= 0)
	{
		::ioctl(m_fd, VIDEO_SELECT_SOURCE, demux ? VIDEO_SOURCE_DEMUX : VIDEO_SOURCE_HDMI);
	}
}

// not finally values i think.. !!
#define VIDEO_STREAMTYPE_MPEG2 0
#define VIDEO_STREAMTYPE_MPEG4_H264 1
#define VIDEO_STREAMTYPE_VC1 3
#define VIDEO_STREAMTYPE_MPEG4_Part2 4
#define VIDEO_STREAMTYPE_VC1_SM 5
#define VIDEO_STREAMTYPE_MPEG1 6
#define VIDEO_STREAMTYPE_H265_HEVC 7

int eDVBVideo::startPid(int pid, int type)
{
	if (m_fcc_enable)
		return 0;

	if (m_fd >= 0)
	{
		int streamtype = VIDEO_STREAMTYPE_MPEG2;
		switch(type)
		{
			default:
			case MPEG2:
				break;
			case MPEG4_H264:
				streamtype = VIDEO_STREAMTYPE_MPEG4_H264;
				break;
			case MPEG1:
				streamtype = VIDEO_STREAMTYPE_MPEG1;
				break;
			case MPEG4_Part2:
				streamtype = VIDEO_STREAMTYPE_MPEG4_Part2;
				break;
			case VC1:
				streamtype = VIDEO_STREAMTYPE_VC1;
				break;
			case VC1_SM:
				streamtype = VIDEO_STREAMTYPE_VC1_SM;
				break;
			case H265_HEVC:
				streamtype = VIDEO_STREAMTYPE_H265_HEVC;
				break;
		}

		eDebugNoNewLine("VIDEO_SET_STREAMTYPE %d - ", streamtype);
		if (::ioctl(m_fd, VIDEO_SET_STREAMTYPE, streamtype) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
		
	}

	if (m_fd_demux >= 0)
	{
		dmx_pes_filter_params pes;

		pes.pid      = pid;
		pes.input    = DMX_IN_FRONTEND;
		pes.output   = DMX_OUT_DECODER;
		switch (m_dev)
		{
		case 0:
			pes.pes_type = DMX_PES_VIDEO0;
			break;
		case 1:
			pes.pes_type = DMX_PES_VIDEO1;
			break;
		case 2:
			pes.pes_type = DMX_PES_VIDEO2;
			break;
		case 3:
			pes.pes_type = DMX_PES_VIDEO3;
			break;
		}
		pes.flags    = 0;
		eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - video - ", pid);
		if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
		{
			eDebug("failed (%m)");
			return -errno;
		}
		eDebug("ok");
		eDebugNoNewLine("DEMUX_START - video - ");
		if (::ioctl(m_fd_demux, DMX_START) < 0)
		{
			eDebug("failed (%m)");
			return -errno;
		}
		eDebug("ok");
	}

	if (m_fd >= 0)
	{
		freeze();  // why freeze here?!? this is a problem when only a pid change is requested... because of the unfreeze logic in Decoder::setState
		eDebugNoNewLine("VIDEO_PLAY - ");
		if (::ioctl(m_fd, VIDEO_PLAY) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
	}
	return 0;
}

void eDVBVideo::stop()
{
	if (m_fcc_enable)
		return;

	if (m_fd_demux >= 0)
	{
		eDebugNoNewLine("DEMUX_STOP - video - ");
		if (::ioctl(m_fd_demux, DMX_STOP) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
	}

	if (m_fd >= 0)
	{
		eDebugNoNewLine("VIDEO_STOP - ");
		if (::ioctl(m_fd, VIDEO_STOP, 1) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
	}
}

void eDVBVideo::flush()
{
	eDebugNoNewLine("VIDEO_CLEAR_BUFFER - ");
	if (::ioctl(m_fd, VIDEO_CLEAR_BUFFER) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBVideo::freeze()
{
	eDebugNoNewLine("VIDEO_FREEZE - ");
	if (::ioctl(m_fd, VIDEO_FREEZE) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBVideo::unfreeze()
{
	eDebugNoNewLine("VIDEO_CONTINUE - ");
	if (::ioctl(m_fd, VIDEO_CONTINUE) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

int eDVBVideo::setSlowMotion(int repeat)
{
	eDebugNoNewLine("VIDEO_SLOWMOTION(%d) - ", repeat);
	int ret = ::ioctl(m_fd, VIDEO_SLOWMOTION, repeat);
	if (ret < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
	return ret;
}

int eDVBVideo::setFastForward(int skip)
{
	eDebugNoNewLine("VIDEO_FAST_FORWARD(%d) - ", skip);
	int ret = ::ioctl(m_fd, VIDEO_FAST_FORWARD, skip);
	if (ret < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
	return ret;
}

int eDVBVideo::getPTS(pts_t &now)
{
	int ret = ::ioctl(m_fd, VIDEO_GET_PTS, &now);
	if (ret < 0)
		eDebug("VIDEO_GET_PTS failed(%m)");
	return ret;
}

eDVBVideo::~eDVBVideo()
{
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

void eDVBVideo::video_event(int)
{
	struct video_event evt;
	eDebugNoNewLine("VIDEO_GET_EVENT - ");
	if (::ioctl(m_fd, VIDEO_GET_EVENT, &evt) < 0)
		eDebug("failed (%m)");
	else
	{
		eDebug("ok");
		if (evt.type == VIDEO_EVENT_SIZE_CHANGED)
		{
			struct iTSMPEGDecoder::videoEvent event;
			event.type = iTSMPEGDecoder::videoEvent::eventSizeChanged;
			m_aspect = event.aspect = evt.u.size.aspect_ratio == 0 ? 2 : 3;  // convert dvb api to etsi
			m_height = event.height = evt.u.size.h;
			m_width = event.width = evt.u.size.w;
			/* emit */ m_event(event);
		}
		else if (evt.type == VIDEO_EVENT_FRAME_RATE_CHANGED)
		{
			struct iTSMPEGDecoder::videoEvent event;
			event.type = iTSMPEGDecoder::videoEvent::eventFrameRateChanged;
			m_framerate = event.framerate = evt.u.frame_rate;
			/* emit */ m_event(event);
		}
		else if (evt.type == 16 /*VIDEO_EVENT_PROGRESSIVE_CHANGED*/)
		{
			struct iTSMPEGDecoder::videoEvent event;
			event.type = iTSMPEGDecoder::videoEvent::eventProgressiveChanged;
			m_progressive = event.progressive = evt.u.frame_rate;
			/* emit */ m_event(event);
		}
		else
			eDebug("unhandled DVBAPI Video Event %d", evt.type);
	}
}

RESULT eDVBVideo::connectEvent(const Slot1<void, struct iTSMPEGDecoder::videoEvent> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

static int readMpegProc(const char *str, int decoder)
{
	int val = -1;
	char tmp[64];
	sprintf(tmp, "/proc/stb/vmpeg/%d/%s", decoder, str);
	FILE *f = fopen(tmp, "r");
	if (f)
	{
		fscanf(f, "%x", &val);
		fclose(f);
	}
	return val;
}

static int readApiSize(int fd, int &xres, int &yres, int &aspect)
{
	video_size_t size;
	if (!::ioctl(fd, VIDEO_GET_SIZE, &size))
	{
		xres = size.w;
		yres = size.h;
		aspect = size.aspect_ratio == 0 ? 2 : 3;  // convert dvb api to etsi
		return 0;
	}
//	eDebug("VIDEO_GET_SIZE failed (%m)");
	return -1;
}

static int readApiFrameRate(int fd, int &framerate)
{
	unsigned int frate;
	if (!::ioctl(fd, VIDEO_GET_FRAME_RATE, &frate))
	{
		framerate = frate;	
		return 0;
	}
//	eDebug("VIDEO_GET_FRAME_RATE failed (%m)");
	return -1;
}

int eDVBVideo::getWidth()
{
	if (m_width == -1)
		readApiSize(m_fd, m_width, m_height, m_aspect);
	if (m_width == -1)
		m_width = readMpegProc("xres", m_dev);
	return m_width;
}

int eDVBVideo::getHeight()
{
	if (m_height == -1)
		readApiSize(m_fd, m_width, m_height, m_aspect);
	if (m_height == -1)
		m_height = readMpegProc("yres", m_dev);
	return m_height;
}

int eDVBVideo::getAspect()
{
	if (m_aspect == -1)
		readApiSize(m_fd, m_width, m_height, m_aspect);
	if (m_aspect == -1)
		m_aspect = readMpegProc("aspect", m_dev);
	return m_aspect;
}

int eDVBVideo::getProgressive()
{
	if (m_progressive == -1)
		m_progressive = readMpegProc("progressive", m_dev);
	return m_progressive;
}

int eDVBVideo::getFrameRate()
{
	if (m_framerate == -1)
		readApiFrameRate(m_fd, m_framerate);
	if (m_framerate == -1)
		m_framerate = readMpegProc("framerate", m_dev);
	return m_framerate;
}

DEFINE_REF(eDVBPCR);

eDVBPCR::eDVBPCR(eDVBDemux *demux, int dev): m_demux(demux), m_dev(dev)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
	m_fd_demux = ::open(filename, O_RDWR);
	if (m_fd_demux < 0)
		eWarning("%s: %m", filename);
}

int eDVBPCR::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	switch (m_dev)
	{
	case 0:
		pes.pes_type = DMX_PES_PCR0;
		break;
	case 1:
		pes.pes_type = DMX_PES_PCR1;
		break;
	case 2:
		pes.pes_type = DMX_PES_PCR2;
		break;
	case 3:
		pes.pes_type = DMX_PES_PCR3;
		break;
	}
	pes.flags    = 0;
	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - pcr - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	eDebugNoNewLine("DEMUX_START - pcr - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

void eDVBPCR::stop()
{
	eDebugNoNewLine("DEMUX_STOP - pcr - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
}

eDVBPCR::~eDVBPCR()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eDVBTText);

eDVBTText::eDVBTText(eDVBDemux *demux, int dev)
    :m_demux(demux), m_dev(dev)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
	m_fd_demux = ::open(filename, O_RDWR);
	if (m_fd_demux < 0)
		eWarning("%s: %m", filename);
}

int eDVBTText::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = m_dev ? DMX_PES_TELETEXT1 : DMX_PES_TELETEXT0; // FIXME
	pes.flags    = 0;

	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - ttx - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed(%m)");
		return -errno;
	}
	eDebug("ok");
	eDebugNoNewLine("DEMUX_START - ttx - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed(%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

void eDVBTText::stop()
{
	eDebugNoNewLine("DEMUX_STOP - ttx - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
}

eDVBTText::~eDVBTText()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eTSMPEGDecoder);

int eTSMPEGDecoder::setState()
{
	int res = 0;

	int noaudio = (m_state != statePlay) && (m_state != statePause);
	int nott = noaudio; /* actually same conditions */

	if ((noaudio && m_audio) || (!m_audio && !noaudio))
		m_changed |= changeAudio | changeState;

	if ((nott && m_text) || (!m_text && !nott))
		m_changed |= changeText | changeState;

	const char *decoder_states[] = {"stop", "pause", "play", "decoderfastforward", "trickmode", "slowmotion"};
	eDebug("decoder state: %s, vpid=%d, apid=%d", decoder_states[m_state], m_vpid, m_apid);

	int changed = m_changed;
	if (m_changed & changePCR)
	{
		if (m_pcr)
			m_pcr->stop();
		m_pcr = 0;
	}
	if (m_changed & changeVideo)
	{
		if (m_video)
		{
			m_video->stop();
			m_video = 0;
			m_video_event_conn = 0;
		}
	}
	if (m_changed & changeAudio)
	{
		if (m_audio)
			m_audio->stop();
		m_audio = 0;
	}
	if (m_changed & changeText)
	{
		if (m_text)
			m_text->stop();
		m_text = 0;
	}
	if (m_changed & changePCR)
	{
		if ((m_pcrpid >= 0) && (m_pcrpid < 0x1FFF))
		{
			m_pcr = new eDVBPCR(m_demux, m_decoder);
			if (m_pcr->startPid(m_pcrpid))
				res = -1;
		}
		m_changed &= ~changePCR;
	}
	if (m_changed & changeAudio)
	{
		if ((m_apid >= 0) && (m_apid < 0x1FFF) && !noaudio)
		{
			m_audio = new eDVBAudio(m_demux, m_decoder);
			if (m_audio->startPid(m_apid, m_atype))
				res = -1;
		}
		m_changed &= ~changeAudio;
	}
	if (m_changed & changeVideo)
	{
		if ((m_vpid >= 0) && (m_vpid < 0x1FFF))
		{
			m_video = new eDVBVideo(m_demux, m_decoder, m_fcc_enable);
			m_video->connectEvent(slot(*this, &eTSMPEGDecoder::video_event), m_video_event_conn);
			if (m_video->startPid(m_vpid, m_vtype))
				res = -1;
		}
		m_changed &= ~changeVideo;
	}
	if (m_changed & changeText)
	{
		if ((m_textpid >= 0) && (m_textpid < 0x1FFF) && !nott)
		{
			m_text = new eDVBTText(m_demux, m_decoder);
			if (m_text->startPid(m_textpid))
				res = -1;
		}
		m_changed &= ~changeText;
	}

	if (changed & (changeState|changeVideo|changeAudio))
	{
					/* play, slowmotion, fast-forward */
		int state_table[6][4] = 
			{
				/* [stateStop] =                 */ {0, 0, 0},
				/* [statePause] =                */ {0, 0, 0},
				/* [statePlay] =                 */ {1, 0, 0},
				/* [stateDecoderFastForward] =   */ {1, 0, m_ff_sm_ratio},
				/* [stateHighspeedFastForward] = */ {1, 0, 1},
				/* [stateSlowMotion] =           */ {1, m_ff_sm_ratio, 0}
			};
		int *s = state_table[m_state];
		if (changed & (changeState|changeVideo) && m_video)
		{
			m_video->setSlowMotion(s[1]);
			m_video->setFastForward(s[2]);
			if (s[0])
				m_video->unfreeze();
			else
				m_video->freeze();
		}
		if (changed & (changeState|changeAudio) && m_audio)
		{
			if (s[0])
				m_audio->unfreeze();
			else
				m_audio->freeze();
		}
		m_changed &= ~changeState;
	}

	if (changed && !m_video && m_audio && m_radio_pic.length())
		showSinglePic(m_radio_pic.c_str());

	return res;
}

int eTSMPEGDecoder::m_pcm_delay=-1,
	eTSMPEGDecoder::m_ac3_delay=-1;

RESULT eTSMPEGDecoder::setHwPCMDelay(int delay)
{
	if (delay != m_pcm_delay )
	{
		FILE *fp = fopen("/proc/stb/audio/audio_delay_pcm", "w");
		if (fp)
		{
			fprintf(fp, "%x", delay*90);
			fclose(fp);
			m_pcm_delay = delay;
			return 0;
		}
	}
	return -1;
}

RESULT eTSMPEGDecoder::setHwAC3Delay(int delay)
{
	if ( delay != m_ac3_delay )
	{
		FILE *fp = fopen("/proc/stb/audio/audio_delay_bitstream", "w");
		if (fp)
		{
			fprintf(fp, "%x", delay*90);
			fclose(fp);
			m_ac3_delay = delay;
			return 0;
		}
	}
	return -1;
}


RESULT eTSMPEGDecoder::setPCMDelay(int delay)
{
	return m_decoder == 0 ? setHwPCMDelay(delay) : -1;
}

RESULT eTSMPEGDecoder::setAC3Delay(int delay)
{
	return m_decoder == 0 ? setHwAC3Delay(delay) : -1;
}

eTSMPEGDecoder::eTSMPEGDecoder(eDVBDemux *demux, int decoder)
	: m_demux(demux), 
		m_vpid(-1), m_vtype(-1), m_apid(-1), m_atype(-1), m_pcrpid(-1), m_textpid(-1),
		m_changed(0), m_decoder(decoder), m_video_clip_fd(-1), m_showSinglePicTimer(eTimer::create(eApp)),
		m_fcc_fd(-1), m_fcc_enable(false), m_fcc_state(fcc_state_stop), m_fcc_feid(-1), m_fcc_vpid(-1), m_fcc_vtype(-1), m_fcc_pcrpid(-1)
{
	if (m_demux)
	{
		demux->connectEvent(slot(*this, &eTSMPEGDecoder::demux_event), m_demux_event_conn);
	}
	CONNECT(m_showSinglePicTimer->timeout, eTSMPEGDecoder::finishShowSinglePic);
	m_state = stateStop;
}

eTSMPEGDecoder::~eTSMPEGDecoder()
{
	finishShowSinglePic();
	m_vpid = m_apid = m_pcrpid = m_textpid = pidNone;
	m_changed = -1;
	setState();
	fccStop();
	fccFreeFD();
}

RESULT eTSMPEGDecoder::setVideoPID(int vpid, int type)
{
	if ((m_vpid != vpid) || (m_vtype != type))
	{
		m_changed |= changeVideo;
		m_vpid = vpid;
		m_vtype = type;
	}
	return 0;
}

RESULT eTSMPEGDecoder::setAudioPID(int apid, int type)
{
	if ((m_apid != apid) || (m_atype != type))
	{
		m_changed |= changeAudio;
		m_atype = type;
		m_apid = apid;
	}
	return 0;
}

int eTSMPEGDecoder::m_audio_channel = -1;

RESULT eTSMPEGDecoder::setAudioChannel(int channel)
{
	if (channel == -1)
		channel = ac_stereo;
	if (m_decoder == 0 && m_audio_channel != channel)
	{
		if (m_audio)
		{
			m_audio->setChannel(channel);
			m_audio_channel=channel;
		}
		else
			eDebug("eTSMPEGDecoder::setAudioChannel but no audio decoder exist");
	}
	return 0;
}

int eTSMPEGDecoder::getAudioChannel()
{
	return m_audio_channel == -1 ? ac_stereo : m_audio_channel;
}

RESULT eTSMPEGDecoder::setSyncPCR(int pcrpid)
{
	if (m_pcrpid != pcrpid)
	{
		m_changed |= changePCR;
		m_pcrpid = pcrpid;
	}
	return 0;
}

RESULT eTSMPEGDecoder::setTextPID(int textpid)
{
	if (m_textpid != textpid)
	{
		m_changed |= changeText;
		m_textpid = textpid;
	}
	return 0;
}

RESULT eTSMPEGDecoder::setSyncMaster(int who)
{
	return -1;
}

RESULT eTSMPEGDecoder::set()
{
	return setState();
}

RESULT eTSMPEGDecoder::play()
{
	if (m_state == statePlay)
	{
		if (!m_changed)
			return 0;
	} else  
	{
		m_state = statePlay;
		m_changed |= changeState;
	}
	return setState();
}

RESULT eTSMPEGDecoder::pause()
{
	if (m_state == statePause)
		return 0;
	m_state = statePause;
	m_changed |= changeState;
	return setState();
}

RESULT eTSMPEGDecoder::setFastForward(int frames_to_skip)
{
	if ((m_state == stateDecoderFastForward) && (m_ff_sm_ratio == frames_to_skip))
		return 0;

	m_state = stateDecoderFastForward;
	m_ff_sm_ratio = frames_to_skip;
	m_changed |= changeState;
	return setState();

//		return m_video->setFastForward(frames_to_skip);
}

RESULT eTSMPEGDecoder::setSlowMotion(int repeat)
{
	if ((m_state == stateSlowMotion) && (m_ff_sm_ratio == repeat))
		return 0;

	m_state = stateSlowMotion;
	m_ff_sm_ratio = repeat;
	m_changed |= changeState;
	return setState();
}

RESULT eTSMPEGDecoder::setTrickmode()
{
	if (m_state == stateTrickmode)
		return 0;

	m_state = stateTrickmode;
	m_changed |= changeState;
	return setState();
}

RESULT eTSMPEGDecoder::flush()
{
	if (m_audio)
		m_audio->flush();
	if (m_video)
		m_video->flush();
	return 0;
}

void eTSMPEGDecoder::demux_event(int event)
{
	switch (event)
	{
	case eDVBDemux::evtFlush:
		flush();
		break;
	default:
		break;
	}
}

RESULT eTSMPEGDecoder::getPTS(int what, pts_t &pts)
{
	if (what == 0) /* auto */
		what = m_video ? 1 : 2;

	if (what == 1) /* video */
	{
		if (m_video)
			return m_video->getPTS(pts);
		else
			return -1;
	}

	if (what == 2) /* audio */
	{
		if (m_audio)
			return m_audio->getPTS(pts);
		else
			return -1;
	}

	return -1;
}

RESULT eTSMPEGDecoder::setRadioPic(const std::string &filename)
{
	m_radio_pic = filename;
	return 0;
}

RESULT eTSMPEGDecoder::showSinglePic(const char *filename)
{
	if (m_decoder == 0)
	{
		eDebug("showSinglePic %s", filename);
		int f = open(filename, O_RDONLY);
		if (f >= 0)
		{
			struct stat s;
			size_t written=0;
			fstat(f, &s);
			if (m_video_clip_fd == -1)
				m_video_clip_fd = open("/dev/dvb/adapter0/video0", O_WRONLY);
			if (m_video_clip_fd >= 0)
			{
				bool seq_end_avail = false;
				size_t pos=0;
				unsigned char pes_header[] = { 0x00, 0x00, 0x01, 0xE0, 0x00, 0x00, 0x80, 0x00, 0x00 };
				unsigned char seq_end[] = { 0x00, 0x00, 0x01, 0xB7 };
				unsigned char iframe[s.st_size];
				unsigned char stuffing[8192];
				int streamtype = VIDEO_STREAMTYPE_MPEG2;
				memset(stuffing, 0, 8192);
				read(f, iframe, s.st_size);
				if (ioctl(m_video_clip_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_MEMORY) < 0)
					eDebug("VIDEO_SELECT_SOURCE MEMORY failed (%m)");
				if (ioctl(m_video_clip_fd, VIDEO_SET_STREAMTYPE, streamtype) < 0)
					eDebug("VIDEO_SET_STREAMTYPE failed(%m)");
				if (ioctl(m_video_clip_fd, VIDEO_PLAY) < 0)
					eDebug("VIDEO_PLAY failed (%m)");
				if (ioctl(m_video_clip_fd, VIDEO_CONTINUE) < 0)
					eDebug("video: VIDEO_CONTINUE: %m");
				if (ioctl(m_video_clip_fd, VIDEO_CLEAR_BUFFER) < 0)
					eDebug("video: VIDEO_CLEAR_BUFFER: %m");
				while(pos <= (s.st_size-4) && !(seq_end_avail = (!iframe[pos] && !iframe[pos+1] && iframe[pos+2] == 1 && iframe[pos+3] == 0xB7)))
					++pos;
				if ((iframe[3] >> 4) != 0xE) // no pes header
					write(m_video_clip_fd, pes_header, sizeof(pes_header));
				else
					iframe[4] = iframe[5] = 0x00;
				write(m_video_clip_fd, iframe, s.st_size);
				if (!seq_end_avail)
					write(m_video_clip_fd, seq_end, sizeof(seq_end));
				write(m_video_clip_fd, stuffing, 8192);
				m_showSinglePicTimer->start(150, true);
			}
			close(f);
		}
		else
		{
			eDebug("couldnt open %s", filename);
			return -1;
		}
	}
	else
	{
		eDebug("only show single pics on first decoder");
		return -1;
	}
	return 0;
}

void eTSMPEGDecoder::finishShowSinglePic()
{
	if (m_video_clip_fd >= 0)
	{
		if (ioctl(m_video_clip_fd, VIDEO_STOP, 0) < 0)
			eDebug("VIDEO_STOP failed (%m)");
		if (ioctl(m_video_clip_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_DEMUX) < 0)
				eDebug("VIDEO_SELECT_SOURCE DEMUX failed (%m)");
		close(m_video_clip_fd);
		m_video_clip_fd = -1;
	}
}

RESULT eTSMPEGDecoder::connectVideoEvent(const Slot1<void, struct videoEvent> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_video_event.connect(event));
	return 0;
}

void eTSMPEGDecoder::video_event(struct videoEvent event)
{
	/* emit */ m_video_event(event);
}

int eTSMPEGDecoder::getVideoWidth()
{
	if (m_video)
		return m_video->getWidth();
	return -1;
}

int eTSMPEGDecoder::getVideoHeight()
{
	if (m_video)
		return m_video->getHeight();
	return -1;
}

int eTSMPEGDecoder::getVideoProgressive()
{
	if (m_video)
		return m_video->getProgressive();
	return -1;
}

int eTSMPEGDecoder::getVideoFrameRate()
{
	if (m_video)
		return m_video->getFrameRate();
	return -1;
}

int eTSMPEGDecoder::getVideoAspect()
{
	if (m_video)
		return m_video->getAspect();
	return -1;
}

#define FCC_SET_VPID 100
#define FCC_SET_APID 101
#define FCC_SET_PCRPID 102
#define FCC_SET_VCODEC 103
#define FCC_SET_ACODEC 104
#define FCC_SET_FRONTEND_ID 105
#define FCC_START 106
#define FCC_STOP 107
#define FCC_DECODER_START 108
#define FCC_DECODER_STOP 109

RESULT eTSMPEGDecoder::prepareFCC(int fe_id, int vpid, int vtype, int pcrpid)
{
	//eDebug("[eTSMPEGDecoder::prepareFCC] vp : %d, vt : %d, pp : %d, fe : %d", vpid, vtype, pcrpid, fe_id); 

	if ((fccGetFD() == -1) || (fccSetPids(fe_id, vpid, vtype, pcrpid) < 0) || (fccStart() < 0))
	{
		fccFreeFD();
		return -1;
	}

	m_fcc_enable = true;

	return 0;
}

RESULT eTSMPEGDecoder::fccDecoderStart()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state != fcc_state_ready)
	{
		eDebug("FCC decoder is already in decoding state.");
		return 0;
	}

	if (ioctl(m_fcc_fd, FCC_DECODER_START) < 0)
	{
		eDebug("ioctl FCC_DECODER_START failed! (%m)");
		return -1;
	}

	m_fcc_state = fcc_state_decoding;

	eDebug("[eTSMPEGDecoder] FCC_DECODER_START OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccDecoderStop()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state != fcc_state_decoding)
	{
		eDebug("FCC decoder is not in decoding state.");
	}
	else if (ioctl(m_fcc_fd, FCC_DECODER_STOP) < 0)
	{
		eDebug("ioctl FCC_DECODER_STOP failed! (%m)");
		return -1;
	}

	m_fcc_state = fcc_state_ready;

	/* stop pcr, video, audio, text */
	finishShowSinglePic();

	m_vpid = m_apid = m_pcrpid = m_textpid = pidNone;
	m_changed = -1;
	setState();

	eDebug("[eTSMPEGDecoder] FCC_DECODER_STOP OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccUpdatePids(int fe_id, int vpid, int vtype, int pcrpid)
{
	//eDebug("[eTSMPEGDecoder] vp : %d, vt : %d, pp : %d, fe : %d", vpid, vtype, pcrpid, fe_id);

	if ((fe_id != m_fcc_feid) || (vpid != m_fcc_vpid) || (vtype != m_fcc_vtype) || (pcrpid != m_fcc_pcrpid))
	{
		int cur_fcc_state = m_fcc_state;
		fccStop();
		if (prepareFCC(fe_id, vpid, vtype, pcrpid))
		{
			eDebug("[eTSMPEGDecoder] prepare FCC failed!");
			return -1;
		}
	}
	return 0;
}

RESULT eTSMPEGDecoder::fccStart()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state != fcc_state_stop)
	{
		eDebug("[eTSMPEGDecoder] FCC is already started!");
		return 0;
	}
	else if (ioctl(m_fcc_fd, FCC_START) < 0)
	{
		eDebug("ioctl FCC_START failed! (%m)");
		return -1;
	}

	eDebug("[eTSMPEGDecoder] FCC_START OK!");

	m_fcc_state = fcc_state_ready;
	return 0;
}

RESULT eTSMPEGDecoder::fccStop()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state == fcc_state_stop)
	{
		eDebug("[eTSMPEGDecoder] FCC is already stopped!");
		return 0;
	}

	else if (m_fcc_state == fcc_state_decoding)
	{
		fccDecoderStop();
	}

	if (ioctl(m_fcc_fd, FCC_STOP) < 0)
	{
		eDebug("ioctl FCC_STOP failed! (%m)");
		return -1;
	}

	m_fcc_state = fcc_state_stop;

	eDebug("[eTSMPEGDecoder] FCC_STOP OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccSetPids(int fe_id, int vpid, int vtype, int pcrpid)
{
	int streamtype = VIDEO_STREAMTYPE_MPEG2;

	if (m_fcc_fd == -1)
		return -1;

	if (ioctl(m_fcc_fd, FCC_SET_FRONTEND_ID, fe_id) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_FRONTEND_ID failed! (%m)");
		return -1;
	}

	else if(ioctl(m_fcc_fd, FCC_SET_PCRPID, pcrpid) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_PCRPID failed! (%m)");
		return -1;
	}

	else if (ioctl(m_fcc_fd, FCC_SET_VPID, vpid) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_VPID failed! (%m)");
		return -1;
	}

	switch(vtype)
	{
		default:
		case eDVBVideo::MPEG2:
			break;
		case eDVBVideo::MPEG4_H264:
			streamtype = VIDEO_STREAMTYPE_MPEG4_H264;
			break;
		case eDVBVideo::MPEG1:
			streamtype = VIDEO_STREAMTYPE_MPEG1;
			break;
		case eDVBVideo::MPEG4_Part2:
			streamtype = VIDEO_STREAMTYPE_MPEG4_Part2;
			break;
		case eDVBVideo::VC1:
			streamtype = VIDEO_STREAMTYPE_VC1;
			break;
		case eDVBVideo::VC1_SM:
			streamtype = VIDEO_STREAMTYPE_VC1_SM;
			break;
		case eDVBVideo::H265_HEVC:
			streamtype = VIDEO_STREAMTYPE_H265_HEVC;
			break;
	}

	if(ioctl(m_fcc_fd, FCC_SET_VCODEC, streamtype) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_VCODEC failed! (%m)");
		return -1;
	}

	m_fcc_feid = fe_id;
	m_fcc_vpid = vpid;
	m_fcc_vtype = vtype;
	m_fcc_pcrpid = pcrpid;

	//eDebug("[eTSMPEGDecoder] SET PIDS OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccGetFD()
{
	if (m_fcc_fd == -1)
	{
		eFCCDecoder* fcc = eFCCDecoder::getInstance();
		if (fcc != NULL)
		{
			m_fcc_fd = fcc->allocateFcc();
		}
	}

	return m_fcc_fd;
}

RESULT eTSMPEGDecoder::fccFreeFD()
{
	if (m_fcc_fd != -1)
	{
		eFCCDecoder* fcc = eFCCDecoder::getInstance();
		if (fcc != NULL)
		{
			fcc->freeFcc(m_fcc_fd);
			m_fcc_fd = -1;
		}
	}

	return 0;
}

