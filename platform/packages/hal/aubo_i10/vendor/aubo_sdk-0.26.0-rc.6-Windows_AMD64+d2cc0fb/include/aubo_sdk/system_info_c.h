#ifndef AUBO_SDK_SystemInfo_C_H
#define AUBO_SDK_SystemInfo_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int getControlSoftwareVersionCode(SYSTEM_INFO_HANDLER h);
ARCS_ABI int getControlSoftwareFullVersion(SYSTEM_INFO_HANDLER h, char *result);
ARCS_ABI int getInterfaceVersionCode(SYSTEM_INFO_HANDLER h);
ARCS_ABI int getControlSoftwareBuildDate(SYSTEM_INFO_HANDLER h, char *result);
ARCS_ABI int getControlSoftwareVersionHash(SYSTEM_INFO_HANDLER h, char *result);
ARCS_ABI uint64_t getControlSystemTime(SYSTEM_INFO_HANDLER h);
#ifdef __cplusplus
}
#endif

#endif
