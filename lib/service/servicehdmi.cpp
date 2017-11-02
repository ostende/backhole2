#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/base/nconfig.h>
#include <lib/base/object.h>
#include <lib/dvb/decoder.h>
#include <lib/service/servicehdmi.h>
#include <lib/service/service.h>

#include <string>

#define HDMI_IN_REC_ENCODER_INDEX 0
#define HDMI_IN_REC_DECODER_INDEX 2

eServiceFactoryHDMI::eServiceFactoryHDMI()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		sc->addServiceFactory(eServiceFactoryHDMI::id, this, extensions);
	}

	m_service_info = new eStaticServiceHDMIInfo();
}

eServiceFactoryHDMI::~eServiceFactoryHDMI()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		sc->removeServiceFactory(eServiceFactoryHDMI::id);
	}
}

DEFINE_REF(eServiceFactoryHDMI)

RESULT eServiceFactoryHDMI::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	ptr = new eServiceHDMI(ref);
	return 0;
}

RESULT eServiceFactoryHDMI::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ePtr<eNavigation> nav_instance;
	getNavInstance(nav_instance);
	ptr = new eServiceHDMIRecord(ref, nav_instance);
	return 0;
}

RESULT eServiceFactoryHDMI::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr = 0;
	return -1;
}

RESULT eServiceFactoryHDMI::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_info;
	return 0;
}

RESULT eServiceFactoryHDMI::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
}

void eServiceFactoryHDMI::getNavInstance(ePtr<eNavigation> &nav_instance)
{
	if (!m_nav_instance)
	{
		ePtr<iServiceHandler> service_center;
		eServiceCenter::getInstance(service_center);
		m_nav_instance = new eNavigation(service_center, HDMI_IN_REC_DECODER_INDEX);
	}
	nav_instance = m_nav_instance;
}

DEFINE_REF(eStaticServiceHDMIInfo)

eStaticServiceHDMIInfo::eStaticServiceHDMIInfo()
{
}

RESULT eStaticServiceHDMIInfo::getName(const eServiceReference &ref, std::string &name)
{
	if (ref.name.length())
	{
		name = ref.name;
	}
	else
	{
		name = "HDMI IN";
	}
	return 0;
}

int eStaticServiceHDMIInfo::getLength(const eServiceReference &ref)
{
	return -1;
}

int eStaticServiceHDMIInfo::getInfo(const eServiceReference &ref, int w)
{
	return iServiceInformation::resNA;
}

long long eStaticServiceHDMIInfo::getFileSize(const eServiceReference &ref)
{
	return 0;
}

eServiceHDMI::eServiceHDMI(eServiceReference ref)
 : m_ref(ref), m_decoder_index(0)
{

}

eServiceHDMI::~eServiceHDMI()
{
}

DEFINE_REF(eServiceHDMI);

RESULT eServiceHDMI::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceHDMI::start()
{
	m_decoder = new eTSMPEGDecoder(NULL, m_decoder_index);
	m_decoder->setVideoPID(1, 0);
	m_decoder->setAudioPID(1, 0);
	m_decoder->play();
	m_event(this, evStart);
	return 0;
}

RESULT eServiceHDMI::stop()
{
	m_decoder = NULL;
	m_event(this, evStopped);
	return 0;
}

RESULT eServiceHDMI::setTarget(int target)
{
	m_decoder_index = target;
	return 0;
}

RESULT eServiceHDMI::info(ePtr<iServiceInformation> &i)
{
	i = this;
	return 0;
}

RESULT eServiceHDMI::getName(std::string &name)
{
	if (m_ref.name.length())
	{
		name = m_ref.name;
	}
	else
	{
		name = "HDMI IN";
	}
	return 0;
}

int eServiceHDMI::getInfo(int w)
{
	return resNA;
}

std::string eServiceHDMI::getInfoString(int w)
{
	return "";
}

PyObject* eServiceHDMI::getInfoObject(int w)
{
	Py_RETURN_NONE;
}

DEFINE_REF(eServiceHDMIRecord);

