#ifndef AUBO_SDK_RobotConfig_C_H
#define AUBO_SDK_RobotConfig_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int getDof(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int getName(ROBOT_CONFIG_HANDLER h, char *result);
ARCS_ABI double getCycletime(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int setSlowDownFraction(ROBOT_CONFIG_HANDLER h, int level,
                                 double fraction);
ARCS_ABI double getSlowDownFraction(ROBOT_CONFIG_HANDLER h, int level);
ARCS_ABI int getRobotType(ROBOT_CONFIG_HANDLER h, char *result);
ARCS_ABI int getRobotSubType(ROBOT_CONFIG_HANDLER h, char *result);
ARCS_ABI int getControlBoxType(ROBOT_CONFIG_HANDLER h, char *result);
ARCS_ABI double getDefaultToolAcc(ROBOT_CONFIG_HANDLER h);
ARCS_ABI double getDefaultToolSpeed(ROBOT_CONFIG_HANDLER h);
ARCS_ABI double getDefaultJointAcc(ROBOT_CONFIG_HANDLER h);
ARCS_ABI double getDefaultJointSpeed(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int setMountingPose(ROBOT_CONFIG_HANDLER h, const double *pose);
ARCS_ABI int getMountingPose(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int setCollisionLevel(ROBOT_CONFIG_HANDLER h, int level);
ARCS_ABI int getCollisionLevel(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int setCollisionStopType(ROBOT_CONFIG_HANDLER h, int type);
ARCS_ABI int getCollisionStopType(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int setHomePosition(ROBOT_CONFIG_HANDLER h, const double *positions);
ARCS_ABI int getHomePosition(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int setFreedriveDamp(ROBOT_CONFIG_HANDLER h, const double *damp);
ARCS_ABI int getFreedriveDamp(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getTcpForceSensorNames(ROBOT_CONFIG_HANDLER h, char **result);
ARCS_ABI int selectTcpForceSensor(ROBOT_CONFIG_HANDLER h, const char *name);
ARCS_ABI BOOL hasTcpForceSensor(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int setTcpForceOffset(ROBOT_CONFIG_HANDLER h,
                               const double *force_offset);
ARCS_ABI int getTcpForceOffset(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getBaseForceSensorNames(ROBOT_CONFIG_HANDLER h, char **result);
ARCS_ABI int selectBaseForceSensor(ROBOT_CONFIG_HANDLER h, const char *name);
ARCS_ABI BOOL hasBaseForceSensor(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int setBaseForceOffset(ROBOT_CONFIG_HANDLER h,
                                const double *force_offset);
ARCS_ABI int getBaseForceOffset(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int setPersistentParameters(ROBOT_CONFIG_HANDLER h, const char *param);
ARCS_ABI int setKinematicsCompensate(ROBOT_CONFIG_HANDLER h,
                                     const DHParam_C *param);
ARCS_ABI int setHardwareCustomParameters(ROBOT_CONFIG_HANDLER h,
                                         const char *param);
ARCS_ABI int getHardwareCustomParameters(ROBOT_CONFIG_HANDLER h,
                                         const char *param, char *result);
ARCS_ABI int setRobotZero(ROBOT_CONFIG_HANDLER h);
ARCS_ABI DHParam_C *getKinematicsParam(ROBOT_CONFIG_HANDLER h, BOOL real);
ARCS_ABI DHComp_C *getKinematicsCompensate(ROBOT_CONFIG_HANDLER h,
                                           double ref_temperature);
ARCS_ABI uint32_t getSafetyParametersCheckSum(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int confirmSafetyParameters(
    ROBOT_CONFIG_HANDLER h, const RobotSafetyParameterRange_C *parameters);
ARCS_ABI uint32_t calcSafetyParametersCheckSum(
    ROBOT_CONFIG_HANDLER h, const RobotSafetyParameterRange_C *parameters);
ARCS_ABI int getJointMaxPositions(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getJointMinPositions(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getJointMaxSpeeds(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getJointMaxAccelerations(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getTcpMaxSpeeds(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getTcpMaxAccelerations(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI BOOL toolSpaceInRange(ROBOT_CONFIG_HANDLER h, const double *pose);
ARCS_ABI int setPayload(ROBOT_CONFIG_HANDLER h, double m, const double *cog,
                        const double *aom, const double *inertia);
ARCS_ABI Payload_C getPayload(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int getTcpOffset(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getGravity(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int setGravity(ROBOT_CONFIG_HANDLER h, const double *gravity);
ARCS_ABI int setTcpOffset(ROBOT_CONFIG_HANDLER h, const double *offset);
ARCS_ABI int setToolInertial(ROBOT_CONFIG_HANDLER h, double m,
                             const double *com, const double *inertial);
ARCS_ABI int firmwareUpdate(ROBOT_CONFIG_HANDLER h, const char *fw);
ARCS_ABI double getFirmwareUpdateProcess(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int setTcpForceSensorPose(ROBOT_CONFIG_HANDLER h,
                                   const double *sensor_pose);
ARCS_ABI int getTcpForceSensorPose(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getLimitJointMaxPositions(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getLimitJointMinPositions(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getLimitJointMaxSpeeds(ROBOT_CONFIG_HANDLER h, double *result);
ARCS_ABI int getLimitJointMaxAccelerations(ROBOT_CONFIG_HANDLER h,
                                           double *result);
ARCS_ABI double getLimitTcpMaxSpeed(ROBOT_CONFIG_HANDLER h);
ARCS_ABI SafeguedStopType_C getSafeguardStopType(ROBOT_CONFIG_HANDLER h);
ARCS_ABI int getSafeguardStopSource(ROBOT_CONFIG_HANDLER h);
#ifdef __cplusplus
}
#endif

#endif
