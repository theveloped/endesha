#ifndef AUBO_SDK_MotionControl_C_H
#define AUBO_SDK_MotionControl_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI double getEqradius(MOTION_CONTROL_HANDLER h);
ARCS_ABI int setEqradius(MOTION_CONTROL_HANDLER h, double eqradius);
ARCS_ABI double getSpeedFraction(MOTION_CONTROL_HANDLER h);
ARCS_ABI int setSpeedFraction(MOTION_CONTROL_HANDLER h, double fraction);
ARCS_ABI int speedFractionCritical(MOTION_CONTROL_HANDLER h, BOOL enable);
ARCS_ABI BOOL isSpeedFractionCritical(MOTION_CONTROL_HANDLER h);
ARCS_ABI BOOL isBlending(MOTION_CONTROL_HANDLER h);
ARCS_ABI int pathOffsetEnable(MOTION_CONTROL_HANDLER h);
ARCS_ABI int pathOffsetSet(MOTION_CONTROL_HANDLER h, const double *offset,
                           int type);
ARCS_ABI int pathOffsetDisable(MOTION_CONTROL_HANDLER h);
ARCS_ABI int jointOffsetEnable(MOTION_CONTROL_HANDLER h);
ARCS_ABI int jointOffsetSet(MOTION_CONTROL_HANDLER h, const double *offset,
                            int type);
ARCS_ABI int jointOffsetDisable(MOTION_CONTROL_HANDLER h);
ARCS_ABI int getTrajectoryQueueSize(MOTION_CONTROL_HANDLER h);
ARCS_ABI int getQueueSize(MOTION_CONTROL_HANDLER h);
ARCS_ABI int getExecId(MOTION_CONTROL_HANDLER h);
ARCS_ABI double getDuration(MOTION_CONTROL_HANDLER h, int id);
ARCS_ABI double getMotionLeftTime(MOTION_CONTROL_HANDLER h, int id);
ARCS_ABI double getProgress(MOTION_CONTROL_HANDLER h);
ARCS_ABI int setWorkObjectHold(MOTION_CONTROL_HANDLER h,
                               const char *module_name,
                               const double *mounting_pose);
ARCS_ABI char *getWorkObjectHold(MOTION_CONTROL_HANDLER h);
ARCS_ABI int getPauseJointPositions(MOTION_CONTROL_HANDLER h, double *result);
ARCS_ABI int setServoMode(MOTION_CONTROL_HANDLER h, BOOL enable);
ARCS_ABI BOOL isServoModeEnabled(MOTION_CONTROL_HANDLER h);
ARCS_ABI int setServoModeSelect(MOTION_CONTROL_HANDLER h, int mode);
ARCS_ABI int getServoModeSelect(MOTION_CONTROL_HANDLER h);
ARCS_ABI int servoJoint(MOTION_CONTROL_HANDLER h, const double *q, double a,
                        double v, double t, double lookahead_time, double gain);
ARCS_ABI int servoCartesian(MOTION_CONTROL_HANDLER h, const double *pose,
                            double a, double v, double t, double lookahead_time,
                            double gain);
ARCS_ABI int servoJointWithAxes(MOTION_CONTROL_HANDLER h, const double *q,
                                const double *extq, double a, double v,
                                double t, double lookahead_time, double gain);
ARCS_ABI int servoCartesianWithAxes(MOTION_CONTROL_HANDLER h,
                                    const double *pose, const double *extq,
                                    double a, double v, double t,
                                    double lookahead_time, double gain);
ARCS_ABI int trackJoint(MOTION_CONTROL_HANDLER h, const double *q, double t,
                        double smooth_scale, double delay_sacle);
ARCS_ABI int trackCartesian(MOTION_CONTROL_HANDLER h, const double *pose,
                            double t, double smooth_scale, double delay_sacle);
ARCS_ABI int followJoint(MOTION_CONTROL_HANDLER h, const double *q);
ARCS_ABI int followLine(MOTION_CONTROL_HANDLER h, const double *pose);
ARCS_ABI int speedJoint(MOTION_CONTROL_HANDLER h, const double *qd, double a,
                        double t);
ARCS_ABI int resumeSpeedJoint(MOTION_CONTROL_HANDLER h, const double *qd,
                              double a, double t);
ARCS_ABI int speedLine(MOTION_CONTROL_HANDLER h, const double *xd, double a,
                       double t);
ARCS_ABI int resumeSpeedLine(MOTION_CONTROL_HANDLER h, const double *xd,
                             double a, double t);
ARCS_ABI int moveSpline(MOTION_CONTROL_HANDLER h, const double *q, double a,
                        double v, double duration);
ARCS_ABI int moveJoint(MOTION_CONTROL_HANDLER h, const double *q, double a,
                       double v, double blend_radius, double duration);
ARCS_ABI int resumeMoveJoint(MOTION_CONTROL_HANDLER h, const double *q,
                             double a, double v, double duration);
ARCS_ABI int moveLine(MOTION_CONTROL_HANDLER h, const double *pose, double a,
                      double v, double blend_radius, double duration);
ARCS_ABI int moveProcess(MOTION_CONTROL_HANDLER h, const double *pose, double a,
                         double v, double blend_radius);
ARCS_ABI int resumeMoveLine(MOTION_CONTROL_HANDLER h, const double *pose,
                            double a, double v, double duration);
ARCS_ABI int moveCircle(MOTION_CONTROL_HANDLER h, const double *via_pose,
                        const double *end_pose, double a, double v,
                        double blend_radius, double duration);
