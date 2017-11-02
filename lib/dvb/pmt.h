#ifndef __lib_dvb_dvbmid_h
#define __lib_dvb_dvbmid_h

#ifndef SWIG
#include <map>
#include <lib/base/buffer.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <lib/python/python.h>
#include <lib/python/connections.h>
#include <dvbsi++/program_map_section.h>
#include <dvbsi++/program_association_section.h>

#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>

class eDVBCAService;
class eDVBScan;

#include <dvbsi++/application_information_section.h>
class OCSection : public LongCrcSection
{
protected:
	void *data;

public:
	OCSection(const uint8_t * const buffer)
	: LongCrcSection(buffer)
	{
		data = malloc(getSectionLength());
		memcpy(data, buffer, getSectionLength());
	}
	~OCSection()
	{
		free(data);
	}
	void *getData() { return data; }
};

struct channel_data: public Object
{
	ePtr<eDVBChannel> m_channel;
	ePtr<eConnection> m_stateChangedConn;
	int m_prevChannelState;
	int m_dataDemux;
};

// TODO .. put all static stuff into a 'eDVBCAServiceHandler class'

typedef std::map<eServiceReferenceDVB, eDVBCAService*> CAServiceMap;
typedef std::map<iDVBChannel*, channel_data*> ChannelMap;

class eDVBCAService: public Object
{
	eIOBuffer m_buffer;
	ePtr<eSocketNotifier> m_sn;
	eServiceReferenceDVB m_service;
	uint8_t m_used_demux[32];
	unsigned int m_prev_build_hash;

	int m_sock, m_clilen; 
	struct sockaddr_un m_servaddr;
	unsigned int m_sendstate;
	unsigned char m_capmt[2048];
	ePtr<eTimer> m_retryTimer;
	void sendCAPMT();
	void Connect();
	void socketCB(int what);

	static void DVBChannelAdded(eDVBChannel*);
	static void DVBChannelStateChanged(iDVBChannel*);
	static CAServiceMap exist;
	static ChannelMap exist_channels;
	static ePtr<eConnection> m_chanAddedConn;
	static channel_data *getChannelData(eDVBChannelID &chid);

	eDVBCAService();
	~eDVBCAService();
public:
	static void registerChannelCallback(eDVBResourceManager *res_mgr);
	static RESULT register_service( const eServiceReferenceDVB &ref, int demux_nums[2], eDVBCAService *&caservice );
	static RESULT unregister_service( const eServiceReferenceDVB &ref, int demux_nums[2], eTable<ProgramMapSection> *ptr );
	void buildCAPMT(eTable<ProgramMapSection> *ptr);
};

#endif

#include <list>
#include <string>
class HbbTVApplicationInfo
{
public:
	int m_OrgId;
	int m_AppId;
	int m_ControlCode;
	short m_ProfileCode;
	std::string m_HbbTVUrl;
	std::string m_ApplicationName;
public:
	HbbTVApplicationInfo(int controlCode, int orgid, int appid, std::string hbbtvUrl, std::string applicationName, int profileCode)
		: m_ControlCode(controlCode), m_HbbTVUrl(hbbtvUrl), m_ApplicationName(applicationName), m_OrgId(orgid), 
		  m_AppId(appid), m_ProfileCode(profileCode)
	{}
};
typedef std::list<HbbTVApplicationInfo *> HbbTVApplicationInfoList;
typedef HbbTVApplicationInfoList::iterator HbbTVApplicationInfoListIterator;
typedef HbbTVApplicationInfoList::const_iterator HbbTVApplicationInfoListConstIterator;

class eDVBServicePMTHandler: public Object
{
#ifndef SWIG
	friend class eDVBCAService;
	eServiceReferenceDVB m_reference;
	ePtr<eDVBService> m_service;

	int m_last_channel_state;
	eDVBCAService *m_ca_servicePtr;
	ePtr<eDVBScan> m_dvb_scan; // for sdt scan

	eAUTable<eTable<ProgramMapSection> > m_PMT;
	eAUTable<eTable<ProgramAssociationSection> > m_PAT;

	eUsePtr<iDVBChannel> m_channel;
	eUsePtr<iDVBPVRChannel> m_pvr_channel;
	ePtr<eDVBResourceManager> m_resourceManager;
	ePtr<iDVBDemux> m_demux, m_pvr_demux_tmp;

	void channelStateChanged(iDVBChannel *);
	ePtr<eConnection> m_channelStateChanged_connection;
	void channelEvent(iDVBChannel *, int event);
	ePtr<eConnection> m_channelEvent_connection;
	void SDTScanEvent(int);
	ePtr<eConnection> m_scan_event_connection;

	eAUTable<eTable<ApplicationInformationSection> > m_AIT;
	eAUTable<eTable<OCSection> > m_OC;

	void registerCAService();
	void PMTready(int error);
	void PATready(int error);
	
	int m_pmt_pid;
	
	void AITready(int error);
	void OCready(int error);
	int m_dsmcc_pid;
	int m_ait_pid;
	HbbTVApplicationInfoList m_HbbTVApplications;
	std::string m_HBBTVUrl;
	std::string m_ApplicationName;
	unsigned char m_AITData[4096];
	
	int m_use_decode_demux;
	uint8_t m_decode_demux_num;
	ePtr<eTimer> m_no_pat_entry_delay;
	uint8_t mDemuxId;

	bool m_pmt_ready;
	bool m_ca_disabled;
public:
	eDVBServicePMTHandler();
	~eDVBServicePMTHandler();
#endif

#ifdef SWIG
private:
	eDVBServicePMTHandler();
public:
#endif

