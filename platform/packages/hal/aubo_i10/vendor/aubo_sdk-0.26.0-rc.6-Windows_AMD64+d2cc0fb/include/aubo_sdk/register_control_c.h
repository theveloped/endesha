#ifndef AUBO_SDK_RegisterControl_C_H
#define AUBO_SDK_RegisterControl_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI BOOL getBoolInput(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setBoolInput(REGISTER_CONTROL_HANDLER h, uint32_t address,
                          BOOL value);
ARCS_ABI int getInt32Input(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setInt32Input(REGISTER_CONTROL_HANDLER h, uint32_t address,
                           int value);
ARCS_ABI float getFloatInput(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setFloatInput(REGISTER_CONTROL_HANDLER h, uint32_t address,
                           float value);
ARCS_ABI double getDoubleInput(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setDoubleInput(REGISTER_CONTROL_HANDLER h, uint32_t address,
                            double value);
ARCS_ABI BOOL getBoolOutput(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setBoolOutput(REGISTER_CONTROL_HANDLER h, uint32_t address,
                           BOOL value);
ARCS_ABI int getInt32Output(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setInt32Output(REGISTER_CONTROL_HANDLER h, uint32_t address,
                            int value);
ARCS_ABI float getFloatOutput(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setFloatOutput(REGISTER_CONTROL_HANDLER h, uint32_t address,
                            float value);
ARCS_ABI double getDoubleOutput(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setDoubleOutput(REGISTER_CONTROL_HANDLER h, uint32_t address,
                             double value);
ARCS_ABI int16_t getInt16Register(REGISTER_CONTROL_HANDLER h, uint32_t address);
ARCS_ABI int setInt16Register(REGISTER_CONTROL_HANDLER h, uint32_t address,
                              int16_t value);
ARCS_ABI BOOL variableUpdated(REGISTER_CONTROL_HANDLER h, const char *key,
                              uint64_t since);
ARCS_ABI BOOL hasNamedVariable(REGISTER_CONTROL_HANDLER h, const char *key);
ARCS_ABI int getNamedVariableType(REGISTER_CONTROL_HANDLER h, const char *key,
                                  char *result);
ARCS_ABI BOOL getBool(REGISTER_CONTROL_HANDLER h, const char *key,
                      BOOL default_value);
ARCS_ABI int setBool(REGISTER_CONTROL_HANDLER h, const char *key, BOOL value);
ARCS_ABI int getVecChar(REGISTER_CONTROL_HANDLER h, const char *key,
                        const char *default_value, char *result, int sz);
ARCS_ABI int setVecChar(REGISTER_CONTROL_HANDLER h, const char *key,
                        const char *value, int sz);
ARCS_ABI int getInt32(REGISTER_CONTROL_HANDLER h, const char *key,
                      int default_value);
ARCS_ABI int setInt32(REGISTER_CONTROL_HANDLER h, const char *key, int value);
ARCS_ABI int getVecInt32(REGISTER_CONTROL_HANDLER h, const char *key,
                         int32_t *default_value, int *result);
ARCS_ABI int setVecInt32(REGISTER_CONTROL_HANDLER h, const char *key,
                         int32_t *value);
ARCS_ABI float getFloat(REGISTER_CONTROL_HANDLER h, const char *key,
                        float default_value);
ARCS_ABI int setFloat(REGISTER_CONTROL_HANDLER h, const char *key, float value);
ARCS_ABI int getVecFloat(REGISTER_CONTROL_HANDLER h, const char *key,
                         const float *default_value, float *result);
ARCS_ABI int setVecFloat(REGISTER_CONTROL_HANDLER h, const char *key,
                         const float *value);
ARCS_ABI double getDouble(REGISTER_CONTROL_HANDLER h, const char *key,
                          double default_value);
ARCS_ABI int setDouble(REGISTER_CONTROL_HANDLER h, const char *key,
                       double value);
ARCS_ABI int getVecDouble(REGISTER_CONTROL_HANDLER h, const char *key,
                          const double *default_value, double *result);
ARCS_ABI int setVecDouble(REGISTER_CONTROL_HANDLER h, const char *key,
                          const double *value);
ARCS_ABI int getString(REGISTER_CONTROL_HANDLER h, const char *key,
                       const char *default_value, char *result);
ARCS_ABI int setString(REGISTER_CONTROL_HANDLER h, const char *key,
                       const char *value);
ARCS_ABI int clearNamedVariable(REGISTER_CONTROL_HANDLER h, const char *key);
ARCS_ABI int setWatchDog(REGISTER_CONTROL_HANDLER h, const char *key,
                         double timeout, int action);
ARCS_ABI int getWatchDogAction(REGISTER_CONTROL_HANDLER h, const char *key);
ARCS_ABI int getWatchDogTimeout(REGISTER_CONTROL_HANDLER h, const char *key);
ARCS_ABI int modbusAddSignal(REGISTER_CONTROL_HANDLER h,
                             const char *device_info, int slave_number,
                             int signal_address, int signal_type,
                             const char *signal_name, BOOL sequential_mode);
ARCS_ABI int modbusDeleteSignal(REGISTER_CONTROL_HANDLER h,
                                const char *signal_name);
ARCS_ABI int modbusDeleteAllSignals(REGISTER_CONTROL_HANDLER h);
ARCS_ABI int modbusGetSignalStatus(REGISTER_CONTROL_HANDLER h,
                                   const char *signal_name);
ARCS_ABI int modbusGetSignalNames(REGISTER_CONTROL_HANDLER h, char **result);
ARCS_ABI int modbusGetSignalTypes(REGISTER_CONTROL_HANDLER h, int *result);
ARCS_ABI int modbusGetSignalValues(REGISTER_CONTROL_HANDLER h, int *result);
ARCS_ABI int modbusGetSignalErrors(REGISTER_CONTROL_HANDLER h, int *result);
ARCS_ABI int modbusSendCustomCommand(REGISTER_CONTROL_HANDLER h, const char *IP,
                                     int slave_number, int function_code,
                                     uint8_t *data, int sz);
ARCS_ABI int modbusSetDigitalInputAction(REGISTER_CONTROL_HANDLER h,
                                         const char *robot_name,
                                         const char *signal_name,
                                         StandardInputAction_C action);
ARCS_ABI int modbusSetOutputRunstate(REGISTER_CONTROL_HANDLER h,
                                     const char *robot_name,
                                     const char *signal_name,
                                     StandardOutputRunState_C runstate);
ARCS_ABI int modbusSetOutputSignal(REGISTER_CONTROL_HANDLER h,
                                   const char *signal_name, uint16_t value);
ARCS_ABI int modbusSetOutputSignalPulse(REGISTER_CONTROL_HANDLER h,
                                        const char *signal_name, uint16_t value,
                                        double duration);
ARCS_ABI int modbusSetSignalUpdateFrequency(REGISTER_CONTROL_HANDLER h,
                                            const char *signal_name,
                                            int update_frequency);
ARCS_ABI int modbusGetSignalIndex(REGISTER_CONTROL_HANDLER h,
                                  const char *signal_name);
ARCS_ABI int modbusGetSignalError(REGISTER_CONTROL_HANDLER h,
                                  const char *signal_name);
ARCS_ABI int getModbusDeviceStatus(REGISTER_CONTROL_HANDLER h,
                                   const char *device_name);
#ifdef __cplusplus
}
#endif

#endif