ARCS_ABI int setCirclePathMode(MOTION_CONTROL_HANDLER h, int mode);
ARCS_ABI int moveCircle2(MOTION_CONTROL_HANDLER h,
                         const CircleParameters_C *param);
ARCS_ABI int pathBufferAlloc(MOTION_CONTROL_HANDLER h, const char *name,
                             int type, int size);
ARCS_ABI int pathBufferAppend(MOTION_CONTROL_HANDLER h, const char *name,
                              const double *waypoints, int rows);
ARCS_ABI int pathBufferEval(MOTION_CONTROL_HANDLER h, const char *name,
                            const double *a, const double *v, double t);
ARCS_ABI BOOL pathBufferValid(MOTION_CONTROL_HANDLER h, const char *name);
ARCS_ABI int pathBufferFree(MOTION_CONTROL_HANDLER h, const char *name);
ARCS_ABI int pathBufferList(MOTION_CONTROL_HANDLER h, char **result);
ARCS_ABI int movePathBuffer(MOTION_CONTROL_HANDLER h, const char *name);
ARCS_ABI int moveIntersection(MOTION_CONTROL_HANDLER h, const double *poses,
                              int rows, double a, double v,
                              double main_pipe_radius, double sub_pipe_radius,
                              double normal_distance, double normal_alpha);
ARCS_ABI int stopJoint(MOTION_CONTROL_HANDLER h, double acc);
ARCS_ABI int resumeStopJoint(MOTION_CONTROL_HANDLER h, double acc);
ARCS_ABI int stopLine(MOTION_CONTROL_HANDLER h, double acc, double acc_rot);
ARCS_ABI int resumeStopLine(MOTION_CONTROL_HANDLER h, double acc,
                            double acc_rot);
ARCS_ABI int weaveStart(MOTION_CONTROL_HANDLER h, const char *params);
ARCS_ABI int weaveEnd(MOTION_CONTROL_HANDLER h);
ARCS_ABI int storePath(MOTION_CONTROL_HANDLER h, BOOL keep_sync);
ARCS_ABI int stopMove(MOTION_CONTROL_HANDLER h, BOOL quick, BOOL all_tasks);
ARCS_ABI int startMove(MOTION_CONTROL_HANDLER h);
ARCS_ABI int clearPath(MOTION_CONTROL_HANDLER h);
ARCS_ABI int restoPath(MOTION_CONTROL_HANDLER h);
ARCS_ABI int setFuturePointSamplePeriod(MOTION_CONTROL_HANDLER h,
                                        double sample_time);
ARCS_ABI int getFuturePathPointsJoint(MOTION_CONTROL_HANDLER h,
                                      double **result);
ARCS_ABI int conveyorTrackCircle(MOTION_CONTROL_HANDLER h, int encoder_id,
                                 const double *center, BOOL rotate_tool);
ARCS_ABI int conveyorTrackLine(MOTION_CONTROL_HANDLER h, int encoder_id,
                               const double *direction);
ARCS_ABI int conveyorTrackStop(MOTION_CONTROL_HANDLER h, int encoder_id,
                               double a);
ARCS_ABI int setConveyorTrackEncoder(MOTION_CONTROL_HANDLER h, int encoder_id,
                                     int tick_per_meter);
ARCS_ABI int setConveyorTrackLimit(MOTION_CONTROL_HANDLER h, int encoder_id,
                                   double limit);
ARCS_ABI int setConveyorTrackStartWindow(MOTION_CONTROL_HANDLER h,
                                         int encoder_id, double window_min,
                                         double window_max);
ARCS_ABI int setConveyorTrackSensorOffset(MOTION_CONTROL_HANDLER h,
                                          int encoder_id, double offset);
ARCS_ABI int setConveyorTrackSyncSeparation(MOTION_CONTROL_HANDLER h,
                                            int encoder_id, double distance,
                                            double time);
ARCS_ABI int setConveyorTrackCompensate(MOTION_CONTROL_HANDLER h,
                                        int encoder_id, double comp);
ARCS_ABI BOOL isConveyorTrackSync(MOTION_CONTROL_HANDLER h, int encoder_id);
ARCS_ABI BOOL isConveyorTrackExceed(MOTION_CONTROL_HANDLER h, int encoder_id);
ARCS_ABI int getConveyorTrackQueue(MOTION_CONTROL_HANDLER h, int encoder_id,
                                   double *result);
ARCS_ABI int getConveyorTrackNextItem(MOTION_CONTROL_HANDLER h, int encoder_id);
ARCS_ABI int conveyorTrackCreatItem(MOTION_CONTROL_HANDLER h, int encoder_id,
                                    int item_id, const double *offset);
ARCS_ABI BOOL hasItemOnConveyorToTrack(MOTION_CONTROL_HANDLER h,
                                       int encoder_id);
ARCS_ABI BOOL conveyorTrackSwitch(MOTION_CONTROL_HANDLER h, int encoder_id);
ARCS_ABI int conveyorTrackClearItems(MOTION_CONTROL_HANDLER h, int encoder_id);
ARCS_ABI int moveSpiral(MOTION_CONTROL_HANDLER h,
                        const SpiralParameters_C *param, double blend_radius,
                        double v, double a, double t);
ARCS_ABI int pathOffsetLimits(MOTION_CONTROL_HANDLER h, double v, double a);
ARCS_ABI int pathOffsetCoordinate(MOTION_CONTROL_HANDLER h, int ref_coord);
ARCS_ABI int getLookAheadSize(MOTION_CONTROL_HANDLER h);
ARCS_ABI int setLookAheadSize(MOTION_CONTROL_HANDLER h, int size);
#ifdef __cplusplus
}
#endif

#endif
