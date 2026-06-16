/** @file  robot_config.h
 *  @brief 获取机器人配置接口，如获取DH参数、碰撞等级、安装位姿等等
 */
#ifndef AUBO_SDK_ROBOT_CONFIG_H
#define AUBO_SDK_ROBOT_CONFIG_H

#include <vector>
#include <unordered_map>

#include <aubo/global_config.h>
#include <aubo/type_def.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup RobotConfig RobotConfig (机器人配置管理)
 * @ingroup RobotInterface
 *  RobotConfig
 */
class ARCS_ABI_EXPORT RobotConfig
{
public:
    RobotConfig();
    virtual ~RobotConfig();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人的名字
     *
     * @return 返回机器人的名字
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getName(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua函数原型
     * getName() -> string
     *
     * @par Lua示例
     * robot_name = getName()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getName","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"rob1"}
     * \endchinese
     * \english
     * Get the robot's name.
     *
     * @return The robot's name.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getName(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua function prototype
     * getName() -> string
     *
     * @par Lua example
     * robot_name = getName()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getName","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"rob1"}
     * \endenglish
     */
    std::string getName();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人的自由度(从硬件抽象层读取)
     *
     * @return 返回机器人的自由度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDof(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua函数原型
     * getDof() -> number
     *
     * @par Lua示例
     * robot_dof = getDof()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDof","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":6}
     * \endchinese
     * \english
     * Get the robot's degrees of freedom (from the hardware abstraction layer).
     *
     * @return The robot's degrees of freedom.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getDof(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua function prototype
     * getDof() -> number
     *
     * @par Lua example
     * robot_dof = getDof()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDof","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":6}
     * \endenglish
     */
    int getDof();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人的伺服控制周期(从硬件抽象层读取)
     *
     * @return 机器人的伺服控制周期
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getCycletime(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua函数原型
     * getCycletime() -> number
     *
     * @par Lua示例
     * robot_Cycletime = getCycletime()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getCycletime","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.005}
     * \endchinese
     * \english
     * Get the robot's servo control cycle time (from the hardware abstraction
     * layer).
     *
     * @return The robot's servo control cycle time.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getCycletime(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua function prototype
     * getCycletime() -> number
     *
     * @par Lua example
     * robot_Cycletime = getCycletime()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getCycletime","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.005}
     * \endenglish
     */
    double getCycletime();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 预设缓速模式下的速度缩减比例
     *
     * @param level 缓速等级 1, 2
     * @param fraction
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setSlowDownFraction","params":[1,0.8],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the speed reduction ratio for the preset slow-down mode.
     *
     * @param level Slow-down level 1, 2
     * @param fraction
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setSlowDownFraction","params":[1,0.8],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setSlowDownFraction(int level, double fraction);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取预设的缓速模式下的速度缩减比例
     *
     * @param level 缓速等级 1, 2
     * @return 返回预设的缓速模式下的速度缩减比例
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSlowDownFraction","params":[1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.5}
     * \endchinese
     * \english
     * Get the speed reduction ratio for the preset slow-down mode.
     *
     * @param level Slow-down level 1, 2
     * @return The speed reduction ratio for the preset slow-down mode.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSlowDownFraction","params":[1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.5}
     * \endenglish
     */
    double getSlowDownFraction(int level);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取默认的工具端加速度，单位m/s^2
     *
     * @return 默认的工具端加速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDefaultToolAcc(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua函数原型
     * getDefaultToolAcc() -> number
     *
     * @par Lua示例
     * DefaultToolAcc = getDefaultToolAcc()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultToolAcc","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endchinese
     * \english
     * Get the default tool acceleration, in m/s^2.
     *
     * @return The default tool acceleration.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getDefaultToolAcc(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua function prototype
     * getDefaultToolAcc() -> number
     *
     * @par Lua example
     * DefaultToolAcc = getDefaultToolAcc()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultToolAcc","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endenglish
     */
    double getDefaultToolAcc();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取默认的工具端速度，单位m/s
     *
     * @return 默认的工具端速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDefaultToolSpeed(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua函数原型
     * getDefaultToolSpeed() -> number
     *
     * @par Lua示例
     * DefaultToolSpeed = getDefaultToolSpeed()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultToolSpeed","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endchinese
     * \english
     * Get the default tool speed, in m/s.
     *
     * @return The default tool speed.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getDefaultToolSpeed(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua function prototype
     * getDefaultToolSpeed() -> number
     *
     * @par Lua example
     * DefaultToolSpeed = getDefaultToolSpeed()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultToolSpeed","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endenglish
     */
    double getDefaultToolSpeed();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取默认的关节加速度，单位rad/s^2
     *
     * @return 默认的关节加速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDefaultJointAcc(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua函数原型
     * getDefaultJointAcc() -> number
     *
     * @par Lua示例
     * DefaultJointAcc = getDefaultJointAcc()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultJointAcc","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endchinese
     * \english
     * Get the default joint acceleration, in rad/s^2.
     *
     * @return The default joint acceleration.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getDefaultJointAcc(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua function prototype
     * getDefaultJointAcc() -> number
     *
     * @par Lua example
     * DefaultJointAcc = getDefaultJointAcc()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultJointAcc","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endenglish
     */
    double getDefaultJointAcc();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取默认的关节速度，单位rad/s
     *
     * @return 默认的关节速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDefaultJointSpeed(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua函数原型
     * getDefaultJointSpeed() -> number
     *
     * @par Lua示例
     * DefaultJointSpeed = getDefaultJointSpeed()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultJointSpeed","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endchinese
     * \english
     * Get the default joint speed, in rad/s.
     *
     * @return The default joint speed.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getDefaultJointSpeed(self: pyaubo_sdk.RobotConfig) -> float
     *
     * @par Lua function prototype
     * getDefaultJointSpeed() -> number
     *
     * @par Lua example
     * DefaultJointSpeed = getDefaultJointSpeed()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getDefaultJointSpeed","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endenglish
     */
    double getDefaultJointSpeed();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人类型代码
     *
     * @return 机器人类型代码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getRobotType(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua函数原型
     * getRobotType() -> string
     *
     * @par Lua示例
     * RobotType = getRobotType()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getRobotType","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"aubo_i5H"}
     * \endchinese
     * \english
     * Get the robot type code.
     *
     * @return The robot type code.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getRobotType(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua function prototype
     * getRobotType() -> string
     *
     * @par Lua example
     * RobotType = getRobotType()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getRobotType","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"aubo_i5H"}
     * \endenglish
     */
    std::string getRobotType();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人子类型代码
     *
     * @return 机器人子类型代码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getRobotSubType(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua函数原型
     * getRobotSubType() -> string
     *
     * @par Lua示例
     * RobotSubType = getRobotSubType()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getRobotSubType","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"B0"}
     * \endchinese
     * \english
     * Get the robot sub-type code.
     *
     * @return The robot sub-type code.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getRobotSubType(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua function prototype
     * getRobotSubType() -> string
     *
     * @par Lua example
     * RobotSubType = getRobotSubType()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getRobotSubType","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"B0"}
     * \endenglish
     */
    std::string getRobotSubType();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取控制柜类型代码
     *
     * @return 控制柜类型代码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getControlBoxType(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua函数原型
     * getControlBoxType() -> string
     *
     * @par Lua示例
     * ControlBoxType = getControlBoxType()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getControlBoxType","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"cb_ISStation"}
     * \endchinese
     * \english
     * Get the control box type code.
     *
     * @return The control box type code.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getControlBoxType(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua function prototype
     * getControlBoxType() -> string
     *
     * @par Lua example
     * ControlBoxType = getControlBoxType()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getControlBoxType","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"cb_ISStation"}
     * \endenglish
     */
    std::string getControlBoxType();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置安装位姿(机器人的基坐标系相对于世界坐标系)  world->base
     *
     * 一般在多机器人系统中使用，默认为 [0,0,0,0,0,0]
     *
     * @param pose 安装位姿
     * @return 成功返回0; 失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setMountingPose(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * setMountingPose(pose: table) -> nil
     *
     * @par Lua示例
     * setMountingPose({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setMountingPose","params":[[0.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the mounting pose (robot base coordinate system relative to world
     * coordinate system) world->base
     *
     * Typically used in multi-robot systems, default is [0,0,0,0,0,0]
     *
     * @param pose Mounting pose
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setMountingPose(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * setMountingPose(pose: table) -> nil
     *
     * @par Lua example
     * setMountingPose({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setMountingPose","params":[[0.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setMountingPose(const std::vector<double> &pose);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取安装位姿(机器人的基坐标系相对于世界坐标系)
     *
     * @return 安装位姿
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getMountingPose(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getMountingPose() -> table
     *
     * @par Lua示例
     * MountingPose = getMountingPose()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getMountingPose","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endchinese
     * \english
     * Get the mounting pose (robot base coordinate system relative to world
     * coordinate system)
     *
     * @return Mounting pose
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getMountingPose(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getMountingPose() -> table
     *
     * @par Lua example
     * MountingPose = getMountingPose()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getMountingPose","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endenglish
     */
    std::vector<double> getMountingPose();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 将机器人绑定到一个坐标系，如果这个坐标系是运动的，那机器人也会跟着运动
     * 应用于地轨或者龙门
     * 这个函数调用的时候 frame 和 ROBOTBASE 的相对关系就固定了
     * \endchinese
     * \english
     * Attach the robot base to a coordinate frame. If this frame moves, the
     * robot will move accordingly. Used for applications like ground rails or
     * gantries. When this function is called, the relationship between the
     * frame and ROBOTBASE is fixed. \endenglish
     */
    int attachRobotBaseTo(const std::string &frame);
    std::string getRobotBaseParent();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置工件数据，编程点位都是基于工件坐标系
     * \endchinese
     * \english
     * Set work object data. All programmed points are based on the work object
     * coordinate system. \endenglish
     */

    int setWorkObjectData(const WObjectData &wobj);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置碰撞灵敏度等级
     * 数值越大越灵敏
     *
     * @param level 碰撞灵敏度等级
     * 0: 关闭碰撞检测功能
     * 1~9: 碰撞灵敏等级
     * @return 成功返回0; 失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setCollisionLevel(self: pyaubo_sdk.RobotConfig, arg0: int) -> int
     *
     * @par Lua函数原型
     * setCollisionLevel(level: number) -> nil
     *
     * @par Lua示例
     * setCollisionLevel(6)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setCollisionLevel","params":[6],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the collision sensitivity level.
     * The higher the value, the more sensitive.
     *
     * @param level Collision sensitivity level
     * 0: Disable collision detection
     * 1~9: Collision sensitivity levels
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setCollisionLevel(self: pyaubo_sdk.RobotConfig, arg0: int) -> int
     *
     * @par Lua function prototype
     * setCollisionLevel(level: number) -> nil
     *
     * @par Lua example
     * setCollisionLevel(6)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setCollisionLevel","params":[6],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setCollisionLevel(int level);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取碰撞灵敏度等级
     *
     * @return 碰撞灵敏度等级
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getCollisionLevel(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua函数原型
     * getCollisionLevel() -> number
     *
     * @par Lua示例
     * CollisionLevel = getCollisionLevel()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getCollisionLevel","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":6}
     * \endchinese
     * \english
     * Get the collision sensitivity level.
     *
     * @return Collision sensitivity level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getCollisionLevel(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua function prototype
     * getCollisionLevel() -> number
     *
     * @par Lua example
     * CollisionLevel = getCollisionLevel()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getCollisionLevel","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":6}
     * \endenglish
     */
    int getCollisionLevel();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置碰撞停止类型
     *
     * @param type 类型 \n
     * 0: 碰撞后浮动，即碰撞之后进入拖动示教模式 \n
     * 1: 碰撞后静止 \n
     * 2: 碰撞后抱闸
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setCollisionStopType(self: pyaubo_sdk.RobotConfig, arg0: int) -> int
     *
     * @par Lua函数原型
     * setCollisionStopType(type: number) -> nil
     *
     * @par Lua示例
     * setCollisionStopType(1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setCollisionStopType","params":[1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the collision stop type.
     *
     * @param type Type \n
     * 0: Floating after collision, i.e., enters freedrive mode after collision
     * \n 1: Stop after collision \n 2: Brake after collision
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setCollisionStopType(self: pyaubo_sdk.RobotConfig, arg0: int) -> int
     *
     * @par Lua function prototype
     * setCollisionStopType(type: number) -> nil
     *
     * @par Lua example
     * setCollisionStopType(1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setCollisionStopType","params":[1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setCollisionStopType(int type);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取碰撞停止类型
     *
     * @return 返回碰撞停止类型 \n
     * 0: 碰撞后浮动，即碰撞之后进入拖动示教模式 \n
     * 1: 碰撞后静止 \n
     * 2: 碰撞后抱闸
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getCollisionStopType(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua函数原型
     * getCollisionStopType() -> number
     *
     * @par Lua示例
     * CollisionStopType = getCollisionStopType()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getCollisionStopType","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endchinese
     * \english
     * Get the collision stop type.
     *
     * @return The collision stop type. \n
     * 0: Floating after collision, i.e., enters freedrive mode after collision
     * \n 1: Stop after collision \n 2: Brake after collision
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getCollisionStopType(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua function prototype
     * getCollisionStopType() -> number
     *
     * @par Lua example
     * CollisionStopType = getCollisionStopType()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getCollisionStopType","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endenglish
     */
    int getCollisionStopType();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置机器人的原点位置
     *
     * @param positions 关节角度
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setHomePosition","params":[[0.0,-0.2617993877991494,1.74532925199433,0.4363323129985824,1.570796326794897,0.0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the robot's home position.
     *
     * @param positions Joint angles
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setHomePosition","params":[[0.0,-0.2617993877991494,1.74532925199433,0.4363323129985824,1.570796326794897,0.0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setHomePosition(const std::vector<double> &positions);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人的原点位置
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getHomePosition","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,-0.2617993877991494,1.74532925199433,0.4363323129985824,1.570796326794897,0.0]}
     * \endchinese
     * \english
     * Get the robot's home position.
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getHomePosition","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,-0.2617993877991494,1.74532925199433,0.4363323129985824,1.570796326794897,0.0]}
     * \endenglish
     */
    std::vector<double> getHomePosition();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置拖动阻尼
     *
     * @param damp 阻尼
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setFreedriveDamp(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * setFreedriveDamp(damp: table) -> nil
     *
     * @par Lua示例
     * setFreedriveDamp({0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setFreedriveDamp","params":[[0.5,0.5,0.5,0.5,0.5,0.5]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set freedrive damping.
     *
     * @param damp Damping values.
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setFreedriveDamp(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * setFreedriveDamp(damp: table) -> nil
     *
     * @par Lua example
     * setFreedriveDamp({0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setFreedriveDamp","params":[[0.5,0.5,0.5,0.5,0.5,0.5]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setFreedriveDamp(const std::vector<double> &damp);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取拖动阻尼
     *
     * @return 拖动阻尼
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getFreedriveDamp(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getFreedriveDamp() -> table
     *
     * @par Lua示例
     * FreedriveDamp = getFreedriveDamp()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getFreedriveDamp","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.5,0.5,0.5,0.5,0.5,0.5]}
     * \endchinese
     * \english
     * Get freedrive damping.
     *
     * @return Freedrive damping values.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getFreedriveDamp(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getFreedriveDamp() -> table
     *
     * @par Lua example
     * FreedriveDamp = getFreedriveDamp()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getFreedriveDamp","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.5,0.5,0.5,0.5,0.5,0.5]}
     * \endenglish
     */
    std::vector<double> getFreedriveDamp();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置混合拖动阻尼
     *
     * @param damp 阻尼
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setHandguidDamp(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * setHandguidDamp(damp: table) -> number
     *
     * @par Lua示例
     * setHandguidDamp({0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setHandguidDamp","params":[[0.5,0.5,0.5,0.5,0.5,0.5]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set handguiding damping.
     *
     * @param damp damping coef.
     *
     * @return return 0 for success；return rror code for failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setHandguidDamp(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * setHandguidDamp(damp: table) -> number
     *
     * @par Lua example
     * setHandguidDamp({0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setHandguidDamp","params":[[0.5,0.5,0.5,0.5,0.5,0.5]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setHandguidDamp(const std::vector<double> &damp);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取混合拖动阻尼
     *
     * @return 拖动阻尼
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getHandguidDamp(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getHandguidDamp() -> table
     *
     * @par Lua示例
     * HandguidDamp = getHandguidDamp()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getHandguidDamp","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.5,0.5,0.5,0.5,0.5,0.5]}
     * \endchinese
     * \english
     * Get handguiding damping.
     *
     * @return handguuiding damping
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getHandguidDamp(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua fuunction prototype
     * getHandguidDamp() -> table
     *
     * @par Lua example
     * HandguidDamp = getHandguidDamp()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getHandguidDamp","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.5,0.5,0.5,0.5,0.5,0.5]}
     * \endenglish
     */
    std::vector<double> getHandguidDamp();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人DH参数
     * alpha a d theta beta
     *
     * @param real 读取真实参数(理论值+补偿值)或者理论参数
     * @return 返回机器人DH参数
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getKinematicsParam(self: pyaubo_sdk.RobotConfig, arg0: bool) -> Dict[str,
     * List[float]]
     *
     * @par Lua函数原型
     * getKinematicsParam(real: boolean) -> table
     *
     * @par Lua示例
     * KinematicsParam = getKinematicsParam(true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getKinematicsParam","params":[true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":{"a":[0.0,-0.0001255999959539622,0.4086348000024445,0.3757601999930339,-0.00018950000230688602,3.7000001611886546e-05],
     * "alpha":[0.0,-1.5701173967707458,3.1440308735524347,3.14650750358636,-1.5703093767832055,1.5751177669179182],"beta":[0.0,0.0,0.0,0.0,0.0,0.0],
     * "d":[0.122,0.12154769999941345,-4.769999941345304e-05,4.769999941345304e-05,0.10287890000385232,0.116],
     * "theta":[3.141592653589793,-1.5707963267948966,0.0,-1.5707963267948966,0.0,0.0]}}
     * \endchinese
     * \english
     * Get the robot's DH parameters: alpha, a, d, theta, beta.
     *
     * @param real Read real parameters (theoretical + compensation) or
     * theoretical parameters.
     * @return Returns the robot's DH parameters.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getKinematicsParam(self: pyaubo_sdk.RobotConfig, arg0: bool) -> Dict[str,
     * List[float]]
     *
     * @par Lua function prototype
     * getKinematicsParam(real: boolean) -> table
     *
     * @par Lua example
     * KinematicsParam = getKinematicsParam(true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getKinematicsParam","params":[true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":{"a":[0.0,-0.0001255999959539622,0.4086348000024445,0.3757601999930339,-0.00018950000230688602,3.7000001611886546e-05],
     * "alpha":[0.0,-1.5701173967707458,3.1440308735524347,3.14650750358636,-1.5703093767832055,1.5751177669179182],"beta":[0.0,0.0,0.0,0.0,0.0,0.0],
     * "d":[0.122,0.12154769999941345,-4.769999941345304e-05,4.769999941345304e-05,0.10287890000385232,0.116],
     * "theta":[3.141592653589793,-1.5707963267948966,0.0,-1.5707963267948966,0.0,0.0]}}
     * \endenglish
     */
    std::unordered_map<std::string, std::vector<double>> getKinematicsParam(
        bool real);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取指定温度下的DH参数补偿值:alpha a d theta beta
     *
     * @param ref_temperature 参考温度 ℃，默认20℃
     * @return 返回DH参数补偿值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getKinematicsCompensate(self: pyaubo_sdk.RobotConfig, arg0: float) ->
     * Dict[str, List[float]]
     *
     * @par Lua函数原型
     * getKinematicsCompensate(ref_temperature: number) -> table
     *
     * @par Lua示例
     * KinematicsCompensate = getKinematicsCompensate(20)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getKinematicsCompensate","params":[20],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":{"a":[0.0,-0.0001255999959539622,0.0006348000024445355,-0.0002398000069661066,-0.00018950000230688602,3.7000001611886546e-05],
     * "alpha":[0.0,0.000678930024150759,0.002438219962641597,0.0049148499965667725,0.00048695001169107854,0.004321440123021603],
     * "beta":[0.0,0.0,0.0,0.0,0.0,0.0],"d":[0.0,4.769999941345304e-05,-4.769999941345304e-05,4.769999941345304e-05,0.0003789000038523227,0.0],
     * "theta":[0.0,0.0,0.0,0.0,0.0,0.0]}}
     * \endchinese
     * \english
     * Get DH parameter compensation values (alpha, a, d, theta, beta) at the
     * specified temperature.
     *
     * @param ref_temperature Reference temperature in ℃, default is 20℃
     * @return Returns DH parameter compensation values.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getKinematicsCompensate(self: pyaubo_sdk.RobotConfig, arg0: float) ->
     * Dict[str, List[float]]
     *
     * @par Lua function prototype
     * getKinematicsCompensate(ref_temperature: number) -> table
     *
     * @par Lua example
     * KinematicsCompensate = getKinematicsCompensate(20)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getKinematicsCompensate","params":[20],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":{"a":[0.0,-0.0001255999959539622,0.0006348000024445355,-0.0002398000069661066,-0.00018950000230688602,3.7000001611886546e-05],
     * "alpha":[0.0,0.000678930024150759,0.002438219962641597,0.0049148499965667725,0.00048695001169107854,0.004321440123021603],
     * "beta":[0.0,0.0,0.0,0.0,0.0,0.0],"d":[0.0,4.769999941345304e-05,-4.769999941345304e-05,4.769999941345304e-05,0.0003789000038523227,0.0],
     * "theta":[0.0,0.0,0.0,0.0,0.0,0.0]}}
     * \endenglish
     */
    std::unordered_map<std::string, std::vector<double>>
    getKinematicsCompensate(double ref_temperature);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置标准 DH 补偿到机器人
     *
     * @param param
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Set standard DH compensation to the robot.
     *
     * @param param
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int setKinematicsCompensate(
        const std::unordered_map<std::string, std::vector<double>> &param);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置需要保存到接口板底座的参数
     *
     * @param param 补偿数据
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setPersistentParameters(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua函数原型
     * setPersistentParameters(param: string) -> nil
     *
     * \endchinese
     * \english
     * Set parameters to be saved to the interface board base.
     *
     * @param param Compensation data.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setPersistentParameters(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua function prototype
     * setPersistentParameters(param: string) -> nil
     *
     * \endenglish
     */
    int setPersistentParameters(const std::string &param);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置硬件抽象层自定义参数
     * 目的是为了做不同硬件之间的兼容
     *
     * @param param 自定义参数
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Set custom parameters for the hardware abstraction layer.
     * The purpose is to ensure compatibility between different hardware.
     *
     * @param param Custom parameters.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int setHardwareCustomParameters(const std::string &param);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取硬件抽象层自定义参数
     *
     * @param
     * @return 返回硬件抽象层自定义的参数
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Get custom parameters from the hardware abstraction layer.
     *
     * @param
     * @return Returns custom parameters from the hardware abstraction layer.
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    std::string getHardwareCustomParameters(const std::string &param);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置机器人关节零位
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setRobotZero(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua函数原型
     * setRobotZero() -> nil
     *
     * @par Lua示例
     * setRobotZero()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setRobotZero","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the robot joint zero position.
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setRobotZero(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua function prototype
     * setRobotZero() -> nil
     *
     * @par Lua example
     * setRobotZero()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setRobotZero","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setRobotZero();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取可用的末端力矩传感器的名字
     *
     * @return 返回可用的末端力矩传感器的名字
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getTcpForceSensorNames(self: pyaubo_sdk.RobotConfig) -> List[str]
     *
     * @par Lua函数原型
     * getTcpForceSensorNames() -> table
     *
     * @par Lua示例
     * TcpForceSensorNames = getTcpForceSensorNames()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpForceSensorNames","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endchinese
     * \english
     * Get the names of available TCP force sensors.
     *
     * @return Returns the names of available TCP force sensors.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getTcpForceSensorNames(self: pyaubo_sdk.RobotConfig) -> List[str]
     *
     * @par Lua function prototype
     * getTcpForceSensorNames() -> table
     *
     * @par Lua example
     * TcpForceSensorNames = getTcpForceSensorNames()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpForceSensorNames","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endenglish
     */
    std::vector<std::string> getTcpForceSensorNames();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置末端力矩传感器
     * 如果存在内置的末端力矩传感器，默认将使用内置的力矩传感器
     *
     * @param name 末端力矩传感器的名字
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * selectTcpForceSensor(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua函数原型
     * selectTcpForceSensor(name: string) -> nil
     * \endchinese
     * \english
     * Set the TCP force sensor.
     * If there is a built-in TCP force sensor, the built-in sensor will be used
     * by default.
     *
     * @param name Name of the TCP force sensor.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * selectTcpForceSensor(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua function prototype
     * selectTcpForceSensor(name: string) -> nil
     * \endenglish
     */
    int selectTcpForceSensor(const std::string &name);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置传感器安装位姿
     *
     * @param sensor_pose 传感器安装位姿
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Set the sensor mounting pose.
     *
     * @param sensor_pose Sensor mounting pose
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int setTcpForceSensorPose(const std::vector<double> &sensor_pose);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取传感器安装位姿
     *
     * @return 传感器安装位姿
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpForceSensorPose","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endchinese
     * \english
     * Get the sensor mounting pose.
     *
     * @return Sensor mounting pose.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpForceSensorPose","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endenglish
     */
    std::vector<double> getTcpForceSensorPose();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 是否安装了末端力矩传感器
     *
     * @return 安装返回true; 没有安装返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * hasTcpForceSensor(self: pyaubo_sdk.RobotConfig) -> bool
     *
     * @par Lua函数原型
     * hasTcpForceSensor() -> boolean
     *
     * @par Lua示例
     * hasTcpForceSensor = hasTcpForceSensor()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.hasTcpForceSensor","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Whether a TCP force sensor is installed.
     *
     * @return Returns true if installed; false otherwise.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * hasTcpForceSensor(self: pyaubo_sdk.RobotConfig) -> bool
     *
     * @par Lua function prototype
     * hasTcpForceSensor() -> boolean
     *
     * @par Lua example
     * hasTcpForceSensor = hasTcpForceSensor()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.hasTcpForceSensor","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool hasTcpForceSensor();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置末端力矩偏移
     *
     * @param force_offset 末端力矩偏移
     * @return 成功返回0; 失败返回错误码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setTcpForceOffset(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * setTcpForceOffset(force_offset: table) -> nil
     *
     * @par Lua示例
     * setTcpForceOffset({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * \endchinese
     * \english
     * Set the TCP force/torque offset.
     *
     * @param force_offset TCP force/torque offset
     * @return Returns 0 on success; error code on failure
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setTcpForceOffset(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * setTcpForceOffset(force_offset: table) -> nil
     *
     * @par Lua example
     * setTcpForceOffset({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * \endenglish
     */
    int setTcpForceOffset(const std::vector<double> &force_offset);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取末端力矩偏移
     *
     * @return 返回末端力矩偏移
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getTcpForceOffset(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getTcpForceOffset() -> table
     *
     * @par Lua示例
     * TcpForceOffset = getTcpForceOffset()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpForceOffset","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endchinese
     * \english
     * Get the TCP force/torque offset.
     *
     * @return Returns the TCP force/torque offset.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getTcpForceOffset(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getTcpForceOffset() -> table
     *
     * @par Lua example
     * TcpForceOffset = getTcpForceOffset()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpForceOffset","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endenglish
     */
    std::vector<double> getTcpForceOffset();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取可用的底座力矩传感器的名字
     *
     * @return 返回可用的底座力矩传感器的名字
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getBaseForceSensorNames(self: pyaubo_sdk.RobotConfig) -> List[str]
     *
     * @par Lua函数原型
     * getBaseForceSensorNames() -> table
     *
     * @par Lua示例
     * BaseForceSensorNames = getBaseForceSensorNames()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getBaseForceSensorNames","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endchinese
     * \english
     * Get the names of available base force sensors.
     *
     * @return Returns the names of available base force sensors.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getBaseForceSensorNames(self: pyaubo_sdk.RobotConfig) -> List[str]
     *
     * @par Lua function prototype
     * getBaseForceSensorNames() -> table
     *
     * @par Lua example
     * BaseForceSensorNames = getBaseForceSensorNames()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getBaseForceSensorNames","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endenglish
     */
    std::vector<std::string> getBaseForceSensorNames();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置底座力矩传感器
     * 如果存在内置的底座力矩传感器，默认将使用内置的力矩传感器
     *
     * @param name 底座力矩传感器的名字
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * selectBaseForceSensor(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua函数原型
     * selectBaseForceSensor(name: string) -> nil
     * \endchinese
     * \english
     * Set the base force sensor.
     * If there is a built-in base force sensor, the built-in sensor will be
     * used by default.
     *
     * @param name Name of the base force sensor.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * selectBaseForceSensor(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua function prototype
     * selectBaseForceSensor(name: string) -> nil
     * \endenglish
     */
    int selectBaseForceSensor(const std::string &name);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 是否安装了底座力矩传感器
     *
     * @return 安装返回true;没有安装返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * hasBaseForceSensor(self: pyaubo_sdk.RobotConfig) -> bool
     *
     * @par Lua函数原型
     * hasBaseForceSensor() -> boolean
     *
     * @par Lua示例
     * hasBaseForceSensor = hasBaseForceSensor()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.hasBaseForceSensor","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Whether a base force sensor is installed.
     *
     * @return Returns true if installed; false otherwise.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * hasBaseForceSensor(self: pyaubo_sdk.RobotConfig) -> bool
     *
     * @par Lua function prototype
     * hasBaseForceSensor() -> boolean
     *
     * @par Lua example
     * hasBaseForceSensor = hasBaseForceSensor()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.hasBaseForceSensor","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool hasBaseForceSensor();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置底座力矩偏移
     *
     * @param force_offset 底座力矩偏移
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setBaseForceOffset(self: pyaubo_sdk.RobotConfig, arg0: List[float]) ->
     * int
     *
     * @par Lua函数原型
     * setBaseForceOffset(force_offset: table) -> nil
     *
     * @par Lua示例
     * setBaseForceOffset({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * \endchinese
     * \english
     * Set the base force/torque offset.
     *
     * @param force_offset Base force/torque offset
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setBaseForceOffset(self: pyaubo_sdk.RobotConfig, arg0: List[float]) ->
     * int
     *
     * @par Lua function prototype
     * setBaseForceOffset(force_offset: table) -> nil
     *
     * @par Lua示例
     * setBaseForceOffset({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * \endenglish
     */
    int setBaseForceOffset(const std::vector<double> &force_offset);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取底座力矩偏移
     *
     * @return 返回底座力矩偏移
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getBaseForceOffset(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getBaseForceOffset() -> table
     *
     * @par Lua示例
     * BaseForceOffset = getBaseForceOffset()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getBaseForceOffset","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endchinese
     * \english
     * Get the base force/torque offset.
     *
     * @return Returns the base force/torque offset.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getBaseForceOffset(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getBaseForceOffset() -> table
     *
     * @par Lua example
     * BaseForceOffset = getBaseForceOffset()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getBaseForceOffset","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endenglish
     */
    std::vector<double> getBaseForceOffset();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取安全参数校验码 CRC32
     *
     * @return 返回安全参数校验码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getSafetyParametersCheckSum(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua函数原型
     * getSafetyParametersCheckSum() -> number
     *
     * @par Lua示例
     * SafetyParametersCheckSum = getSafetyParametersCheckSum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSafetyParametersCheckSum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":2033397241}
     *
     * \endchinese
     * \english
     * Get the safety parameter checksum CRC32.
     *
     * @return Returns the safety parameter checksum.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getSafetyParametersCheckSum(self: pyaubo_sdk.RobotConfig) -> int
     *
     * @par Lua function prototype
     * getSafetyParametersCheckSum() -> number
     *
     * @par Lua示例
     * SafetyParametersCheckSum = getSafetyParametersCheckSum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSafetyParametersCheckSum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":2033397241}
     *
     * \endenglish
     */
    uint32_t getSafetyParametersCheckSum();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 发起确认安全配置参数请求:
     * 将安全配置参数写入到安全接口板flash或文件
     *
     * @param parameters 安全配置参数
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * confirmSafetyParameters(self: pyaubo_sdk.RobotConfig, arg0:
     * arcs::common_interface::RobotSafetyParameterRange) -> int
     *
     * @par Lua函数原型
     *
     * \endchinese
     * \english
     * Initiate a request to confirm safety configuration parameters:
     * Write safety configuration parameters to the safety interface board flash
     * or file.
     *
     * @param parameters Safety configuration parameters.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * confirmSafetyParameters(self: pyaubo_sdk.RobotConfig, arg0:
     * arcs::common_interface::RobotSafetyParameterRange) -> int
     *
     * @par Lua function prototype
     *
     * \endenglish
     */
    int confirmSafetyParameters(const RobotSafetyParameterRange &parameters);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 计算安全参数的 CRC32 校验值
     *
     * @return crc32
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Calculate the CRC32 checksum of safety parameters.
     *
     * @return crc32
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    uint32_t calcSafetyParametersCheckSum(
        const RobotSafetyParameterRange &parameters);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最大位置（物理极限）
     *
     * @return 返回关节最大位置
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getJointMaxPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getJointMaxPositions() -> table
     *
     * @par Lua示例
     * JointMaxPositions = getJointMaxPositions()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMaxPositions","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[6.283185307179586,6.283185307179586,6.283185307179586,6.283185307179586,6.283185307179586,6.283185307179586]}
     * \endchinese
     * \english
     * Get the joint maximum positions (physical limits).
     *
     * @return Returns the joint maximum positions.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getJointMaxPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getJointMaxPositions() -> table
     *
     * @par Lua example
     * JointMaxPositions = getJointMaxPositions()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMaxPositions","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[6.283185307179586,6.283185307179586,6.283185307179586,6.283185307179586,6.283185307179586,6.283185307179586]}
     * \endenglish
     */
    std::vector<double> getJointMaxPositions();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最小位置（物理极限）
     *
     * @return 返回关节最小位置
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getJointMinPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getJointMinPositions() -> table
     *
     * @par Lua示例
     * JointMinPositions = getJointMinPositions()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMinPositions","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[-6.283185307179586,-6.283185307179586,-6.283185307179586,-6.283185307179586,-6.283185307179586,-6.283185307179586]}
     * \endchinese
     * \english
     * Get the joint minimum positions (physical limits).
     *
     * @return Returns the joint minimum positions.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getJointMinPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getJointMinPositions() -> table
     *
     * @par Lua example
     * JointMinPositions = getJointMinPositions()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMinPositions","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[-6.283185307179586,-6.283185307179586,-6.283185307179586,-6.283185307179586,-6.283185307179586,-6.283185307179586]}
     * \endenglish
     */
    std::vector<double> getJointMinPositions();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最大速度（物理极限）
     *
     * @return 返回关节最大速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getJointMaxSpeeds(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getJointMaxSpeeds() -> table
     *
     * @par Lua示例
     * JointMaxSpeeds = getJointMaxSpeeds()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMaxSpeeds","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[3.892084231947355,3.892084231947355,3.892084231947355,3.1066860685499065,3.1066860685499065,3.1066860685499065]}
     * \endchinese
     * \english
     * Get the joint maximum speeds (physical limits).
     *
     * @return Returns the joint maximum speeds.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getJointMaxSpeeds(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getJointMaxSpeeds() -> table
     *
     * @par Lua example
     * JointMaxSpeeds = getJointMaxSpeeds()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMaxSpeeds","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[3.892084231947355,3.892084231947355,3.892084231947355,3.1066860685499065,3.1066860685499065,3.1066860685499065]}
     * \endenglish
     */
    std::vector<double> getJointMaxSpeeds();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最大加速度（物理极限）
     *
     * @return 返回关节最大加速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getJointMaxAccelerations(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getJointMaxAccelerations() -> table
     *
     * @par Lua示例
     * JointMaxAccelerations = getJointMaxAccelerations()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMaxAccelerations","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[31.104877758314785,31.104877758314785,31.104877758314785,20.73625684294463,20.73625684294463,20.73625684294463]}
     * \endchinese
     * \english
     * Get the joint maximum accelerations (physical limits).
     *
     * @return Returns the joint maximum accelerations.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getJointMaxAccelerations(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getJointMaxAccelerations() -> table
     *
     * @par Lua example
     * JointMaxAccelerations = getJointMaxAccelerations()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getJointMaxAccelerations","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[31.104877758314785,31.104877758314785,31.104877758314785,20.73625684294463,20.73625684294463,20.73625684294463]}
     * \endenglish
     */
    std::vector<double> getJointMaxAccelerations();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取TCP最大速度（物理极限）
     *
     * @return 返回TCP最大速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getTcpMaxSpeeds(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getTcpMaxSpeeds() -> table
     *
     * @par Lua示例
     * TcpMaxSpeeds = getTcpMaxSpeeds()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpMaxSpeeds","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[2.0,5.0]}
     * \endchinese
     * \english
     * Get the TCP maximum speed (physical limits).
     *
     * @return Returns the TCP maximum speed.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getTcpMaxSpeeds(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getTcpMaxSpeeds() -> table
     *
     * @par Lua example
     * TcpMaxSpeeds = getTcpMaxSpeeds()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpMaxSpeeds","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[2.0,5.0]}
     * \endenglish
     */
    std::vector<double> getTcpMaxSpeeds();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取TCP最大加速度（物理极限）
     *
     * @return 返回TCP最大加速度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getTcpMaxAccelerations(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getTcpMaxAccelerations() -> table
     *
     * @par Lua示例
     * TcpMaxAccelerations = getTcpMaxAccelerations()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpMaxAccelerations","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[10.0,10.0]}
     *
     * \endchinese
     * \english
     * Get the TCP maximum acceleration (physical limits).
     *
     * @return Returns the TCP maximum acceleration.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getTcpMaxAccelerations(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getTcpMaxAccelerations() -> table
     *
     * @par Lua example
     * TcpMaxAccelerations = getTcpMaxAccelerations()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpMaxAccelerations","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[10.0,10.0]}
     * \endenglish
     */
    std::vector<double> getTcpMaxAccelerations();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置机器人安装姿态
     *
     * @param gravity 安装姿态
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setGravity(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * setGravity(gravity: table) -> nil
     *
     * @par Lua示例
     * setGravity({0.0,0.0,-9.87654321})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setGravity","params":[[0.0,0.0,-9.87654321]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the robot installation attitude (gravity vector).
     *
     * @param gravity Installation attitude (gravity vector)
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setGravity(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * setGravity(gravity: table) -> nil
     *
     * @par Lua example
     * setGravity({0.0,0.0,-9.87654321})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setGravity","params":[[0.0,0.0,-9.87654321]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setGravity(const std::vector<double> &gravity);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取机器人的安装姿态
     *
     * 如果机器人底座安装了姿态传感器，则从传感器读取数据，否则按照用户设置
     *
     * @return 返回安装姿态
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getGravity(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getGravity() -> table
     *
     * @par Lua示例
     * Gravity = getGravity()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getGravity","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,-9.87654321]}
     *
     * \endchinese
     * \english
     * Get the robot's installation attitude (gravity vector).
     *
     * If the robot base is equipped with an attitude sensor, data is read from
     * the sensor; otherwise, the user setting is used.
     *
     * @return Returns the installation attitude.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getGravity(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getGravity() -> table
     *
     * @par Lua example
     * Gravity = getGravity()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getGravity","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,-9.87654321]}
     *
     * \endenglish
     */
    std::vector<double> getGravity();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置当前的TCP偏移
     *
     * TCP偏移表示形式为(x,y,z,rx,ry,rz)。
     * 其中x、y、z是工具中心点（TCP）在基坐标系下相对于法兰盘中心的位置偏移，单位是m。
     * rx、ry、rz是工具中心点（TCP）在基坐标系下相对于法兰盘中心的的姿态偏移，是ZYX欧拉角，单位是rad。
     *
     * @param offset 当前的TCP偏移,形式为(x,y,z,rx,ry,rz)
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setTcpOffset(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * setTcpOffset(offset: table) -> nil
     *
     * @par Lua示例
     * setTcpOffset({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setTcpOffset","params":[[0.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the current TCP offset.
     *
     * The TCP offset is represented as (x, y, z, rx, ry, rz).
     * x, y, z are the position offsets of the Tool Center Point (TCP) relative
     * to the flange center in the base coordinate system, in meters. rx, ry, rz
     * are the orientation offsets of the TCP relative to the flange center in
     * the base coordinate system, as ZYX Euler angles in radians.
     *
     * @param offset The current TCP offset, in the form (x, y, z, rx, ry, rz)
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setTcpOffset(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * setTcpOffset(offset: table) -> nil
     *
     * @par Lua example
     * setTcpOffset({0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setTcpOffset","params":[[0.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setTcpOffset(const std::vector<double> &offset);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取当前的TCP偏移
     *
     * TCP偏移表示形式为(x,y,z,rx,ry,rz)。
     * 其中x、y、z是工具中心点（TCP）在基坐标系下相对于法兰盘中心的位置偏移，单位是m。
     * rx、ry、rz是工具中心点（TCP）在基坐标系下相对于法兰盘中心的的姿态偏移，是ZYX欧拉角，单位是rad。
     *
     * @return 当前的TCP偏移,形式为(x,y,z,rx,ry,rz)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getTcpOffset(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getTcpOffset() -> table
     *
     * @par Lua示例
     * TcpOffset = getTcpOffset()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpOffset","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endchinese
     * \english
     * Get the current TCP offset.
     *
     * The TCP offset is represented as (x, y, z, rx, ry, rz).
     * x, y, z are the position offsets of the Tool Center Point (TCP) relative
     * to the flange center in the base coordinate system, in meters. rx, ry, rz
     * are the orientation offsets of the TCP relative to the flange center in
     * the base coordinate system, as ZYX Euler angles in radians.
     *
     * @return The current TCP offset, in the form (x, y, z, rx, ry, rz)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getTcpOffset(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getTcpOffset() -> table
     *
     * @par Lua example
     * TcpOffset = getTcpOffset()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getTcpOffset","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,0.0,0.0,0.0,0.0]}
     * \endenglish
     */
    std::vector<double> getTcpOffset();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置工具端质量、质心及惯量
     *
     * @param m 工具端质量
     * @param com 质心
     * @param inertial 惯量
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolInertial(self: pyaubo_sdk.RobotConfig, arg0: float, arg1:
     * List[float], arg2: List[float]) -> int
     *
     * @par Lua函数原型
     * setToolInertial(m: number, com: table, inertial: table) -> nil
     *
     * @par Lua示例
     * setToolInertial(3, {0,0,0}, {0,0,0}, {0,0,0,0,0,0,0,0,0})
     *
     * \endchinese
     * \english
     * Set tool mass, center of mass, and inertia.
     *
     * @param m Tool mass
     * @param com Center of mass
     * @param inertial Inertia
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolInertial(self: pyaubo_sdk.RobotConfig, arg0: float, arg1:
     * List[float], arg2: List[float]) -> int
     *
     * @par Lua function prototype
     * setToolInertial(m: number, com: table, inertial: table) -> nil
     *
     * @par Lua example
     * setToolInertial(3, {0,0,0}, {0,0,0}, {0,0,0,0,0,0,0,0,0})
     *
     * \endenglish
     */
    int setToolInertial(double m, const std::vector<double> &com,
                        const std::vector<double> &inertial);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置有效负载
     *
     * @param m 质量, 单位: kg
     * @param cog 重心, 单位: m, 形式为(CoGx, CoGy, CoGz)
     * @param aom 力矩轴的方向, 单位: rad, 形式为(rx, ry, rz)
     * @param inertia 惯量, 单位: kg*m^2, 形式为(Ixx, Iyy, Izz, Ixy, Ixz,
     * Iyz)或(Ixx, Ixy, Ixz, Iyx, Iyy, Iyz, Izx, Izy, Izz)
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setPayload(self: pyaubo_sdk.RobotConfig, arg0: float, arg1: List[float],
     * arg2: List[float], arg3: List[float]) -> int
     *
     * @par Lua函数原型
     * setPayload(m: number, cog: table, aom: table, inertia: table) -> nil
     *
     * @par Lua示例
     * setPayload(3, {0,0,0}, {0,0,0}, {0,0,0,0,0,0,0,0,0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setPayload","params":[3,[0,0,0],[0,0,0],[0,0,0,0,0,0,0,0,0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the payload.
     *
     * @param m Mass, unit: kg
     * @param cog Center of gravity, unit: m, format (CoGx, CoGy, CoGz)
     * @param aom Axis of moment, unit: rad, format (rx, ry, rz)
     * @param inertia Inertia, unit: kg*m^2, format (Ixx, Iyy, Izz, Ixy, Ixz,
     * Iyz) or (Ixx, Ixy, Ixz, Iyx, Iyy, Iyz, Izx, Izy, Izz)
     *
     * @return Returns 0 on success; error code on failure
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setPayload(self: pyaubo_sdk.RobotConfig, arg0: float, arg1: List[float],
     * arg2: List[float], arg3: List[float]) -> int
     *
     * @par Lua function prototype
     * setPayload(m: number, cog: table, aom: table, inertia: table) -> nil
     *
     * @par Lua example
     * setPayload(3, {0,0,0}, {0,0,0}, {0,0,0,0,0,0,0,0,0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setPayload","params":[3,[0,0,0],[0,0,0],[0,0,0,0,0,0,0,0,0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setPayload(double m, const std::vector<double> &cog,
                   const std::vector<double> &aom,
                   const std::vector<double> &inertia);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取有效负载
     *
     * @return 有效负载.
     * 第一个元素表示质量, 单位: kg;
     * 第二个元素表示重心, 单位: m, 形式为(CoGx, CoGy, CoGz);
     * 第三个元素表示力矩轴的方向, 单位: rad, 形式为(rx, ry, rz);
     * 第四个元素表示惯量, 单位: kg*m^2, 形式为(Ixx, Iyy, Izz, Ixy, Ixz, Iyz)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getPayload(self: pyaubo_sdk.RobotConfig) -> Tuple[float, List[float],
     * List[float], List[float]]
     *
     * @par Lua函数原型
     * getPayload() -> number, table, table, table
     *
     * @par Lua示例
     * m, cog, aom, inertia = getPayload()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getPayload","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[3.0,[0.0,0.0,0.0],[0.0,0.0,0.0],[0.0,0.0,0.0,0.0,0.0,0.0]]}
     * \endchinese
     * \english
     * Get the payload.
     *
     * @return The payload.
     * The first element is the mass in kg;
     * The second element is the center of gravity in meters, format (CoGx,
     * CoGy, CoGz); The third element is the axis of moment in radians, format
     * (rx, ry, rz); The fourth element is the inertia in kg*m^2, format (Ixx,
     * Iyy, Izz, Ixy, Ixz, Iyz)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getPayload(self: pyaubo_sdk.RobotConfig) -> Tuple[float, List[float],
     * List[float], List[float]]
     *
     * @par Lua function prototype
     * getPayload() -> number, table, table, table
     *
     * @par Lua example
     * m, cog, aom, inertia = getPayload()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getPayload","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[3.0,[0.0,0.0,0.0],[0.0,0.0,0.0],[0.0,0.0,0.0,0.0,0.0,0.0]]}
     * \endenglish
     */
    Payload getPayload();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 末端位姿是否在安全范围之内
     *
     * @param pose 末端位姿
     * @return 在安全范围内返回true; 反之返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * toolSpaceInRange(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> bool
     *
     * @par Lua函数原型
     * toolSpaceInRange(pose: table) -> boolean
     *
     * @par Lua示例
     * SpaceInRange = toolSpaceInRange({0.58712,-0.15775, 0.48703, 2.76,
     * 0.344, 1.432})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.toolSpaceInRange","params":[[0.58712,
     * -0.15775, 0.48703, 2.76, 0.344, 1.432]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endchinese
     * \english
     * Whether the end-effector pose is within the safety range.
     *
     * @param pose End-effector pose
     * @return Returns true if within the safety range; otherwise returns false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * toolSpaceInRange(self: pyaubo_sdk.RobotConfig, arg0: List[float]) -> bool
     *
     * @par Lua function prototype
     * toolSpaceInRange(pose: table) -> boolean
     *
     * @par Lua example
     * SpaceInRange = toolSpaceInRange({0.58712,-0.15775, 0.48703, 2.76,
     * 0.344, 1.432})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.toolSpaceInRange","params":[[0.58712,
     * -0.15775, 0.48703, 2.76, 0.344, 1.432]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endenglish
     */
    bool toolSpaceInRange(const std::vector<double> &pose);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 发起固件升级请求，控制器软件将进入固件升级模式
     *
     * @param fw 固件升级路径。该路径的格式为: 固件安装包路径\#升级节点列表。
     * 其中固件安装包路径和升级节点列表以井号(#)分隔，升级节点以逗号(,)分隔。
     * 如果节点名称后带有!，则表示强制(不带版本校验)升级该节点；
     * 反之，则表示带校验版本地升级节点，
     * 即在升级该节点前，会先判断当前版本和目标版本是否相同，如果相同就不升级该节点。\n
     * 可以根据实际需求灵活设置需要升级的节点。\n
     * 例如，
     * /tmp/firmware_update-1.0.42-rc.5+2347b0d.firm\#master_mcu!,slace_mcu!,
     * base!,tool!,joint1!,joint2!,joint3!,joint4!,joint5!,joint6!
     * 表示强制升级接口板主板、接口板从板、基座、工具和6个关节（joint1至joint6）。\n
     * all表示所有的节点，例如
     * /tmp/firm_XXX.firm\#all 表示带校验版本地升级全部节点，
     * /tmp/firm_XXX.firm\#all！表示强制升级全部节点
     *
     * @return 指令下发成功返回0; 失败返回错误码。 \n
     * -AUBO_BAD_STATE: 运行时(RuntimeMachine)的当前状态不是Stopped,
     * 固件升级请求被拒绝。AUBO_BAD_STATE的值是1。 \n
     * -AUBO_TIMEOUT: 超时。AUBO_TIMEOUT的值是4。 \n
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * firmwareUpdate(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua函数原型
     * firmwareUpdate(fw: string) -> nil
     *
     * @par Lua示例
     * firmwareUpdate("/tmp/firmware_update-1.0.42-rc.12+3e33eac.firm#master_mcu")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.firmwareUpdate","params":["/tmp/firmware_update-1.0.42-rc.12+3e33eac.firm#master_mcu"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Initiate a firmware upgrade request. The controller software will enter
     * firmware upgrade mode.
     *
     * @param fw Firmware upgrade path. The format is: firmware package
     * path\#upgrade node list. The firmware package path and node list are
     * separated by a hash (#), and nodes are separated by commas (,). If a node
     * name ends with !, it means to force upgrade (without version check) that
     * node; otherwise, the node will be upgraded only if the current version
     * differs from the target version. You can flexibly specify which nodes to
     * upgrade as needed. For example,
     * /tmp/firmware_update-1.0.42-rc.5+2347b0d.firm#master_mcu!,slace_mcu!,base!,tool!,joint1!,joint2!,joint3!,joint4!,joint5!,joint6!
     * means to force upgrade the interface board main, interface board slave,
     * base, tool, and joints 1-6. "all" means all nodes, e.g.
     * /tmp/firm_XXX.firm#all means upgrade all nodes with version check,
     * /tmp/firm_XXX.firm#all! means force upgrade all nodes.
     *
     * @return Returns 0 if the command is sent successfully; otherwise, returns
     * an error code. -AUBO_BAD_STATE: The current state of the RuntimeMachine
     * is not Stopped, so the firmware upgrade request is rejected.
     * AUBO_BAD_STATE = 1. -AUBO_TIMEOUT: Timeout. AUBO_TIMEOUT = 4.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * firmwareUpdate(self: pyaubo_sdk.RobotConfig, arg0: str) -> int
     *
     * @par Lua function prototype
     * firmwareUpdate(fw: string) -> nil
     *
     * @par Lua example
     * firmwareUpdate("/tmp/firmware_update-1.0.42-rc.12+3e33eac.firm#master_mcu")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.firmwareUpdate","params":["/tmp/firmware_update-1.0.42-rc.12+3e33eac.firm#master_mcu"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int firmwareUpdate(const std::string &fw);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取当前的固件升级的进程
     *
     * @return 当前的固件升级进程。 \n
     * 第一个元素表示步骤名称。如果是failed，则表示固件升级失败 \n
     * 第二个元素表示升级的进度(0~1)，完成之后，返回("", 1)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getFirmwareUpdateProcess(self: pyaubo_sdk.RobotConfig) -> Tuple[str,
     * float]
     *
     * @par Lua函数原型
     * getFirmwareUpdateProcess() -> table
     *
     * @par Lua示例
     * step,progress = getFirmwareUpdateProcess()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getFirmwareUpdateProcess","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[" ",0.0]}
     *
     * \endchinese
     * \english
     * Get the current firmware upgrade process.
     *
     * @return The current firmware upgrade process. \n
     * The first element is the step name. If it is "failed", the firmware
     * upgrade failed. \n The second element is the upgrade progress (0~1). When
     * finished, returns ("", 1)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getFirmwareUpdateProcess(self: pyaubo_sdk.RobotConfig) -> Tuple[str,
     * float]
     *
     * @par Lua function prototype
     * getFirmwareUpdateProcess() -> table
     *
     * @par Lua example
     * step,progress = getFirmwareUpdateProcess()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getFirmwareUpdateProcess","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[" ",0.0]}
     *
     * \endenglish
     */
    std::tuple<std::string, double> getFirmwareUpdateProcess();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最大位置（当前正在使用的限制值）
     *
     * @return 返回关节最大位置（当前正在使用的限制值）
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getLimitJointMaxPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getLimitJointMaxPositions() -> table
     *
     * @par Lua示例
     * LimitJointMaxPositions = getLimitJointMaxPositions()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMaxPositions","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[6.2831854820251465,6.2831854820251465,6.2831854820251465,6.2831854820251465,6.2831854820251465,6.2831854820251465]}
     * \endchinese
     * \english
     * Get the joint maximum positions (currently used limit values).
     *
     * @return Returns the joint maximum positions (currently used limit
     * values).
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getLimitJointMaxPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getLimitJointMaxPositions() -> table
     *
     * @par Lua example
     * LimitJointMaxPositions = getLimitJointMaxPositions()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMaxPositions","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[6.2831854820251465,6.2831854820251465,6.2831854820251465,6.2831854820251465,6.2831854820251465,6.2831854820251465]}
     * \endenglish
     */
    std::vector<double> getLimitJointMaxPositions();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最小位置（当前正在使用的限制值）
     *
     * @return 返回关节最小位置（当前正在使用的限制值）
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getLimitJointMinPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getLimitJointMinPositions() -> table
     *
     * @par Lua示例
     * LimitJointMinPositions = getLimitJointMinPositions()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMinPositions","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[-6.2831854820251465,-6.2831854820251465,-6.2831854820251465,-6.2831854820251465,-6.2831854820251465,-6.2831854820251465]}
     * \endchinese
     * \english
     * Get the joint minimum positions (currently used limit values).
     *
     * @return Returns the joint minimum positions (currently used limit
     * values).
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getLimitJointMinPositions(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getLimitJointMinPositions() -> table
     *
     * @par Lua example
     * LimitJointMinPositions = getLimitJointMinPositions()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMinPositions","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[-6.2831854820251465,-6.2831854820251465,-6.2831854820251465,-6.2831854820251465,-6.2831854820251465,-6.2831854820251465]}
     * \endenglish
     */
    std::vector<double> getLimitJointMinPositions();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最大速度（当前正在使用的限制值）
     *
     * @return 返回关节最大速度（当前正在使用的限制值）
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getLimitJointMaxSpeeds(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getLimitJointMaxSpeeds() -> table
     *
     * @par Lua示例
     * LimitJointMaxSpeeds = getLimitJointMaxSpeeds()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMaxSpeeds","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[3.8920841217041016,3.8920841217041016,3.8920841217041016,3.1066861152648926,3.1066861152648926,3.1066861152648926]}
     * \endchinese
     * \english
     * Get the joint maximum speeds (currently used limit values).
     *
     * @return Returns the joint maximum speeds (currently used limit values).
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getLimitJointMaxSpeeds(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getLimitJointMaxSpeeds() -> table
     *
     * @par Lua example
     * LimitJointMaxSpeeds = getLimitJointMaxSpeeds()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMaxSpeeds","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[3.8920841217041016,3.8920841217041016,3.8920841217041016,3.1066861152648926,3.1066861152648926,3.1066861152648926]}
     * \endenglish
     */
    std::vector<double> getLimitJointMaxSpeeds();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取关节最大加速度（当前正在使用的限制值）
     *
     * @return 返回关节最大加速度（当前正在使用的限制值）
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getLimitJointMaxAccelerations(self: pyaubo_sdk.RobotConfig) ->
     * List[float]
     *
     * @par Lua函数原型
     * getLimitJointMaxAccelerations() -> table
     *
     * @par Lua示例
     * LimitJointMaxAccelerations = getLimitJointMaxAccelerations()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMaxAccelerations","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[31.104877758314785,31.104877758314785,31.104877758314785,20.73625684294463,20.73625684294463,20.73625684294463]}
     * \endchinese
     * \english
     * Get the joint maximum accelerations (currently used limit values).
     *
     * @return Returns the joint maximum accelerations (currently used limit
     * values).
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getLimitJointMaxAccelerations(self: pyaubo_sdk.RobotConfig) ->
     * List[float]
     *
     * @par Lua function prototype
     * getLimitJointMaxAccelerations() -> table
     *
     * @par Lua example
     * LimitJointMaxAccelerations = getLimitJointMaxAccelerations()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitJointMaxAccelerations","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[31.104877758314785,31.104877758314785,31.104877758314785,20.73625684294463,20.73625684294463,20.73625684294463]}
     * \endenglish
     */
    std::vector<double> getLimitJointMaxAccelerations();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取TCP最大速度（当前正在使用的限制值）
     *
     * @return 返回TCP最大速度（当前正在使用的限制值）
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getLimitTcpMaxSpeed(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getLimitTcpMaxSpeed() -> number
     *
     * @par Lua示例
     * LimitTcpMaxSpeed = getLimitTcpMaxSpeed()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitTcpMaxSpeed","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":2.0}
     * \endchinese
     * \english
     * Get the TCP maximum speed (currently used limit value).
     *
     * @return Returns the TCP maximum speed (currently used limit value).
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getLimitTcpMaxSpeed(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getLimitTcpMaxSpeed() -> number
     *
     * @par Lua example
     * LimitTcpMaxSpeed = getLimitTcpMaxSpeed()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getLimitTcpMaxSpeed","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":2.0}
     * \endenglish
     */
    double getLimitTcpMaxSpeed();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取当前安全停止的类型
     *
     * @return 返回当前安全停止的类型
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSafeguardStopType","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     * \endchinese
     * \english
     * Get the current safeguard stop type.
     *
     * @return Returns the current safeguard stop type.
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSafeguardStopType","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     * \endenglish
     */
    SafeguedStopType getSafeguardStopType();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 按位获取完整的安全停止触发源
     *
     * @return 返回所有安全停止触发源
     *
     * 安全停止的原因:
     * 手动模式下可配置安全IO触发的安全停止 - 1<<0
     * 自动模式下可配置安全IO触发的安全停止 - 1<<1
     * 控制柜SI输入触发的安全停止 - 1<<2
     * 示教器三态开关触发的安全停止 - 1<<3
     * 自动切手动触发的安全停止 - 1<<4
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSafeguardStopSource","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Get the complete safeguard stop source as a bitmask.
     *
     * @return Returns all safeguard stop sources.
     *
     * Reasons for safeguard stop:
     * Safeguard stop triggered by configurable safety IO in manual mode - 1<<0
     * Safeguard stop triggered by configurable safety IO in automatic mode -
     * 1<<1 Safeguard stop triggered by control box SI input - 1<<2 Safeguard
     * stop triggered by teach pendant three-position switch - 1<<3 Safeguard
     * stop triggered by switching from auto to manual - 1<<4
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSafeguardStopSource","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int getSafeguardStopSource();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 按位获取完整的机器人紧急停止触发源
     *
     * @return 返回所有机器人紧急停止触发源
     *
     * 紧急停止的原因:
     * 控制柜紧急停止按钮触发 - 1<<0
     * 示教器紧急停止按钮触发 - 1<<1
     * 手柄紧急停止按钮触发 - 1<<2
     * 固定IO紧急停止触发 - 1<<3
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getRobotEmergencyStopSource","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Get the complete robot emergency stop source as a bitmask.
     *
     * @return Returns all robot emergency stop sources.
     *
     * Reasons for emergency stop:
     * Emergency stop triggered by control box button - 1<<0
     * Emergency stop triggered by teach pendant button - 1<<1
     * Emergency stop triggered by handle button - 1<<2
     * Emergency stop triggered by fixed IO - 1<<3
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getRobotEmergencyStopSource","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int getRobotEmergencyStopSource();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取工具端力矩传感器的名字
     *
     * @return 当前工具端力矩传感器名字
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getSelectedTcpForceSensorName(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua函数原型
     * getSelectedTcpForceSensorName() -> str
     *
     * @par Lua示例
     * TcpForceSensorName = getSelectedTcpForceSensorName()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSelectedTcpForceSensorName","params":[],"id":1}
     * \endchinese
     * \english
     * Get the name of the selected TCP force sensor.
     *
     * @return The name of the currently selected TCP force sensor.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getSelectedTcpForceSensorName(self: pyaubo_sdk.RobotConfig) -> str
     *
     * @par Lua function prototype
     * getSelectedTcpForceSensorName() -> str
     *
     * @par Lua example
     * TcpForceSensorName = getSelectedTcpForceSensorName()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getSelectedTcpForceSensorName","params":[],"id":1}
     * \endenglish
     */
    std::string getSelectedTcpForceSensorName();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 添加焊枪动力学参数
     *
     * @param m 质量, 单位: kg
     * @param cog 质心, 单位: m, 形式为(CoGx, CoGy, CoGz)
     * @param inertia 惯性张量, 单位: kg*m^2, 形式为(Ixx, Iyy, Izz, Ixy,
     * Ixz, Iyz)或(Ixx, Ixy, Ixz, Iyx, Iyy, Iyz, Izx, Izy, Izz)
     * @return 成功返回0; 失败返回错误码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * attachWeldingGun(self: pyaubo_sdk.RobotConfig, arg0: float, arg1:
     * List[float], arg2: List[float]) -> int
     *
     * @par Lua函数原型
     * attachWeldingGun(m: number, cog: table, inertia: table) -> nil
     *
     * @par Lua示例
     * attachWeldingGun(3, {0,0,0}, {0,0,0,0,0,0,0,0,0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.attachWeldingGun","params":[3,[0,0,0],[0,0,0,0,0,0,0,0,0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int attachWeldingGun(double m, const std::vector<double> &cog,
                         const std::vector<double> &inertia);
    /**
     * @ingroup RobotConfig
     * \chinese
     * 设置碰撞阈值
     *
     * @param threshold 碰撞阈值
     * @return 成功返回0; 失败返回错误码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setCollisionThreshold(self: pyaubo_sdk.RobotConfig, arg0: List[float])
     * -> int
     *
     * @par Lua函数原型
     * setCollisionThreshold(threshold: table) -> nil
     *
     * @par Lua示例
     * setCollisionThreshold({99.0,
     * 114.0,
     * 103.0, 56.0, 51.0, 60.0,54.6111111, 66.22222222, 59.66666667, 28.94444444,
     * 27.05555556, 30.11111111,19.1, 28.0, 25.0, 7.3, 7.9, 6.2})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setCollisionThreshold","params":[[99.0,
     * 114.0,
     * 103.0, 56.0, 51.0, 60.0,54.6111111, 66.22222222, 59.66666667, 28.94444444,
     * 27.05555556, 30.11111111,19.1, 28.0, 25.0, 7.3, 7.9, 6.2]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Enable optimized collision force.
     *
     * @param threshold
     * @return Returns 0 on success; error code on failure.
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.setCollisionThreshold","params":[[99.0,
     * 114.0,
     * 103.0, 56.0, 51.0, 60.0,54.6111111, 66.22222222, 59.66666667, 28.94444444,
     * 27.05555556, 30.11111111,19.1, 28.0, 25.0, 7.3, 7.9, 6.2]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     * \endenglish
     */
    int setCollisionThreshold(const std::vector<double> &threshold);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取碰撞阈值
     *
     * @return 碰撞阈值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getCollisionThreshold(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * getCollisionThreshold() -> table
     *
     * @par Lua示例
     * CollisionThreshold = getCollisionThreshold()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getCollisionThreshold","params":[99.0,
     * 114.0, 103.0, 56.0, 51.0, 60.0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endchinese
     * \english
     * Get collision threshold.
     *
     * @return collision threshold.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getCollisionThreshold(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua function prototype
     * getCollisionThreshold() -> table
     *
     * @par Lua example
     * CollisionThreshold = getCollisionThreshold()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.getCollisionThreshold","params":[[99.0,
     * 114.0,
     * 103.0, 56.0, 51.0, 60.0,54.6111111, 66.22222222, 59.66666667, 28.94444444,
     * 27.05555556, 30.11111111,19.1, 28.0, 25.0, 7.3, 7.9, 6.2]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     * \endenglish
     */
    std::vector<double> getCollisionThreshold();

    int enableAxisGroup(const std::string &group_name);
    int disableAxisGroup();

    /**
     * @ingroup RobotConfig
     * \chinese
     * 使能末端碰撞检测
     *
     * @param enable 使能碰撞阈值
     * @return 成功返回0; 失败返回错误码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * enableEndCollisionCheck(self: pyaubo_sdk.RobotConfig, arg0: bool)
     * -> int
     *
     * @par Lua函数原型
     * enableEndCollisionCheck(threshold: table) -> nil
     *
     * @par Lua示例
     * enableEndCollisionCheck(true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.enableEndCollisionCheck","params":[true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set end collision threshold.
     *
     * @param threshold
     * @return Returns 0 on success; error code on failure.
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.enableEndCollisionCheck","params":[true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     * \endenglish
     */
    int enableEndCollisionCheck(bool enable);

    /**
     * @ingroup RobotConfig
     * \chinese
     * 获取末端碰撞检测是否使能
     *
     * @return 是否使能末端碰撞检测
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isEndCollisionCheckEnabled(self: pyaubo_sdk.RobotConfig) -> List[float]
     *
     * @par Lua函数原型
     * isEndCollisionCheckEnabled() -> table
     *
     * @par Lua示例
     * IsEndCollisionCheckEnabled = isEndCollisionCheckEnabled()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isEndCollisionCheckEnabled","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endchinese
     * \english
     * Get collision check is enabled.
     *
     * @return end collision threshold.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isEndCollisionCheckEnabled(self: pyaubo_sdk.RobotConfig) -> bool
     *
     * @par Lua function prototype
     * isEndCollisionCheckEnabled() -> bool
     *
     * @par Lua example
     * IsEndCollisionCheckEnabled = isEndCollisionCheckEnabled()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.isEndCollisionCheckEnabled","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endenglish
     */
    bool isEndCollisionCheckEnabled();

protected:
    void *d_;
};
using RobotConfigPtr = std::shared_ptr<RobotConfig>;

} // namespace common_interface
} // namespace arcs
#endif // AUBO_SDK_ROBOT_CONFIG_H
