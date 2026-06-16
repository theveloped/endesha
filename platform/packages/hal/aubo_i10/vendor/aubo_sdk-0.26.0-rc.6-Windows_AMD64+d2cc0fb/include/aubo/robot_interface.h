/** @file  robot_interface.h
 *  @brief 机器人API 接口
 */
#ifndef AUBO_SDK_ROBOT_INTERFACE_H
#define AUBO_SDK_ROBOT_INTERFACE_H

#include <aubo/sync_move.h>
#include <aubo/trace.h>
#include <aubo/robot/motion_control.h>
#include <aubo/robot/force_control.h>
#include <aubo/robot/io_control.h>
#include <aubo/robot/robot_algorithm.h>
#include <aubo/robot/robot_state.h>
#include <aubo/robot/robot_manage.h>
#include <aubo/robot/robot_config.h>
#include <aubo/global_config.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup RobotInterface RobotInterface(机器人模块)
 * \~chinese 机器人模块 \~english RobotInterface
 */
class ARCS_ABI_EXPORT RobotInterface
{
public:
    RobotInterface();
    virtual ~RobotInterface();
    
    /**
     * @ingroup RobotInterface
     * @ref RobotConfig
     * \chinese
     * 获取RobotConfig接口
     *
     * @return RobotConfigPtr对象的指针
     *
     * @par Python函数原型
     * getRobotConfig(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotConfig
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotConfigPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotConfig();
     * @endcode
     * \endchinese
     * \english
     * Get RobotConfig interface
     *
     * @return Pointer to RobotConfig object
     *
     * @par Python function prototype
     * getRobotConfig(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotConfig
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotConfigPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotConfig();
     * @endcode
     * \endenglish
     */

    RobotConfigPtr getRobotConfig();

    /**
     * @ingroup RobotInterface
     * @ref MotionControl
     * \chinese
     * 获取运动规划接口
     *
     * @return MotionControlPtr对象的指针
     *
     * @par Python函数原型
     * getMotionControl(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::MotionControl
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * MotionControlPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getMotionControl();
     * @endcode
     * \endchinese
     * \english
     * Get motion planning interface
     *
     * @return Pointer to MotionControl object
     *
     * @par Python function prototype
     * getMotionControl(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::MotionControl
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * MotionControlPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getMotionControl();
     * @endcode
     * \endenglish
     */
    MotionControlPtr getMotionControl();

    /**
     * @ingroup RobotInterface
     * @ref ForceControl
     * \chinese
     * 获取力控接口
     *
     * @return ForceControlPtr对象的指针
     *
     * @par Python函数原型
     * getForceControl(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::ForceControl
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * ForceControlPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getForceControl();
     * @endcode
     * \endchinese
     * \english
     * Get force control interface
     *
     * @return Pointer to ForceControl object
     *
     * @par Python function prototype
     * getForceControl(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::ForceControl
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * ForceControlPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getForceControl();
     * @endcode
     * \endenglish
     */
    ForceControlPtr getForceControl();

    /**
     * @ingroup RobotInterface
     * @ref IoControl
     * \chinese
     * 获取IO控制的接口
     *
     * @return IoControlPtr对象的指针
     *
     * @par Python函数原型
     * getIoControl(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::IoControl
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * IoControlPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getIoControl();
     * @endcode
     * \endchinese
     * \english
     * Get IO control interface
     *
     * @return Pointer to IoControl object
     *
     * @par Python function prototype
     * getIoControl(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::IoControl
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * IoControlPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getIoControl();
     * @endcode
     * \endenglish
     */
    IoControlPtr getIoControl();

    /**
     * @ingroup RobotInterface
     * @ref SyncMove
     * \chinese
     * 获取同步运动接口
     *
     * @return SyncMovePtr对象的指针
     *
     * @par Python函数原型
     * getSyncMove(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::SyncMove
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * SyncMovePtr ptr = rpc_cli->getRobotInterface(robot_name)->getSyncMove();
     * @endcode
     * \endchinese
     * \english
     * Get synchronized motion interface
     *
     * @return Pointer to SyncMove object
     *
     * @par Python function prototype
     * getSyncMove(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::SyncMove
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * SyncMovePtr ptr = rpc_cli->getRobotInterface(robot_name)->getSyncMove();
     * @endcode
     * \endenglish
     */
    SyncMovePtr getSyncMove();

    /**
     * @ingroup RobotInterface
     * @ref RobotAlgorithm
     * \chinese
     * 获取机器人实用算法接口
     *
     * @return RobotAlgorithmPtr对象的指针
     *
     * @par Python函数原型
     * getRobotAlgorithm(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotAlgorithm
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotAlgorithmPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotAlgorithm();
     * @endcode
     * \endchinese
     * \english
     * Get robot utility algorithm interface
     *
     * @return Pointer to RobotAlgorithm object
     *
     * @par Python function prototype
     * getRobotAlgorithm(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotAlgorithm
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotAlgorithmPtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotAlgorithm();
     * @endcode
     * \endenglish
     */
    RobotAlgorithmPtr getRobotAlgorithm();

    /**
     * @ingroup RobotInterface
     * @ref RobotManage
     * \chinese
     * 获取机器人管理接口(上电、启动、停止等)
     *
     * @return RobotManagePtr对象的指针
     *
     * @par Python函数原型
     * getRobotManage(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotManage
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotManagePtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotManage();
     * @endcode
     * \endchinese
     * \english
     * Get robot management interface (power on, start, stop, etc.)
     *
     * @return Pointer to RobotManage object
     *
     * @par Python function prototype
     * getRobotManage(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotManage
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotManagePtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotManage();
     * @endcode
     * \endenglish
     */
    RobotManagePtr getRobotManage();

    /**
     * @ingroup RobotInterface
     * @ref RobotState
     * \chinese
     * 获取机器人状态接口
     *
     * @return RobotStatePtr对象的指针
     *
     * @par Python函数原型
     * getRobotState(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotState
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotStatePtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotState();
     * @endcode
     * \endchinese
     * \english
     * Get robot state interface
     *
     * @return Pointer to RobotState object
     *
     * @par Python function prototype
     * getRobotState(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::RobotState
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * RobotStatePtr ptr =
     * rpc_cli->getRobotInterface(robot_name)->getRobotState();
     * @endcode
     * \endenglish
     */
    RobotStatePtr getRobotState();

    /**
     * @ingroup RobotInterface
     * @ref Trace
     * \chinese
     * 获取告警信息接口
     *
     * @return TracePtr对象的指针
     *
     * @par Python函数原型
     * getTrace(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::Trace
     *
     * @par C++示例
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * TracePtr ptr = rpc_cli->getRobotInterface(robot_name)->getTrace();
     * @endcode
     * \endchinese
     * \english
     * Get alarm information interface
     *
     * @return Pointer to Trace object
     *
     * @par Python function prototype
     * getTrace(self: pyaubo_sdk.RobotInterface) ->
     * arcs::common_interface::Trace
     *
     * @par C++ example
     * @code
     * auto rpc_cli = std::make_shared<RpcClient>();
     * auto robot_name = rpc_cli->getRobotNames().front();
     * TracePtr ptr = rpc_cli->getRobotInterface(robot_name)->getTrace();
     * @endcode
     * \endenglish
     */
    TracePtr getTrace();

protected:
    void *d_;
};
using RobotInterfacePtr = std::shared_ptr<RobotInterface>;

} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_ROBOT_INTERFACE_H