	enum
	{
		eventNoResources,  // a requested resource couldn't be allocated
		eventTuneFailed,   // tune failed
		eventNoPAT,        // no pat could be received (timeout)
		eventNoPATEntry,   // no pat entry for the corresponding SID could be found
		eventNoPMT,        // no pmt could be received (timeout)
		eventNewProgramInfo, // we just received a PMT
		eventTuned,        // a channel was sucessfully (re-)tuned in, you may start additional filters now
		
		eventPreStart,     // before start filepush thread
		eventSOF,          // seek pre start
		eventEOF,          // a file playback did end
		
		eventHBBTVInfo, /* HBBTV information was detected in the AIT */
		
		eventMisconfiguration, // a channel was not found in any list, or no frontend was found which could provide this channel
		eventNoDiskSpace,  // no disk space available
		eventStartPvrDescramble,   // start PVR Descramble Convert
		eventChannelAllocated,
	};
#ifndef SWIG
	Signal1<void,int> serviceEvent;

	struct videoStream
	{
		int pid;
		int component_tag;
		enum { vtMPEG2, vtMPEG4_H264, vtMPEG1, vtMPEG4_Part2, vtVC1, vtVC1_SM, vtH265_HEVC };
		int type;
	};
	
	struct audioStream
	{
		int pid,
		    rdsPid; // hack for some radio services which transmit radiotext on different pid (i.e. harmony fm, HIT RADIO FFH, ...)
		enum { atMPEG, atAC3, atDTS, atAAC, atAACHE, atLPCM, atDTSHD, atDDP  };
		int type; // mpeg2, ac3, dts, ...
		
		int component_tag;
		std::string language_code; /* iso-639, if available. */
	};

	struct subtitleStream
	{
		int pid;
		int subtitling_type;  	/*  see ETSI EN 300 468 table 26 component_type
									when stream_content is 0x03
									0x10..0x13, 0x20..0x23 is used for dvb subtitles
									0x01 is used for teletext subtitles */
		union
		{
			int composition_page_id;  // used for dvb subtitles
			int teletext_page_number;  // used for teletext subtitles
		};
		union
		{
			int ancillary_page_id;  // used for dvb subtitles
			int teletext_magazine_number;  // used for teletext subtitles
		};
		std::string language_code;
		bool operator<(const subtitleStream &s) const
		{
			if (pid != s.pid)
				return pid < s.pid;
			if (teletext_page_number != s.teletext_page_number)
				return teletext_page_number < s.teletext_page_number;
			return teletext_magazine_number < s.teletext_magazine_number;
		}
	};

	struct program
	{
		struct capid_pair
		{
			uint16_t caid;
			int capid;
			bool operator< (const struct capid_pair &t) const { return t.caid < caid; }
		};
		std::vector<videoStream> videoStreams;
		std::vector<audioStream> audioStreams;
		int defaultAudioStream;
		std::vector<subtitleStream> subtitleStreams;
		std::list<capid_pair> caids;
		int pcrPid;
		int pmtPid;
		int textPid;
		int aitPid;
		int pmtVersion;
		bool isCached;
		bool isCrypted() { return !caids.empty(); }
		PyObject *createPythonObject();
	};

	int getProgramInfo(program &program);
	int getDataDemux(ePtr<iDVBDemux> &demux);
	int getDecodeDemux(ePtr<iDVBDemux> &demux);
	PyObject *getCaIds(bool pair=false); // caid / ecmpid pair
	PyObject *getHbbTVApplications(void); 
	
	int getPVRChannel(ePtr<iDVBPVRChannel> &pvr_channel);
	int getServiceReference(eServiceReferenceDVB &service) { service = m_reference; return 0; }
	int getService(ePtr<eDVBService> &service) { service = m_service; return 0; }
	int getPMT(ePtr<eTable<ProgramMapSection> > &ptr) { return m_PMT.getCurrent(ptr); }
	int getChannel(eUsePtr<iDVBChannel> &channel);
	void resetCachedProgram() { m_have_cached_program = false; }
	void sendEventNoPatEntry();

	void getHBBTVUrl(std::string &ret) { ret = m_HBBTVUrl; }
	void getDemuxID(int &id) { id = mDemuxId; }
	void setCaDisable(bool disable) { m_ca_disabled = disable; }

	enum serviceType
	{
		livetv = 0,
		recording = 1,
		scrambled_recording = 2,
		playback = 3,
		timeshift_recording = 4,
		scrambled_timeshift_recording = 5,
		timeshift_playback = 6,
		streamserver = 7,
		scrambled_streamserver = 8,
		streamclient = 9,
		offline = 10,
		pvrDescramble = 11,
	};

	/* deprecated interface */
	int tune(eServiceReferenceDVB &ref, int use_decode_demux, eCueSheet *sg=0, bool simulate=false, eDVBService *service = 0, serviceType type = livetv, bool descramble = true);

	/* new interface */
	int tuneExt(eServiceReferenceDVB &ref, int use_decode_demux, ePtr<iTsSource> &, const char *streaminfo_file, eCueSheet *sg=0, bool simulate=false, eDVBService *service = 0, serviceType type = livetv, bool descramble=true);

	void free();
	void addCaHandler();
	void removeCaHandler();
	bool isCiConnected();
	bool isPmtReady() { return m_pmt_ready; }
private:
	bool m_have_cached_program;
	program m_cached_program;
	bool m_descramble;
	serviceType m_service_type;
#endif
};

#endif
