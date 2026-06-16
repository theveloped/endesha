#ifndef AUBO_SDK_Math_C_H
#define AUBO_SDK_Math_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int poseAdd(MATH_HANDLER h, const double *p1, const double *p2,
                     double *result);
ARCS_ABI int poseSub(MATH_HANDLER h, const double *p1, const double *p2,
                     double *result);
ARCS_ABI int interpolatePose(MATH_HANDLER h, const double *p1, const double *p2,
                             double alpha, double *result);
ARCS_ABI int poseTrans(MATH_HANDLER h, const double *pose_from,
                       const double *pose_from_to, double *result);
ARCS_ABI int poseTransInv(MATH_HANDLER h, const double *pose_from,
                          const double *pose_to_from, double *result);
ARCS_ABI int poseInverse(MATH_HANDLER h, const double *pose, double *result);
ARCS_ABI double poseDistance(MATH_HANDLER h, const double *p1,
                             const double *p2);
ARCS_ABI double poseAngleDistance(MATH_HANDLER h, const double *p1,
                                  const double *p2);
ARCS_ABI BOOL poseEqual(MATH_HANDLER h, const double *p1, const double *p2,
                        double eps);
ARCS_ABI int transferRefFrame(MATH_HANDLER h, const double *F_b_a_old,
                              Vector3d_C V_in_a, int type, double *result);
ARCS_ABI int poseRotation(MATH_HANDLER h, const double *pose,
                          const double *rotv, double *result);
ARCS_ABI int rpyToQuaternion(MATH_HANDLER h, const double *rpy, double *result);
ARCS_ABI int quaternionToRpy(MATH_HANDLER h, const double *quant,
                             double *result);
ARCS_ABI int tcpOffsetIdentify(MATH_HANDLER h, const double *poses, int rows,
                               double *result);
ARCS_ABI int calibrateCoordinate(MATH_HANDLER h, const double *poses, int rows,
                                 int type, double *result);
ARCS_ABI int calculateCircleFourthPoint(MATH_HANDLER h, const double *p1,
                                        const double *p2, const double *p3,
                                        int mode, double *result);
ARCS_ABI int forceTrans(MATH_HANDLER h, const double *pose_a_in_b,
                        const double *force_in_a, double *result);
ARCS_ABI int getDeltaPoseBySensorDistance(MATH_HANDLER h,
                                          const double *distances,
                                          double position, double radius,
                                          double track_scale, double *result);
ARCS_ABI int deltaPoseTrans(MATH_HANDLER h, const double *pose_a_in_b,
                            const double *ft_in_a, double *result);
ARCS_ABI int deltaPoseAdd(MATH_HANDLER h, const double *pose_a_in_b,
                          const double *v_in_b, double *result);
#ifdef __cplusplus
}
#endif

#endif
