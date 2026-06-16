#ifndef AUBO_SDK_SyncMove_C_H
#define AUBO_SDK_SyncMove_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int syncMoveOn(SYNC_MOVE_HANDLER h, const char *syncident,
                        const char **taskset);
ARCS_ABI BOOL syncMoveSegment(SYNC_MOVE_HANDLER h, int id);
ARCS_ABI int syncMoveOff(SYNC_MOVE_HANDLER h, const char *syncident);
ARCS_ABI int syncMoveUndo(SYNC_MOVE_HANDLER h);
ARCS_ABI int waitSyncTasks(SYNC_MOVE_HANDLER h, const char *syncident,
                           const char **taskset);
ARCS_ABI BOOL isSyncMoveOn(SYNC_MOVE_HANDLER h);
ARCS_ABI int syncMoveSuspend(SYNC_MOVE_HANDLER h);
ARCS_ABI int syncMoveResume(SYNC_MOVE_HANDLER h);
#ifdef __cplusplus
}
#endif

#endif