eServiceHDMIRecord::eServiceHDMIRecord(const eServiceReference &ref, ePtr<eNavigation> &nav_instance)
{
	m_ref = ref;
	m_state = stateIdle;
	m_target_fd = -1;
	m_error = 0;
	m_encoder_fd = -1;
	m_thread = NULL;
	m_nav_instance = nav_instance;
}

RESULT eServiceHDMIRecord::prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id, const char *name, const char *descr, const char *tags, bool descramble, bool recordecm)
{
	m_filename = filename;

	if (m_state == stateIdle)
	{
		return doPrepare();
	}
	return -1;
}

RESULT eServiceHDMIRecord::prepareStreaming()
{
	return -1;
}

RESULT eServiceHDMIRecord::start(bool simulate)
{
	m_simulate = simulate;
	m_event((iRecordableService*)this, evStart);
	return doRecord();
}

RESULT eServiceHDMIRecord::stop()
{
	if (!m_simulate)
		eDebug("[eServiceHDMIRecord] stop recording!");
	if (m_state == stateRecording)
	{
		if (m_thread)
		{
			m_thread->stop();
			m_thread->stopSaveMetaInformation();
		}
		if (m_target_fd >= 0)
		{
			::close(m_target_fd);
			m_target_fd = -1;
		}

		m_state = statePrepared;
	} else if (!m_simulate)
		eDebug("[eServiceHDMIRecord] (was not recording)");
	if (m_state == statePrepared)
	{
		delete m_thread;
		m_thread = NULL;
		m_nav_instance->stopService();
		if (m_encoder_fd >= 0)
		{
			::close(m_encoder_fd);
			m_encoder_fd = -1;
		}
		m_state = stateIdle;
	}
	m_event((iRecordableService*)this, evRecordStopped);
	return 0;
}

int eServiceHDMIRecord::doPrepare()
{
	if (!m_simulate && m_encoder_fd < 0)
	{
		if (m_nav_instance->playService(m_ref) >= 0)
		{
			char filename[128];
			snprintf(filename, sizeof(filename), "/dev/encoder%d", HDMI_IN_REC_ENCODER_INDEX);
			m_encoder_fd = open(filename, O_RDONLY);
		}
		if (m_encoder_fd < 0)
			return -1;
	}
	m_state = statePrepared;
	return 0;
}

int eServiceHDMIRecord::doRecord()
{
	int err = doPrepare();
	if (err)
	{
		m_error = errTuneFailed;
		m_event((iRecordableService*)this, evRecordFailed);
		return err;
	}

	if (!m_thread && !m_simulate)
	{
		eDebug("[eServiceHDMIRecord] Recording to %s...", m_filename.c_str());
		::remove(m_filename.c_str());
		int fd = ::open(m_filename.c_str(), O_WRONLY | O_CREAT | O_LARGEFILE | O_CLOEXEC, 0666);
		if (fd < 0)
		{
			eDebug("[eServiceHDMIRecord] can't open recording file: %m");
			m_error = errOpenRecordFile;
			m_event((iRecordableService*)this, evRecordFailed);
			return errOpenRecordFile;
		}

		m_thread = new eDVBRecordFileThread();
		m_target_fd = fd;
	}

	eDebug("[eServiceHDMIRecord] start recording...");

	if (m_state != stateRecording)
	{
		if (m_thread && m_encoder_fd >= 0)
		{
			m_thread->startSaveMetaInformation(m_filename);
			m_thread->start(m_encoder_fd, m_target_fd);
		}
		m_state = stateRecording;
	}

	m_error = 0;
	m_event((iRecordableService*)this, evRecordRunning);
	return 0;
}

RESULT eServiceHDMIRecord::stream(ePtr<iStreamableService> &ptr)
{
	ptr = NULL;
	return -1;
}

RESULT eServiceHDMIRecord::subServices(ePtr<iSubserviceList> &ptr)
{
	ptr = NULL;
	return -1;
}

RESULT eServiceHDMIRecord::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eServiceHDMIRecord::connectEvent(const Slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iRecordableService*)this, m_event.connect(event));
	return 0;
}

eAutoInitPtr<eServiceFactoryHDMI> init_eServiceFactoryHDMI(eAutoInitNumbers::service + 1, "eServiceFactoryHDMI");
