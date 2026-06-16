#ifndef AUBO_SDK_RobotInterface_C_H
#define AUBO_SDK_RobotInterface_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI ROBOT_CONFIG_HANDLER robot_getRobotConfig(ROBOT_HANDLER robot);
ARCS_ABI MOTION_CONTROL_HANDLER robot_getMotionControl(ROBOT_HANDLER robot);
ARCS_ABI FORCE_CONTROL_HANDLER robot_getForceControl(ROBOT_HANDLER robot);
ARCS_ABI IO_CONTROL_HANDLER robot_getIoControl(ROBOT_HANDLER robot);
ARCS_ABI SYNC_MOVE_HANDLER robot_getSyncMove(ROBOT_HANDLER robot);
ARCS_ABI ROBOT_ALGORITHM_HANDLER robot_getRobotAlgorithm(ROBOT_HANDLER robot);
ARCS_ABI ROBOT_MANAGE_HANDLER robot_getRobotManage(ROBOT_HANDLER robot);
ARCS_ABI ROBOT_STATE_HANDLER robot_getRobotState(ROBOT_HANDLER robot);
ARCS_ABI TRACE_HANDLER robot_getTrace(ROBOT_HANDLER robot);

#ifdef __cplusplus
}
#endif

#endif
