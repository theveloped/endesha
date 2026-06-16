#ifndef AUBO_SDK_RuntimeMachine_C_H
#define AUBO_SDK_RuntimeMachine_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif

ARCS_ABI int newTask(RUNTIME_MACHINE_HADNLER h, BOOL daemon);
ARCS_ABI int deleteTask(RUNTIME_MACHINE_HADNLER h, int tid);
ARCS_ABI int detachTask(RUNTIME_MACHINE_HADNLER h, int tid);
ARCS_ABI BOOL isTaskAlive(RUNTIME_MACHINE_HADNLER h, int tid);
ARCS_ABI int nop(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int switchTask(RUNTIME_MACHINE_HADNLER h, int tid);
ARCS_ABI int setLabel(RUNTIME_MACHINE_HADNLER h, int tid, const char *lineno);
ARCS_ABI int setPlanContext(RUNTIME_MACHINE_HADNLER h, int tid, int lineno,
                            const char *comment);
ARCS_ABI int gotoLine(RUNTIME_MACHINE_HADNLER h, int lineno);
ARCS_ABI int getAdvancePlanContext(RUNTIME_MACHINE_HADNLER h, int tid,
                                   struct PlanContext_C *result);
ARCS_ABI int getAdvancePtr(RUNTIME_MACHINE_HADNLER h, int tid);
ARCS_ABI int getMainPtr(RUNTIME_MACHINE_HADNLER h, int tid);
ARCS_ABI int getInterpPtr(RUNTIME_MACHINE_HADNLER h, int tid);
ARCS_ABI int getPlanContext(RUNTIME_MACHINE_HADNLER h, int tid,
                            struct PlanContext_C *result);
ARCS_ABI int getExecutionStatus(RUNTIME_MACHINE_HADNLER h,
                                struct ExecutionStatus_C *result);
ARCS_ABI int getExecutionStatus1(RUNTIME_MACHINE_HADNLER h,
                                 struct ExecutionStatus1_C *result);
ARCS_ABI int loadProgram(RUNTIME_MACHINE_HADNLER h, const char *program);
ARCS_ABI int runProgram(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int start(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int stop(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int abort1(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int pause(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int step(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int setResumeWait(RUNTIME_MACHINE_HADNLER h, BOOL wait);
ARCS_ABI int resume(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI RuntimeState_C getStatus(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI RuntimeState_C getRuntimeState(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int setBreakPoint(RUNTIME_MACHINE_HADNLER h, int lineno);
ARCS_ABI int removeBreakPoint(RUNTIME_MACHINE_HADNLER h, int lineno);
ARCS_ABI int clearBreakPoints(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int timerStart(RUNTIME_MACHINE_HADNLER h, const char *name);
ARCS_ABI int timerStop(RUNTIME_MACHINE_HADNLER h, const char *name);
ARCS_ABI int timerReset(RUNTIME_MACHINE_HADNLER h, const char *name);
ARCS_ABI int timerDelete(RUNTIME_MACHINE_HADNLER h, const char *name);
ARCS_ABI double getTimer(RUNTIME_MACHINE_HADNLER h, const char *name);
ARCS_ABI int triggBegin(RUNTIME_MACHINE_HADNLER h, double distance,
                        double delay);
ARCS_ABI int triggEnd(RUNTIME_MACHINE_HADNLER h);
ARCS_ABI int triggInterrupt(RUNTIME_MACHINE_HADNLER h, double distance,
                            double delay);
ARCS_ABI int getTriggInterrupts(RUNTIME_MACHINE_HADNLER h, int *result);

#ifdef __cplusplus
}
#endif

#endif
