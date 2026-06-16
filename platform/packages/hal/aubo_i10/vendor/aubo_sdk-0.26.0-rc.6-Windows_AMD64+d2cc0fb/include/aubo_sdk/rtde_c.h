#ifndef AUBO_SDK_RTDE_C_H
#define AUBO_SDK_RTDE_C_H

#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief 创建 RTDE 客户端实例。
 *
 * @param mode 设置通讯方式，0 表示 TCP 通讯，1 表示 UDS 通讯。
 * @return 成功返回 RTDE 客户端句柄，失败返回 NULL。
 */
ARCS_ABI RTDE_HANDLE rtde_create_client(int mode);

/**
 * @brief 销毁 RTDE 客户端实例。
 *
 * @param cli RTDE 客户端句柄。
 */
ARCS_ABI void rtde_destroy_client(RTDE_HANDLE cli);

/**
 * @brief 设置日志处理器。
 *
 * @param cli RTDE 客户端句柄。
 * @param handler 日志处理函数。
 */
ARCS_ABI void rtde_setLogHandler(RTDE_HANDLE cli,
                                 void (*handler)(int level,
                                                 const char *filename, int line,
                                                 const char *message));

/**
 * @brief 连接到服务器。
 *
 * @param cli RTDE 客户端句柄。
 * @param ip IP 地址，NULL 表示使用默认地址。
 * @param port 端口号，0 表示使用默认端口。
 * @return 0 表示成功，-1 表示失败。
 */
ARCS_ABI int rtde_connect(RTDE_HANDLE cli, const char *ip, int port);

/**
 * @brief 检查是否已连接。
 *
 * @param cli RTDE 客户端句柄。
 * @return true 表示已连接，false 表示未连接。
 */
ARCS_ABI bool rtde_hasConnected(RTDE_HANDLE cli);

/**
 * @brief 登录到服务器。
 *
 * @param cli RTDE 客户端句柄。
 * @param username 用户名。
 * @param password 密码。
 * @return 0 表示成功，-1 表示失败。
 */
ARCS_ABI int rtde_login(RTDE_HANDLE cli, const char *username,
                        const char *password);

/**
 * @brief 检查是否已登录。
 *
 * @param cli RTDE 客户端句柄。
 * @return true 表示已登录，false 表示未登录。
 */
ARCS_ABI bool rtde_hasLogined(RTDE_HANDLE cli);

/**
 * @brief 登出。
 *
 * @param cli RTDE 客户端句柄。
 * @return 0 表示成功。
 */
ARCS_ABI int rtde_logout(RTDE_HANDLE cli);

/**
 * @brief 断开连接。
 *
 * @param cli RTDE 客户端句柄。
 * @return 0 表示成功，-1 表示失败。
 */
ARCS_ABI int rtde_disconnect(RTDE_HANDLE cli);

/**
 * @brief 获取协议版本号。
 *
 * @param cli RTDE 客户端句柄。
 * @return 协议版本号。
 */
ARCS_ABI int rtde_getProtocolVersion(RTDE_HANDLE cli);

/**
 * @brief 设置话题。
 *
 * @param cli RTDE 客户端句柄。
 * @param to_server 数据流向，true 表示客户端发送消息，false
 * 表示服务器发送消息。
 * @param names 信息列表（逗号分隔的字符串）。
 * @param freq 推送频率。
 * @param expected_chanel 通道号。
 * @return 成功返回通道号，失败返回 -1。
 */
ARCS_ABI int rtde_setTopic(RTDE_HANDLE cli, bool to_server, const char *names,
                           double freq, int expected_chanel);

/**
 * @brief 取消订阅。
 *
 * @param cli RTDE 客户端句柄。
 * @param to_server 数据流向。
 * @param chanel 通道号。
 * @return 0 表示成功，-1 表示失败。
 */
ARCS_ABI int rtde_removeTopic(RTDE_HANDLE cli, bool to_server, int chanel);

