#ifndef AUBO_SDK_RobotState_C_H
#define AUBO_SDK_RobotState_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI RobotModeType_C getRobotModeType(ROBOT_STATE_HANDLER h);
ARCS_ABI SafetyModeType_C getSafetyModeType(ROBOT_STATE_HANDLER h);
ARCS_ABI BOOL isPowerOn(ROBOT_STATE_HANDLER h);
ARCS_ABI BOOL isSteady(ROBOT_STATE_HANDLER h);
ARCS_ABI BOOL isCollisionOccurred(ROBOT_STATE_HANDLER h);
ARCS_ABI BOOL isWithinSafetyLimits(ROBOT_STATE_HANDLER h);
ARCS_ABI int getTcpPose(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getActualTcpOffset(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getTargetTcpPose(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getToolPose(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getTcpSpeed(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getTcpForce(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getElbowPosistion(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getElbowVelocity(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getBaseForce(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getTcpTargetPose(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getTcpTargetSpeed(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getTcpTargetForce(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointState(ROBOT_STATE_HANDLER h, JointStateType_C *result);
ARCS_ABI int getJointServoMode(ROBOT_STATE_HANDLER h,
                               JointServoModeType_C *result);
ARCS_ABI int getJointPositions(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointPositionsHistory(ROBOT_STATE_HANDLER h, int steps,
                                      double *result);
ARCS_ABI int getJointSpeeds(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointAccelerations(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointTorqueSensors(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointContactTorques(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getBaseForceSensor(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getTcpForceSensors(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointCurrents(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointVoltages(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointTemperatures(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointUniqueIds(ROBOT_STATE_HANDLER h, char **result);
ARCS_ABI int getJointFirmwareVersions(ROBOT_STATE_HANDLER h, int *result);
ARCS_ABI int getJointHardwareVersions(ROBOT_STATE_HANDLER h, int *result);
ARCS_ABI int getMasterBoardUniqueId(ROBOT_STATE_HANDLER h, char *result);
ARCS_ABI int getMasterBoardFirmwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getMasterBoardHardwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getSlaveBoardUniqueId(ROBOT_STATE_HANDLER h, char *result);
ARCS_ABI int getSlaveBoardFirmwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getSlaveBoardHardwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getToolUniqueId(ROBOT_STATE_HANDLER h, char *result);
ARCS_ABI int getToolFirmwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getToolHardwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getToolCommMode(ROBOT_STATE_HANDLER h);
ARCS_ABI int getPedestalUniqueId(ROBOT_STATE_HANDLER h, char *result);
ARCS_ABI int getPedestalFirmwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getPedestalHardwareVersion(ROBOT_STATE_HANDLER h);
ARCS_ABI int getJointTargetPositions(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointTargetSpeeds(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointTargetAccelerations(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointTargetTorques(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI int getJointTargetCurrents(ROBOT_STATE_HANDLER h, double *result);
ARCS_ABI double getControlBoxTemperature(ROBOT_STATE_HANDLER h);
ARCS_ABI double getControlBoxHumidity(ROBOT_STATE_HANDLER h);
ARCS_ABI double getMainVoltage(ROBOT_STATE_HANDLER h);
ARCS_ABI double getMainCurrent(ROBOT_STATE_HANDLER h);
ARCS_ABI double getRobotVoltage(ROBOT_STATE_HANDLER h);
ARCS_ABI double getRobotCurrent(ROBOT_STATE_HANDLER h);
ARCS_ABI int getSlowDownLevel(ROBOT_STATE_HANDLER h);
#ifdef __cplusplus
}
#endif

#endif
