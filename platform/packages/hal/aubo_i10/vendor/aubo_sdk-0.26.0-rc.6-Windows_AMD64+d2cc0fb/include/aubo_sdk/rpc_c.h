/** @file  rpc_c.h
 *  @brief 用于RPC模块的交互，如登录、连接等功能
 */

#ifndef AUBO_SDK_RPC_C_H
#define AUBO_SDK_RPC_C_H

#include <aubo_sdk/type_def_c.h>

#ifdef __cplusplus
extern "C" {
#endif

enum Event
{
    Event_Connected = 0,
    Event_Disconnected = 1,
};

ARCS_ABI RPC_HANDLER rpc_create_client(int mode = 0);
ARCS_ABI void rpc_destroy_client(RPC_HANDLER cli);

/**
 * 设置日志处理器
 *
 * 此函数可设置自定义的日志处理函数来处理日志消息。 \n
 * Aubo SDK 有一套默认的日志系统，按照默认的格式输出到默认的文件。
 * 如果用户不希望采用默认的格式或者不希望输出到默认的文件，那就可以通过这个接口重新自定义格式，或者输出路径。
 * 这个函数可以将用户自定义的日志系统与 Aubo SDK 默认的日志系统合并。
 *
 * @note setLogHandler函数要放在即将触发的日志之前，
 * 否则会按照默认的形式输出日志。
 *
 * @param handler 日志处理函数 \n
 * 此日志处理函数的下定义如下: \n
 * void handler(int level, const char* filename, int line, const
 * std::string& message) \n
 * level 表示日志等级 \n
 * &nbsp; 0: LOGLEVEL_FATAL 严重的错误 \n
 * &nbsp; 1: LOGLEVEL_ERROR      错误 \n
 * &nbsp; 2: LOGLEVEL_WARNING    警告 \n
 * &nbsp; 3: LOGLEVEL_INFO       通知 \n
 * &nbsp; 4: LOGLEVEL_DEBUG      调试 \n
 * &nbsp; 5: LOGLEVEL_BACKTRACE  跟踪 \n
 * filename 表示文件名 \n
 * line 表示代码行号 \n
 * message 表示日志信息 \n
 * @return 无
 */
ARCS_ABI void rpc_setLogHandler(RPC_HANDLER cli, LOG_HANDLER handler);

/**
 * 连接到RPC服务
 *
 * @param ip IP地址
 * @param port 端口号，RPC的端口号是30004
 * @param ip和port为空时，采用unix domain sockets通讯方式
 * @retval 0 RPC连接成功
 * @retval -8 RPC连接失败，RPC连接被拒绝
 * @retval -15 RPC连接失败，SDK版本与Server版本不兼容
 */
ARCS_ABI int rpc_connect(RPC_HANDLER cli, const char *ip = "", int port = 0);

/**
 * 断开RPC连接
 *
 * @retval 0 成功
 * @retval -1 失败
 */
ARCS_ABI int rpc_disconnect(RPC_HANDLER cli);

/**
 * 判断是否连接RPC
 *
 * @retval true 已连接RPC
 * @retval false 未连接RPC
 */
ARCS_ABI bool rpc_hasConnected(RPC_HANDLER cli);

/**
 * 登录
 *
 * @param usrname 用户名
 * @param passwd 密码
 * @return 0
 */
ARCS_ABI int rpc_login(RPC_HANDLER cli, const char *usrname,
                       const char *passwd);

/**
 * 登出
 *
 * @return 0
 */
ARCS_ABI int rpc_logout(RPC_HANDLER cli);

/**
 * 判断是否登录
 *
 * @retval true 已登录
 * @retval false 未登录
 */
ARCS_ABI bool rpc_hasLogined(RPC_HANDLER cli);

/**
 * 设置RPC请求超时时间
 *
 * @param timeout 请求超时时间，单位 ms
 * @return 0
 */
ARCS_ABI int rpc_setRequestTimeout(RPC_HANDLER cli, int timeout = 10);

/**
 * 设置事件处理
 *
 * @param cb
 * @return
 */
ARCS_ABI int rpc_setEventHandler(RPC_HANDLER cli, EVENT_CALLBACK cb);

/**
 * 是否关闭异常抛出
 *
 * @param enable
 * @return
 */
ARCS_ABI int rpc_set_exception_free(RPC_HANDLER cli, bool enable);

/**
 * 返回错误代码
 *
 * @return
 */
ARCS_ABI int rpc_errorCode(RPC_HANDLER cli);

/**
 * 设备关机
 *
 * @return
 */
ARCS_ABI int rpc_shutdown(RPC_HANDLER cli);

/**
 * 获取纯数学相关接口
 *
 * @return MathPtr对象的指针
 *
 * @par Python函数原型
 * getMath(self: pyaubo_sdk.AuboApi) -> pyaubo_sdk.Math
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * MathPtr ptr = rpc_cli->getMath();
 * @endcode
 *
 */
ARCS_ABI MATH_HANDLER rpc_getMath(RPC_HANDLER cli);

/**
 * 获取系统信息
 *
 * @return SystemInfoPtr对象的指针
 *
 * @par Python函数原型
 * getSystemInfo(self: pyaubo_sdk.AuboApi) -> pyaubo_sdk.SystemInfo
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * SystemInfoPtr ptr = rpc_cli->getSystemInfo();
 * @endcode
 *
 */
ARCS_ABI SYSTEM_INFO_HANDLER rpc_getSystemInfo(RPC_HANDLER cli);

/**
 * 获取运行时接口
 *
 * @return RuntimeMachinePtr对象的指针
 *
 * @par Python函数原型
 * getRuntimeMachine(self: pyaubo_sdk.AuboApi) -> pyaubo_sdk.RuntimeMachine
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * RuntimeMachinePtr ptr = rpc_cli->getRuntimeMachine();
 * @endcode
 *
 */
ARCS_ABI RUNTIME_MACHINE_HANDLER rpc_getRuntimeMachine(RPC_HANDLER cli);

/**
 * 对外寄存器接口
 *
 * @return RegisterControlPtr对象的指针
 *
 * @par Python函数原型
 * getRegisterControl(self: pyaubo_sdk.AuboApi) ->
 * pyaubo_sdk.RegisterControl
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * RegisterControlPtr ptr = rpc_cli->getRegisterControl();
 * @endcode
 *
 */
ARCS_ABI REGISTER_CONTROL_HANDLER rpc_getRegisterControl(RPC_HANDLER cli);

/**
 * 获取机器人列表
 *
 * @return 机器人列表
 *
 * @par Python函数原型
 * getRobotNames(self: pyaubo_sdk.AuboApi) -> List[str]
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * auto robot_name = rpc_cli->getRobotNames().front();
 * @endcode
 *
 * @par JSON-RPC请求示例
 * {"jsonrpc":"2.0","method":"getRobotNames","params":[],"id":1}
 *
 * @par JSON-RPC响应示例
 * {"id":1,"jsonrpc":"2.0","result":["rob1"]}
 *
 */
ARCS_ABI int rpc_getRobotNames(RPC_HANDLER cli, char **names);

/**
 * 根据名字获取 RobotInterfacePtr 接口
 *
 * @param name 机器人名字
 * @return RobotInterfacePtr对象的指针
 *
 * @par Python函数原型
 * getRobotInterface(self: pyaubo_sdk.AuboApi, arg0: str) ->
 * pyaubo_sdk.RobotInterface
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * auto robot_name = rpc_cli->getRobotNames().front();
 * RobotInterfacePtr ptr = rpc_cli->getRobotInterface(robot_name);
 * @endcode
 *
 */
ARCS_ABI ROBOT_HANDLER rpc_getRobotInterface(RPC_HANDLER cli, const char *name);

/**
 * 获取外部轴列表
 *
 * @return
 */
ARCS_ABI int rpc_getAxisNames(RPC_HANDLER cli, char **names);

/**
 * 获取外部轴接口
 *
 * @param name
 * @return
 */
ARCS_ABI AXIS_HANDLER rpc_getAxisInterface(RPC_HANDLER cli, const char *name);

/// 获取独立 IO 模块接口

/**
 *  获取 socket
 * @return SocketPtr对象的指针
 *
 * @par Python函数原型
 * getSocket(self: pyaubo_sdk.AuboApi) -> arcs::common_interface::Socket
 * @endcode
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * SocketPtr ptr = rpc_cli->getSocket();
 * @endcode
 *
 */
ARCS_ABI SOCKET_HANDLER rpc_getSocket(RPC_HANDLER cli);

/**
 *
 * @return SerialPtr对象的指针
 *
 * @par Python函数原型
 * getSerial(self: pyaubo_sdk.AuboApi) -> arcs::common_interface::Serial
 *
 * @par C++示例
 * @code
 * auto rpc_cli = std::make_shared<RpcClient>();
 * SerialPtr ptr = rpc_cli->getSerial();
 * @endcode
 */
ARCS_ABI SERIAL_HANDLER rpc_getSerial(RPC_HANDLER cli);

/**
 * 获取同步运动接口
 *
 * @return SyncMovePtr对象的指针
 */
ARCS_ABI SYNC_MOVE_HANDLER rpc_getSyncMove(RPC_HANDLER cli, const char *name);

/**
 * 获取告警信息接口
 *
 * @return TracePtr对象的指针
 */
ARCS_ABI TRACE_HANDLER rpc_getTrace(RPC_HANDLER cli, const char *name);

#ifdef __cplusplus
}
#endif
#endif // #define AUBO_SDK_RPC_C_H
