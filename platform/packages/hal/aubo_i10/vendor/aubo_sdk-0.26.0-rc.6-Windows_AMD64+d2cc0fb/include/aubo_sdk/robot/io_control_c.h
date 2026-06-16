#ifndef AUBO_SDK_IoControl_C_H
#define AUBO_SDK_IoControl_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int getStandardDigitalInputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getToolDigitalInputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getConfigurableDigitalInputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getStandardDigitalOutputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getToolDigitalOutputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int setToolIoInput(IO_CONTROL_HANDLER h, int index, BOOL input);
ARCS_ABI BOOL isToolIoInput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int getConfigurableDigitalOutputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getStandardAnalogInputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getToolAnalogInputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getStandardAnalogOutputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getToolAnalogOutputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int setDigitalInputActionDefault(IO_CONTROL_HANDLER h);
ARCS_ABI int setStandardDigitalInputAction(IO_CONTROL_HANDLER h, int index,
                                           StandardInputAction_C action);
ARCS_ABI int setToolDigitalInputAction(IO_CONTROL_HANDLER h, int index,
                                       StandardInputAction_C action);
ARCS_ABI int setConfigurableDigitalInputAction(IO_CONTROL_HANDLER h, int index,
                                               StandardInputAction_C action);
ARCS_ABI StandardInputAction_C
getStandardDigitalInputAction(IO_CONTROL_HANDLER h, int index);
ARCS_ABI StandardInputAction_C getToolDigitalInputAction(IO_CONTROL_HANDLER h,
                                                         int index);
ARCS_ABI StandardInputAction_C
getConfigurableDigitalInputAction(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int setDigitalOutputRunstateDefault(IO_CONTROL_HANDLER h);
ARCS_ABI int setStandardDigitalOutputRunstate(
    IO_CONTROL_HANDLER h, int index, StandardOutputRunState_C runstate);
ARCS_ABI int setToolDigitalOutputRunstate(IO_CONTROL_HANDLER h, int index,
                                          StandardOutputRunState_C runstate);
ARCS_ABI int setConfigurableDigitalOutputRunstate(
    IO_CONTROL_HANDLER h, int index, StandardOutputRunState_C runstate);
ARCS_ABI StandardOutputRunState_C
getStandardDigitalOutputRunstate(IO_CONTROL_HANDLER h, int index);
ARCS_ABI StandardOutputRunState_C
getToolDigitalOutputRunstate(IO_CONTROL_HANDLER h, int index);
ARCS_ABI StandardOutputRunState_C
getConfigurableDigitalOutputRunstate(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int setStandardAnalogOutputRunstate(IO_CONTROL_HANDLER h, int index,
                                             StandardOutputRunState_C runstate);
ARCS_ABI int setToolAnalogOutputRunstate(IO_CONTROL_HANDLER h, int index,
                                         StandardOutputRunState_C runstate);
ARCS_ABI StandardOutputRunState_C
getStandardAnalogOutputRunstate(IO_CONTROL_HANDLER h, int index);
ARCS_ABI StandardOutputRunState_C
getToolAnalogOutputRunstate(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int setStandardAnalogInputDomain(IO_CONTROL_HANDLER h, int index,
                                          int domain);
ARCS_ABI int setToolAnalogInputDomain(IO_CONTROL_HANDLER h, int index,
                                      int domain);
ARCS_ABI int getStandardAnalogInputDomain(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int getToolAnalogInputDomain(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int setStandardAnalogOutputDomain(IO_CONTROL_HANDLER h, int index,
                                           int domain);
ARCS_ABI int setToolAnalogOutputDomain(IO_CONTROL_HANDLER h, int index,
                                       int domain);
ARCS_ABI int setToolVoltageOutputDomain(IO_CONTROL_HANDLER h, int domain);
ARCS_ABI int getToolVoltageOutputDomain(IO_CONTROL_HANDLER h);
ARCS_ABI int getStandardAnalogOutputDomain(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int getToolAnalogOutputDomain(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int setStandardDigitalOutput(IO_CONTROL_HANDLER h, int index,
                                      BOOL value);
ARCS_ABI int setStandardDigitalOutputPulse(IO_CONTROL_HANDLER h, int index,
                                           BOOL value, double duration);
ARCS_ABI int setToolDigitalOutput(IO_CONTROL_HANDLER h, int index, BOOL value);
ARCS_ABI int setToolDigitalOutputPulse(IO_CONTROL_HANDLER h, int index,
                                       BOOL value, double duration);
ARCS_ABI int setConfigurableDigitalOutput(IO_CONTROL_HANDLER h, int index,
                                          BOOL value);
ARCS_ABI int setConfigurableDigitalOutputPulse(IO_CONTROL_HANDLER h, int index,
                                               BOOL value, double duration);
ARCS_ABI int setStandardAnalogOutput(IO_CONTROL_HANDLER h, int index,
                                     double value);
ARCS_ABI int setToolAnalogOutput(IO_CONTROL_HANDLER h, int index, double value);
ARCS_ABI BOOL getStandardDigitalInput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI uint32_t getStandardDigitalInputs(IO_CONTROL_HANDLER h);
ARCS_ABI BOOL getToolDigitalInput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI uint32_t getToolDigitalInputs(IO_CONTROL_HANDLER h);
ARCS_ABI BOOL getConfigurableDigitalInput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI uint32_t getConfigurableDigitalInputs(IO_CONTROL_HANDLER h);
ARCS_ABI double getStandardAnalogInput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI double getToolAnalogInput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI BOOL getStandardDigitalOutput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI uint32_t getStandardDigitalOutputs(IO_CONTROL_HANDLER h);
ARCS_ABI BOOL getToolDigitalOutput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI uint32_t getToolDigitalOutputs(IO_CONTROL_HANDLER h);
ARCS_ABI BOOL getConfigurableDigitalOutput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI uint32_t getConfigurableDigitalOutputs(IO_CONTROL_HANDLER h);
ARCS_ABI double getStandardAnalogOutput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI double getToolAnalogOutput(IO_CONTROL_HANDLER h, int index);
ARCS_ABI int getStaticLinkInputNum(IO_CONTROL_HANDLER h);
ARCS_ABI int getStaticLinkOutputNum(IO_CONTROL_HANDLER h);
ARCS_ABI uint32_t getStaticLinkInputs(IO_CONTROL_HANDLER h);
ARCS_ABI uint32_t getStaticLinkOutputs(IO_CONTROL_HANDLER h);
ARCS_ABI BOOL hasEncoderSensor(IO_CONTROL_HANDLER h);
ARCS_ABI int setEncDecoderType(IO_CONTROL_HANDLER h, int type, int range_id);
ARCS_ABI int setEncTickCount(IO_CONTROL_HANDLER h, int tick);
ARCS_ABI int getEncDecoderType(IO_CONTROL_HANDLER h);
ARCS_ABI int getEncTickCount(IO_CONTROL_HANDLER h);
ARCS_ABI int unwindEncDeltaTickCount(IO_CONTROL_HANDLER h, int delta_count);
ARCS_ABI BOOL getToolButtonStatus(IO_CONTROL_HANDLER h);
#ifdef __cplusplus
}
#endif

#endif