/**
 * @brief 订阅主题。
 *
 * @param cli RTDE 客户端句柄。
 * @param chanel 通道号。
 * @param callback 回调函数，用于处理订阅的数据。
 * @return 0 表示成功，-1 表示失败。
 */
ARCS_ABI int rtde_subscribe(RTDE_HANDLE cli, int chanel,
                            void (*callback)(void *parser));

/**
 * @brief 发布数据。
 *
 * @param cli RTDE 客户端句柄。
 * @param chanel 通道号。
 * @param callback 回调函数，用于生成发布数据。
 * @return 0 表示成功，-1 表示失败。
 */
ARCS_ABI int rtde_publish(RTDE_HANDLE cli, int chanel,
                          void (*callback)(void *builder));

// OutputBuilder
ARCS_ABI int rtde_pushInt(OUTPUT_BUILDER_HANDLE builder, int val);
ARCS_ABI int rtde_pushDouble(OUTPUT_BUILDER_HANDLE builder, double val);
ARCS_ABI int rtde_pushVectorDouble(OUTPUT_BUILDER_HANDLE builder, const double* val, int size);
ARCS_ABI int rtde_pushTupleIntBool(OUTPUT_BUILDER_HANDLE builder, int first, bool second);
ARCS_ABI int rtde_pushInt16(OUTPUT_BUILDER_HANDLE builder, int16_t val);
ARCS_ABI int rtde_pushVectorInt16(OUTPUT_BUILDER_HANDLE builder, const int16_t* val, int size);
ARCS_ABI int rtde_pushVectorInt(OUTPUT_BUILDER_HANDLE builder, const int* val, int size);
ARCS_ABI int rtde_pushString(OUTPUT_BUILDER_HANDLE builder, const char* val);
ARCS_ABI int rtde_pushChar(OUTPUT_BUILDER_HANDLE builder, char val);
ARCS_ABI int rtde_pushRtdeRecipe(OUTPUT_BUILDER_HANDLE builder, const struct RtdeRecipe_C* val);

// InputParser
ARCS_ABI bool rtde_popBool(INPUT_PARSER_HANDLE parser);
ARCS_ABI int32_t rtde_popInt32(INPUT_PARSER_HANDLE parser);
ARCS_ABI int64_t rtde_popInt64(INPUT_PARSER_HANDLE parser);
ARCS_ABI int16_t rtde_popInt16(INPUT_PARSER_HANDLE parser);
ARCS_ABI double rtde_popDouble(INPUT_PARSER_HANDLE parser);
ARCS_ABI char rtde_popChar(INPUT_PARSER_HANDLE parser);

ARCS_ABI int rtde_popVectorInt(INPUT_PARSER_HANDLE* parser, int* data, int size);
ARCS_ABI int rtde_popVectorInt16(INPUT_PARSER_HANDLE parser, int16_t* data, int size);
ARCS_ABI int rtde_popVectorDouble(INPUT_PARSER_HANDLE parser, double* data, int size);
ARCS_ABI int rtde_popVectorVectorDouble(INPUT_PARSER_HANDLE parser, double*** data, int rows, int cols);

ARCS_ABI JointStateType_C rtde_popVectorJointStateType(INPUT_PARSER_HANDLE parser);
ARCS_ABI RobotModeType_C rtde_popRobotModeType(INPUT_PARSER_HANDLE parser);
ARCS_ABI OperationalModeType_C rtde_popOperationalModeType(INPUT_PARSER_HANDLE parser);
ARCS_ABI SafetyModeType_C rtde_popSafetyModeType(INPUT_PARSER_HANDLE parser);
ARCS_ABI RuntimeState_C rtde_popRuntimeState(INPUT_PARSER_HANDLE parser);
ARCS_ABI int rtde_popRobotMsgVector(INPUT_PARSER_HANDLE parser, struct RobotMsgVector_C* robot_msg_vec);
ARCS_ABI int rtde_popPayload(INPUT_PARSER_HANDLE parser, struct Payload_C* payload);

#ifdef __cplusplus
}
#endif

#endif // AUBO_SDK_RTDE_C_H
