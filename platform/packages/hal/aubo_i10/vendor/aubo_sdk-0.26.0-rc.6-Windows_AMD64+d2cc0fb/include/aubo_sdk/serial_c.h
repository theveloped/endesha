#ifndef AUBO_SDK_Serial_C_H
#define AUBO_SDK_Serial_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int serialOpen(SERIAL_HANDLER h, const char *device, int baud,
                        float stop_bits, int even, const char *serial_name);
ARCS_ABI int serialClose(SERIAL_HANDLER h, const char *serial_name);
ARCS_ABI int serialReadByte(SERIAL_HANDLER h, const char *variable,
                            const char *serial_name);
ARCS_ABI int serialReadByteList(SERIAL_HANDLER h, int number,
                                const char *variable, const char *serial_name);
ARCS_ABI int serialReadString(SERIAL_HANDLER h, const char *variable,
                              const char *serial_name, const char *prefix,
                              const char *suffix, BOOL interpret_escape);
ARCS_ABI int serialSendByte(SERIAL_HANDLER h, char value,
                            const char *serial_name);
ARCS_ABI int serialSendInt(SERIAL_HANDLER h, int value,
                           const char *serial_name);
ARCS_ABI int serialSendLine(SERIAL_HANDLER h, const char *str,
                            const char *serial_name);
ARCS_ABI int serialSendString(SERIAL_HANDLER h, const char *str,
                              const char *serial_name);
ARCS_ABI int serialSendAllString(SERIAL_HANDLER h, BOOL is_check,
                                 const char *str, const char *serial_name);
#ifdef __cplusplus
}
#endif

#endif
