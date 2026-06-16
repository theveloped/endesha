#ifndef AUBO_SDK_RobotManage_C_H
#define AUBO_SDK_RobotManage_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int poweron(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int startup(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int poweroff(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int backdrive(ROBOT_MANAGE_HANDLER h, BOOL enable);
ARCS_ABI int freedrive(ROBOT_MANAGE_HANDLER h, BOOL enable);
ARCS_ABI int handguideMode(ROBOT_MANAGE_HANDLER h, int32_t *freeAxes,
                           const double *feature);
ARCS_ABI int exitHandguideMode(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int getHandguideStatus(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int getHandguideTrigger(ROBOT_MANAGE_HANDLER h);
ARCS_ABI BOOL isHandguideEnabled(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int setSim(ROBOT_MANAGE_HANDLER h, BOOL enable);
ARCS_ABI int setOperationalMode(ROBOT_MANAGE_HANDLER h,
                                OperationalModeType_C mode);
ARCS_ABI OperationalModeType_C getOperationalMode(ROBOT_MANAGE_HANDLER h);
ARCS_ABI RobotControlModeType_C getRobotControlMode(ROBOT_MANAGE_HANDLER h);
ARCS_ABI BOOL isSimulationEnabled(ROBOT_MANAGE_HANDLER h);
ARCS_ABI BOOL isFreedriveEnabled(ROBOT_MANAGE_HANDLER h);
ARCS_ABI BOOL isBackdriveEnabled(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int setUnlockProtectiveStop(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int startRecord(ROBOT_MANAGE_HANDLER h, const char *file_name);
ARCS_ABI int stopRecord(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int pauseRecord(ROBOT_MANAGE_HANDLER h, BOOL pause);
ARCS_ABI int restartInterfaceBoard(ROBOT_MANAGE_HANDLER h);
ARCS_ABI int setLinkModeEnable(ROBOT_MANAGE_HANDLER h, BOOL enable);
ARCS_ABI BOOL isLinkModeEnabled(ROBOT_MANAGE_HANDLER h);
#ifdef __cplusplus
}
#endif

#endif
