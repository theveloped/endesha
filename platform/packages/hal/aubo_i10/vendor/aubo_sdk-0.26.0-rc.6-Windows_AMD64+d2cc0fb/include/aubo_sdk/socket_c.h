#ifndef AUBO_SDK_Socket_C_H
#define AUBO_SDK_Socket_C_H
#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int socketOpen(SOCKET_HANDLER h, const char *address, int port,
                        const char *socket_name);
ARCS_ABI int socketClose(SOCKET_HANDLER h, const char *socket_name);
ARCS_ABI int socketReadAsciiFloat(SOCKET_HANDLER h, int number,
                                  const char *variable,
                                  const char *socket_name);
ARCS_ABI int socketReadBinaryInteger(SOCKET_HANDLER h, int number,
                                     const char *variable,
                                     const char *socket_name);
ARCS_ABI int socketReadByteList(SOCKET_HANDLER h, int number,
                                const char *variable, const char *socket_name);
ARCS_ABI int socketReadString(SOCKET_HANDLER h, const char *variable,
                              const char *socket_name, const char *prefix,
                              const char *suffix, BOOL interpret_escape);
ARCS_ABI int socketReadAllString(SOCKET_HANDLER h, const char *variable,
                                 const char *socket_name);
ARCS_ABI int socketSendByte(SOCKET_HANDLER h, char value,
                            const char *socket_name);
ARCS_ABI int socketSendInt(SOCKET_HANDLER h, int value,
                           const char *socket_name);
ARCS_ABI int socketSendLine(SOCKET_HANDLER h, const char *str,
                            const char *socket_name);
ARCS_ABI int socketSendString(SOCKET_HANDLER h, const char *str,
                              const char *socket_name);
ARCS_ABI int socketSendAllString(SOCKET_HANDLER h, BOOL is_check,
                                 const char *str, const char *socket_name);
#ifdef __cplusplus
}
#endif

#endif
