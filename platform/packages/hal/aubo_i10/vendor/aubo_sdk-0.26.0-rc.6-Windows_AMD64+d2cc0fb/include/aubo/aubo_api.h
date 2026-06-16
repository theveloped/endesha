/** @file aubo_api.h
 *  @brief \~chinese 机器人及外部轴等控制API接口，如获取机器人列表、获取系统信息等等
 *  @brief \~english API for controlling the robot and external axis
 */
#ifndef AUBO_SDK_AUBO_API_INTERFACE_H
#define AUBO_SDK_AUBO_API_INTERFACE_H

#include <aubo/system_info.h>
#include <aubo/runtime_machine.h>
#include <aubo/register_control.h>
#include <aubo/robot_interface.h>
#include <aubo/global_config.h>
#include <aubo/math.h>
#include <aubo/socket.h>
#include <aubo/serial.h>
#include <aubo/axis_interface.h>
#include <aubo/gripper_interface.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup AuboApi AuboApi (主入口)
 * @ingroup AuboApi
 *  AuboApi
 */
class ARCS_ABI_EXPORT AuboApi
{
public:
    AuboApi();
    virtual ~AuboApi();

    /**
     * @ingroup AuboApi
     * @ref Math
     * \chinese
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
     * \endchinese
     *
     *\english
     * Get pure mathematic related API
     *
     * @return Shared pointer to a Math object
     *
     * @par Python function prototype
     * getMath(self: pyaubo_sdk.AuboApi) -> pyaubo_sdk.Math
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * MathPtr ptr = rpc_cli->getMath();
     * @endcode
     *\endenglish
     */
    MathPtr getMath();

    /**
     * @ingroup AuboApi
     * @ref SystemInfo
     * \chinese
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
     * \endchinese
     *
     * \english
     * Get system info
     *
     * @return Shared pointer to SystemInfo object
     *
     * @par Python function prototype
     * getSystemInfo(self: pyaubo_sdk.AuboApi) -> pyaubo_sdk.SystemInfo
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * SystemInfoPtr ptr = rpc_cli->getSystemInfo();
     * @endcode
     * \endenglish
     */
    SystemInfoPtr getSystemInfo();

    /**
     * @ingroup AuboApi
     * @ref RuntimeMachine
     * \chinese
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
     * \endchinese
     *
     * \english
     * Get runtime api
     *
     * @return Shared pointer to RuntimeMachine object
     * Python function prototype
     * getRuntimeMachine(self: pyaubo_sdk.AuboApi) -> pyaubo_sdk.RuntimeMachine
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * RuntimeMachinePtr ptr = rpc_cli->getRuntimeMachine();
     * @endcode
     * \endenglish
     */
    RuntimeMachinePtr getRuntimeMachine();

    /**
     * @ingroup AuboApi
     * @ref RegisterControl
     * \chinese
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
     * \endchinese
     *
     * \english
     * External registers api
     *
     * @return Shared pointer to RegisterControl object
     *
     * @par Python function prototype
     * getRegisterControl(self: pyaubo_sdk.AuboApi) ->
     * pyaubo_sdk.RegisterControl
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * RegisterControlPtr ptr = rpc_cli->getRegisterControl();
     * @endcode
     * \endenglish
     */
    RegisterControlPtr getRegisterControl();

    /**
     * @ingroup AuboApi
     * \chinese
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
     * \endchinese
     *
     * \english
     * Get robot list
     *
     * @return robot list
     *
     * @par Python function prototype
     * getRobotNames(self: pyaubo_sdk.AuboApi) -> List[str]
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * @endcode
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"getRobotNames","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":["rob1"]}
     * \endenglish
     */
    std::vector<std::string> getRobotNames();

    /**
     * @ingroup AuboApi
     * @ref RobotInterface
     * \chinese
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
     * \endchinese
     *
     * \english
     * Get RobotInterfacePtr based on name
     *
     * @param name Robot name
     * @return Shared pointer to a RobotInterface object
     *
     * @par Python function prototype
     * getRobotInterface(self: pyaubo_sdk.AuboApi, arg0: str) ->
     * pyaubo_sdk.RobotInterface
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotInterfacePtr ptr = rpc_cli->getRobotInterface(robot_name);
     * @endcode
     * \endenglish
     */
    RobotInterfacePtr getRobotInterface(const std::string &name);

    /**
     * @ingroup AuboApi
     * \~chinese 获取外部轴列表 \~english Get external axis list
     *
     * @return
     */
    std::vector<std::string> getAxisNames();

    /**
     * @ingroup AuboApi
     * @ref AxisInterface
     * \chinese 
     * 获取外部轴接口 
     *
     * @param name
     * @return
     * \endchinese
     *
     * \english 
     * Get external axis interface
     * 
     * @param name
     * @return
     * \endenglish
     */
    AxisInterfacePtr getAxisInterface(const std::string &name);

    /**
     * @ingroup AuboApi
     * @ref Socket
     * \chinese
     * 获取 socket
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
     * \endchinese
     *
     * \english
     * Get socket
     * @return Shared pointer to a socket object
     *
     * @par Python function prototype
     * getSocket(self: pyaubo_sdk.AuboApi) -> arcs::common_interface::Socket
     * @endcode
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * SocketPtr ptr = rpc_cli->getSocket();
     * @endcode
     * \endenglish
     */
    SocketPtr getSocket();

    /**
     * @ingroup AuboApi
     * @ref Serial
     * \chinese
     * 获取Serial串口
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
     * \endchinese
     * 
     * \english
     * @return Shared pointer to Serial object
     *
     * @par Python function prototype
     * getSerial(self: pyaubo_sdk.AuboApi) -> arcs::common_interface::Serial
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * SerialPtr ptr = rpc_cli->getSerial();
     * @endcode
     * \endenglish
     */
    SerialPtr getSerial();

    /**
     * @ingroup AuboApi
     * @ref SyncMove
     * \~chinese 获取同步运动接口 \~english Get syncronous move interface
     *
     * \~chinese @return SyncMovePtr对象的指针 
     * \~english @return Shared pointer to SyncMove object
     */
    SyncMovePtr getSyncMove(const std::string &name);

    /**
     * @ingroup AuboApi
     * @ref Trace
     * \~chinese 获取告警信息接口
     * \~english Get alert interface
     *
     * \~chinese @return TracePtr对象的指针
     * \~english @return Shared pointer of trace object
     */
    TracePtr getTrace(const std::string &name);

    /**
     * @ingroup AuboApi
     * @ref GripperInterface
     * \~chinese 获取通用夹爪接口
     * \~english Get gripper interface
     *
     * \~chinese @return GripperInterfacePtr对象的指针
     * \~english @return Shared pointer of gripper object
     */
    GripperInterfacePtr getGripperInterface();

protected:
    void *d_{ nullptr };
};
using AuboApiPtr = std::shared_ptr<AuboApi>;

} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_AUBO_API_H
