#ifndef AUBO_SDK_ForceControl_C_H
#define AUBO_SDK_ForceControl_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int fcEnable(FORCE_CONTROL_HANDLER h);
ARCS_ABI int fcDisable(FORCE_CONTROL_HANDLER h);
ARCS_ABI BOOL isFcEnabled(FORCE_CONTROL_HANDLER h);
ARCS_ABI int setTargetForce(FORCE_CONTROL_HANDLER h, const double *feature,
                            const uint8_t *compliance, const double *wrench,
                            const double *limits, TaskFrameType_C type);
ARCS_ABI int setDynamicModel(FORCE_CONTROL_HANDLER h, const double *m,
                             const double *d, const double *k);
ARCS_ABI DynamicsModel_C getDynamicModel(FORCE_CONTROL_HANDLER h);
ARCS_ABI int setDynamicModelContact(FORCE_CONTROL_HANDLER h,
                                    const double *env_stiff,
                                    const double *damp_scale,
                                    const double *stiff_scale);
ARCS_ABI int setCondForce(FORCE_CONTROL_HANDLER h, const double *min,
                          const double *max, BOOL outside, double timeout);
ARCS_ABI int setCondOrient(FORCE_CONTROL_HANDLER h, const double *frame,
                           double max_angle, double max_rot, BOOL outside,
                           double timeout);
ARCS_ABI int setCondPlane(FORCE_CONTROL_HANDLER h, const double *plane,
                          double timeout);
ARCS_ABI int setCondCylinder(FORCE_CONTROL_HANDLER h, const double *axis,
                             double radius, BOOL outside, double timeout);
ARCS_ABI int setCondSphere(FORCE_CONTROL_HANDLER h, const double *center,
                           double radius, BOOL outside, double timeout);
ARCS_ABI int setCondTcpSpeed(FORCE_CONTROL_HANDLER h, const double *min,
                             const double *max, BOOL outside, double timeout);
ARCS_ABI int setCondActive(FORCE_CONTROL_HANDLER h);
ARCS_ABI int setCondDistance(FORCE_CONTROL_HANDLER h, double distance,
                             double timeout);
ARCS_ABI int setCondAdvanced(FORCE_CONTROL_HANDLER h, const char *type,
                             const double *args, double timeout);
ARCS_ABI BOOL isCondFullfiled(FORCE_CONTROL_HANDLER h);
ARCS_ABI int setSupvForce(FORCE_CONTROL_HANDLER h, const double *min,
                          const double *max);
ARCS_ABI int setSupvOrient(FORCE_CONTROL_HANDLER h, const double *frame,
                           double max_angle, double max_rot, BOOL outside);
ARCS_ABI int setSupvPosBox(FORCE_CONTROL_HANDLER h, const double *frame,
                           const double *box);
ARCS_ABI int setSupvPosCylinder(FORCE_CONTROL_HANDLER h, const double *frame,
                                const double *cylinder);
ARCS_ABI int setSupvPosSphere(FORCE_CONTROL_HANDLER h, const double *frame,
                              const double *sphere);
ARCS_ABI int setSupvReoriSpeed(FORCE_CONTROL_HANDLER h,
                               const double *speed_limit, BOOL outside,
                               double timeout);
ARCS_ABI int setSupvTcpSpeed(FORCE_CONTROL_HANDLER h, const double *speed_limit,
                             BOOL outside, double timeout);
ARCS_ABI int setLpFilter(FORCE_CONTROL_HANDLER h, const double *cutoff_freq);
ARCS_ABI int resetLpFilter(FORCE_CONTROL_HANDLER h);
ARCS_ABI int speedChangeTune(FORCE_CONTROL_HANDLER h, int speed_levels,
                             double speed_ratio_min);
ARCS_ABI int speedChangeEnable(FORCE_CONTROL_HANDLER h, double ref_force);
ARCS_ABI int speedChangeDisable(FORCE_CONTROL_HANDLER h);
ARCS_ABI int setDamping(FORCE_CONTROL_HANDLER h, const double *damping,
                        double ramp_time);
ARCS_ABI int resetDamping(FORCE_CONTROL_HANDLER h);
ARCS_ABI int softFloatEnable(FORCE_CONTROL_HANDLER h);
ARCS_ABI int softFloatDisable(FORCE_CONTROL_HANDLER h);
ARCS_ABI BOOL isSoftFloatEnabled(FORCE_CONTROL_HANDLER h);
ARCS_ABI int setSoftFloatParams(FORCE_CONTROL_HANDLER h, BOOL joint_space,
                                const uint8_t *select,
                                const double *stiff_percent,
                                const double *stiff_damp_ratio,
                                const double *force_threshold,
                                const double *force_limit);
ARCS_ABI int toolContact(FORCE_CONTROL_HANDLER h, const uint8_t *direction);
#ifdef __cplusplus
}
#endif

#endif
