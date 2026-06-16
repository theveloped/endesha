#ifndef AUBO_SDK_RobotAlgorithm_C_H
#define AUBO_SDK_RobotAlgorithm_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI ForceSensorCalibResult_C
calibrateTcpForceSensor(ROBOT_ALGORITHM_HANDLER h, const double *forces,
                        int forces_rows, const double *poses, int poses_rows);
ARCS_ABI ForceSensorCalibResult_C
calibrateTcpForceSensor2(ROBOT_ALGORITHM_HANDLER h, const double *forces,
                         int forces_rows, const double *poses, int poses_rows);
ARCS_ABI int payloadIdentify(ROBOT_ALGORITHM_HANDLER h,
                             const char *data_no_payload,
                             const char *data_with_payload);
ARCS_ABI int payloadIdentify1(ROBOT_ALGORITHM_HANDLER h, const char *file_name);
ARCS_ABI int payloadCalculateFinished(ROBOT_ALGORITHM_HANDLER h);
ARCS_ABI Payload_C getPayloadIdentifyResult(ROBOT_ALGORITHM_HANDLER h);
ARCS_ABI int generatePayloadIdentifyTraj(ROBOT_ALGORITHM_HANDLER h,
                                         const char *name,
                                         const TrajConfig_C *traj_config);
ARCS_ABI int payloadIdentifyTrajGenFinished(ROBOT_ALGORITHM_HANDLER h);
ARCS_ABI BOOL frictionModelIdentify(ROBOT_ALGORITHM_HANDLER h, const double *q,
                                    int q_rows, const double *qd, int qd_rows,
                                    const double *qdd, int qdd_rows,
                                    const double *temp, int temp_rows);
ARCS_ABI int calibWorkpieceCoordinatePara(ROBOT_ALGORITHM_HANDLER h,
                                          const double *q, int q_rows, int type,
                                          double *result);
ARCS_ABI int forwardDynamics(ROBOT_ALGORITHM_HANDLER h, const double *q,
                             const double *torqs, double *result);
ARCS_ABI int forwardKinematics(ROBOT_ALGORITHM_HANDLER h, const double *q,
                               double *result);
ARCS_ABI int forwardToolKinematics(ROBOT_ALGORITHM_HANDLER h, const double *q,
                                   double *result);
ARCS_ABI int forwardDynamics1(ROBOT_ALGORITHM_HANDLER h, const double *q,
                              const double *torqs, const double *tcp_offset,
                              double *result);
ARCS_ABI int forwardKinematics1(ROBOT_ALGORITHM_HANDLER h, const double *q,
                                const double *tcp_offset, double *result);
ARCS_ABI int inverseKinematics(ROBOT_ALGORITHM_HANDLER h, const double *qnear,
                               const double *pose, double *result);
ARCS_ABI int inverseKinematicsAll(ROBOT_ALGORITHM_HANDLER h, const double *pose,
                                  double **result);
ARCS_ABI int inverseKinematics1(ROBOT_ALGORITHM_HANDLER h, const double *qnear,
                                const double *pose, const double *tcp_offset,
                                double *result);
ARCS_ABI int inverseKinematicsAll1(ROBOT_ALGORITHM_HANDLER h,
                                   const double *pose, const double *tcp_offset,
                                   double **result);
ARCS_ABI int inverseToolKinematics(ROBOT_ALGORITHM_HANDLER h,
                                   const double *qnear, const double *pose,
                                   double *result);
ARCS_ABI int inverseToolKinematicsAll(ROBOT_ALGORITHM_HANDLER h,
                                      const double *pose, double **result);
ARCS_ABI int pathMovej(ROBOT_ALGORITHM_HANDLER h, const double *q1, double r1,
                       const double *q2, double r2, double d, double **result);
ARCS_ABI int pathBlend3Points(ROBOT_ALGORITHM_HANDLER h, int type,
                              const double *q_start, const double *q_via,
                              const double *q_to, double r, double d,
                              double **result);
ARCS_ABI int calcJacobian(ROBOT_ALGORITHM_HANDLER h, const double *q,
                          BOOL base_or_end, double *result);
#ifdef __cplusplus
}
#endif

#endif
