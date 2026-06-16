#ifndef AUBO_SDK_Trace_C_H
#define AUBO_SDK_Trace_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int alarm(TRACE_HANDLER h, TraceLevel_C level, int code,
                   const char **args);
ARCS_ABI int popup(TRACE_HANDLER h, TraceLevel_C level, const char *title,
                   const char *msg, int mode);
ARCS_ABI int textmsg(TRACE_HANDLER h, const char *msg);
ARCS_ABI int notify(TRACE_HANDLER h, const char *msg);
ARCS_ABI int peek(TRACE_HANDLER h, uint64_t num, uint64_t last_time,
                  struct RobotMsg_C *result);
#ifdef __cplusplus
}
#endif

#endif
