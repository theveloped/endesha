/** @file  motion_control.h
 * \~chinese @brief 运动控制接口
 * \~english @brief Motion control interface
 */
#ifndef AUBO_SDK_MOTION_CONTROL_INTERFACE_H
#define AUBO_SDK_MOTION_CONTROL_INTERFACE_H

#include <vector>
#include <functional>
#include <thread>

#include <aubo/global_config.h>
#include <aubo/type_def.h>

namespace arcs {
namespace common_interface {

/**
 * \chinese
 *  pathBuffer类型
 *
 *  机器人运动被编程为位姿到位姿的运动，即从当前位置移动到新位置。两点之间的路径由机器人自动计算。
 * \endchinese
 * \english
 *
 *  pathBuffer Type
 *
 *  The robot movements are programmed as pose-to-pose movements, that is move
 *  from the current position to a new position. The path between these two
 *  positions is then automatically calculated by the robot.
 * \endenglish
 */

enum PathBufferType
{
    PathBuffer_TOPPRA = 1, ///< \~chinese 1: toppra 时间最优路径规划 \~english
                           ///< 1: toppra time optimal path planning
    PathBuffer_CubicSpline =
        2, ///< \~chinese 2: cubic_spline(录制的轨迹) \~english 2: cubic_spline
           ///< (recorded trajectory)

    /// \~chinese 3: 关节B样条插值，最少三个点 \~english 3: Joint B-spline
    /// interpolation, at least three points
    /// \~chinese 废弃，建议用5替代，现在实际是关节空间 CUBIC_SPLINE \~english
    /// Deprecated, use 5 instead, currently it is joint space CUBIC_SPLINE
    PathBuffer_JointSpline = 3,

    /// \~chinese 4:关节B样条插值，最少三个点，但是传入的是笛卡尔空间位姿
    /// \~english 4: Joint B-spline interpolation, at least three points, but
    /// the input is Cartesian space pose 废弃，建议用6替代，现在实际是关节空间
    /// CUBIC_SPLINE
    PathBuffer_JointSplineC = 4,

    ///< \~chinese 5: 关节B样条插值，最少三个点 \~english 5: Joint B-spline
    ///< interpolation, at least three points
    PathBuffer_JointBSpline = 5,

    /// \~chinese 6:关节B样条插值，最少三个点，但是传入的是笛卡尔空间位姿
    /// \~english 6: Joint B-spline interpolation, at least three points, but
    /// the input is Cartesian space pose
    PathBuffer_JointBSplineC = 6,
};

/**
 * @defgroup MotionControl MotionControl (运动规划与控制)
 * @ingroup RobotInterface
 *  MotionControl
 */
class ARCS_ABI_EXPORT MotionControl
{
public:
    MotionControl();
    virtual ~MotionControl();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取等效半径，单位 m
     * moveLine/moveCircle时，末端姿态旋转的角度等效到末端位置移动
     * 可以通过 setEqradius 设置，默认为1
     *
     * @return 返回等效半径
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getEqradius(self: pyaubo_sdk.MotionControl) -> float
     *
     * @par Lua函数原型
     * getEqradius() -> number
     *
     * @par Lua 示例
     * num = getEqradius()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getEqradius","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1.0}
     * \endchinese
     * \english
     * Get the equivalent radius, in meters.
     * When using moveLine/moveCircle, the rotation angle of the end effector's
     * pose is converted to an equivalent end position movement. Can be set via
     * setEqradius, default is 1.
     *
     * @return Returns the equivalent radius.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getEqradius(self: pyaubo_sdk.MotionControl) -> float
     *
     * @par Lua function prototype
     * getEqradius() -> number
     *
     * @par Lua example
     * num = getEqradius()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getEqradius","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1.0}
     * \endenglish
     */
    double getEqradius();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置等效半径，单位 m
     * moveLine/moveCircle时，末端姿态旋转的角度等效到末端位置移动，数值越大，姿态旋转速度越快
     *
     * @param eqradius 0表示只规划移动，姿态旋转跟随移动
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setEqradius","params":[0.8],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * @par Python函数原型
     * setEqradius(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua函数原型
     * setEqradius(eqradius: number) -> number
     *
     * @par Lua示例
     * num = setEqradius(1)
     *
     * \endchinese
     * \english
     * Set the equivalent radius, in meters.
     * When using moveLine/moveCircle, the rotation angle of the end effector's
     * pose is converted to an equivalent end position movement. The larger the
     * value, the faster the posture rotation speed.
     *
     * @param eqradius 0 means only plan the movement, and the posture rotation
     * follows the movement.
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setEqradius","params":[0.8],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * @par Python function prototype
     * setEqradius(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua function prototype
     * setEqradius(eqradius: number) -> number
     *
     * @par Lua example
     * num = setEqradius(1)
     *
     * \endenglish
     */
    int setEqradius(double eqradius);

    /**
     * @ingroup MotionControl
     * \chinese
     * 动态调整机器人运行速度和加速度比例 (0., 1.]
     *
     * @param fraction 机器人运行速度和加速度比例
     * @return 成功返回0; 失败返回错误码
     * AUBO_INVL_ARGUMENT
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setSpeedFraction(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua函数原型
     * setSpeedFraction(fraction: number) -> nil
     *
     * @par Lua示例
     * setSpeedFraction(0.5)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setSpeedFraction","params":[0.8],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Dynamically adjust the robot's speed and acceleration ratio (0., 1.]
     *
     * @param fraction The ratio of robot speed and acceleration
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_INVL_ARGUMENT
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setSpeedFraction(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua function prototype
     * setSpeedFraction(fraction: number) -> nil
     *
     * @par Lua example
     * setSpeedFraction(0.5)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setSpeedFraction","params":[0.8],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setSpeedFraction(double fraction);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取速度和加速度比例，默认为 1
     * 可以通过 setSpeedFraction 接口设置
     *
     * @return 返回速度和加速度比例
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getSpeedFraction(self: pyaubo_sdk.MotionControl) -> float
     *
     * @par Lua函数原型
     * getSpeedFraction() -> number
     *
     * @par Lua示例
     * num = getSpeedFraction()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getSpeedFraction","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1.0}
     * \endchinese
     * \english
     * Get the speed and acceleration ratio, default is 1.
     * Can be set via setSpeedFraction interface.
     *
     * @return Returns the speed and acceleration ratio.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getSpeedFraction(self: pyaubo_sdk.MotionControl) -> float
     *
     * @par Lua function prototype
     * getSpeedFraction() -> number
     *
     * @par Lua example
     * num = getSpeedFraction()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getSpeedFraction","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1.0}
     * \endenglish
     */
    double getSpeedFraction();

    /**
     * @ingroup MotionControl
     * \chinese
     * 速度比例设置临界区，使能之后速度比例被强制设定为1. ,
     * 失能之后恢复之前的速度比例
     *
     * @param enable
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * speedFractionCritical() -> bool
     *
     * @par Lua示例
     * speedFractionCritical(true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.speedFractionCritical","params":[true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Speed fraction critical section. When enabled, the speed fraction is
     * forced to 1. When disabled, the previous speed fraction is restored.
     *
     * @param enable
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * speedFractionCritical() -> nil
     *
     * @par Lua example
     * speedFractionCritical(true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.speedFractionCritical","params":[true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int speedFractionCritical(bool enable);

    /**
     * @ingroup MotionControl
     * \chinese
     * 是否处于速度比例设置临界区
     *
     * @return 处于速度比例设置临界区返回 true; 反之返回 false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * isSpeedFractionCritical() -> bool
     *
     * @par Lua示例
     * status = isSpeedFractionCritical()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isSpeedFractionCritical","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endchinese
     * \english
     * Whether it is in the speed fraction critical section
     *
     * @return Returns true if in the speed fraction critical section; otherwise
     * returns false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * isSpeedFractionCritical() -> bool
     *
     * @par Lua example
     * status = isSpeedFractionCritical()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isSpeedFractionCritical","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endenglish
     */
    bool isSpeedFractionCritical();

    /**
     * @ingroup MotionControl
     * \chinese
     * 是否处交融区
     *
     * @return 处交融区返回 true; 反之返回 false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * isBlending() -> bool
     *
     * @par Lua示例
     * status = isBlending()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isBlending","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     * \english
     * Whether it is in the blending area
     *
     * @return Returns true if in the blending area; otherwise returns false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * isBlending() -> bool
     *
     * @par Lua example
     * status = isBlending()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isBlending","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool isBlending();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置偏移的最大速度和最大加速度
     * 仅对pathOffsetSet中 type=1 有效
     * @param v 最大速度
     * @param a 最大加速度
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathOffsetLimits(self: pyaubo_sdk.MotionControl, arg0: float, arg1:
     * float) -> int
     *
     * @par Lua函数原型
     * pathOffsetLimits(v: number, a: number) -> nil
     *
     * @par Lua示例
     * pathOffsetLimits(1.5,2.5)
     *
     * \endchinese
     * \english
     * Set the maximum speed and maximum acceleration for offset.
     * Only valid when type=1 in pathOffsetSet.
     * @param v Maximum speed
     * @param a Maximum acceleration
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathOffsetLimits(self: pyaubo_sdk.MotionControl, arg0: float, arg1:
     * float) -> int
     *
     * @par Lua function prototype
     * pathOffsetLimits(v: number, a: number) -> nil
     *
     * @par Lua example
     * pathOffsetLimits(1.5,2.5)
     *
     * \endenglish
     */
    int pathOffsetLimits(double v, double a);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置偏移的参考坐标系
     * 仅对pathOffsetSet中 type=1 有效
     * @param ref_coord 参考坐标系 0-基坐标系 1-TCP
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathOffsetCoordinate(self: pyaubo_sdk.MotionControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * pathOffsetCoordinate(ref_coord: number) -> number
     *
     * @par Lua示例
     * num = pathOffsetCoordinate(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetCoordinate","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the reference coordinate system for offset.
     * Only valid when type=1 in pathOffsetSet.
     * @param ref_coord Reference coordinate system: 0-base coordinate, 1-TCP
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathOffsetCoordinate(self: pyaubo_sdk.MotionControl, arg0: int) -> float
     *
     * @par Lua function prototype
     * pathOffsetCoordinate(ref_coord: number) -> number
     *
     * @par Lua example
     * num = pathOffsetCoordinate(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetCoordinate","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int pathOffsetCoordinate(int ref_coord);

    /**
     * @ingroup MotionControl
     * \chinese
     * 路径偏移使能
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathOffsetEnable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * pathOffsetEnable() -> number
     *
     * @par Lua示例
     * num = pathOffsetEnable()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetEnable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Enable path offset
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathOffsetEnable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * pathOffsetEnable() -> number
     *
     * @par Lua example
     * num = pathOffsetEnable()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetEnable","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int pathOffsetEnable();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置路径偏移
     *
     * @param offset 在各方向的位姿偏移
     * @param type 运动类型 0-位置规划 1-速度规划
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathOffsetSet(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * int) -> int
     *
     * @par Lua函数原型
     * pathOffsetSet(offset: table, type: number) -> nil
     *
     * @par Lua 示例
     * pathOffsetSet({ 0, 0, 0.1, 0, 0, 0 }, 0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetSet","params":[[0,0,0.01,0,0,0],0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set path offset
     *
     * @param offset Pose offset in each direction
     * @param type Motion type 0-position planning 1-velocity planning
     * @return Returns 0 on success; otherwise returns error code
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathOffsetSet(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * int) -> int
     *
     * @par Lua function prototype
     * pathOffsetSet(offset: table, type: number) -> nil
     *
     * @par Lua example
     * pathOffsetSet({ 0, 0, 0.1, 0, 0, 0 }, 0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetSet","params":[[0,0,0.01,0,0,0],0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int pathOffsetSet(const std::vector<double> &offset, int type = 0);

    /**
     * @ingroup MotionControl
     * \chinese
     * 路径偏移失能
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathOffsetDisable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * pathOffsetDisable() -> nil
     *
     * @par Lua示例
     * pathOffsetDisable()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetDisable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Disable path offset
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathOffsetDisable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * pathOffsetDisable() -> nil
     *
     * @par Lua example
     * pathOffsetDisable()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathOffsetDisable","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int pathOffsetDisable();

    /**
     * @ingroup MotionControl
     * \chinese
     * @brief 监控轨迹偏移范围
     * @param min: 沿坐标轴负方向最大偏移量
     * @param max: 沿坐标轴正方向最大偏移量
     * @param strategy: 达到最大偏移量后监控策略
     * 　　　　0-禁用监控
     * 　　　　1-饱和限制，即维持最大姿态
     * 　　　　2-保护停止
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathOffsetSupv(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * List[float], arg2: int) -> int
     *
     * @par Lua函数原型
     * pathOffsetSupv(min: table, max: table, strategy: number) -> number
     *
     * @par Lua示例
     * num = pathOffsetSupv({0,0,-0.2,0,0,0},{0,0,0.5,0,0,0},0)
     *
     * \endchinese
     * \english
     * @brief Monitor trajectory offset range
     * @param min: Maximum offset in the negative direction of the coordinate
     * axis
     * @param max: Maximum offset in the positive direction of the coordinate
     * axis
     * @param strategy: Monitoring strategy after reaching the maximum offset
     * 　　　　0 - Disable monitoring
     * 　　　　1 - Saturation limit, i.e., maintain maximum pose
     * 　　　　2 - Protective stop
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathOffsetSupv(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * List[float], arg2: int) -> int
     *
     * @par Lua function prototype
     * pathOffsetSupv(min: table, max: table, strategy: number) -> number
     *
     * @par Lua example
     * num = pathOffsetSupv({0,0,-0.2,0,0,0},{0,0,0.5,0,0,0},0)
     *
     * \endenglish
     */
    int pathOffsetSupv(const std::vector<double> &min,
                       const std::vector<double> &max, int strategy);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节偏移使能
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * jointOffsetEnable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * jointOffsetEnable() -> nil
     *
     * @par Lua示例
     * jointOffsetEnable()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.jointOffsetEnable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Enable joint offset
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * jointOffsetEnable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * jointOffsetEnable() -> nil
     *
     * @par Lua example
     * jointOffsetEnable()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.jointOffsetEnable","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int jointOffsetEnable();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置关节偏移
     *
     * @param offset 在各关节的位姿偏移
     * @param type
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * jointOffsetSet(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * int) -> int
     *
     * @par Lua函数原型
     * jointOffsetSet(offset: table, type: number) -> nil
     *
     * @par Lua示例
     * jointOffsetSet({0.1,0,0,0,0,0},1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.jointOffsetSet","params":[[0.1,0,0,0,0],1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set joint offset
     *
     * @param offset Pose offset for each joint
     * @param type
     * @return Returns 0 on success; otherwise returns error code
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * jointOffsetSet(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * int) -> int
     *
     * @par Lua function prototype
     * jointOffsetSet(offset: table, type: number) -> nil
     *
     * @par Lua example
     * jointOffsetSet({0.1,0,0,0,0,0},1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.jointOffsetSet","params":[[0.1,0,0,0,0],1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int jointOffsetSet(const std::vector<double> &offset, int type = 1);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节偏移失能
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * jointOffsetDisable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * jointOffsetDisable() -> nil
     *
     * @par Lua示例
     * jointOffsetDisable()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.jointOffsetDisable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Disable joint offset
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * jointOffsetDisable(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * jointOffsetDisable() -> nil
     *
     * @par Lua example
     * jointOffsetDisable()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.jointOffsetDisable","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int jointOffsetDisable();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取已经入队的指令段(INST)数量，运动指令包括
     * moveJoint/moveLine/moveCircle 等运动指令以及 setPayload 等配置指令
     *
     * 指令一般会在接口宏定义里面用 _INST 指示, 比如 moveJoint
     *   _INST(MotionControl, 5, moveJoint, q, a, v, blend_radius, duration)
     *
     * @return 已经入队的指令段数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getQueueSize(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * getQueueSize() -> number
     *
     * @par Lua示例
     * num = getQueueSize()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getQueueSize","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the number of enqueued instruction segments (INST), including motion
     * instructions such as moveJoint/moveLine/moveCircle and configuration
     * instructions such as setPayload.
     *
     * Instructions are generally indicated with _INST in macro definitions, for
     * example: _INST(MotionControl, 5, moveJoint, q, a, v, blend_radius,
     * duration)
     *
     * @return The number of enqueued instruction segments.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getQueueSize(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * getQueueSize() -> number
     *
     * @par Lua example
     * num = getQueueSize()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getQueueSize","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getQueueSize();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取已经入队的运动规划插补点数量
     *
     * @return 已经入队的运动规划插补点数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getTrajectoryQueueSize(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * getTrajectoryQueueSize() -> number
     *
     * @par Lua示例
     * num = getTrajectoryQueueSize()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getTrajectoryQueueSize","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Get the number of enqueued motion planning interpolation points
     *
     * @return The number of enqueued motion planning interpolation points
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getTrajectoryQueueSize(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * getTrajectoryQueueSize() -> number
     *
     * @par Lua example
     * num = getTrajectoryQueueSize()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getTrajectoryQueueSize","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int getTrajectoryQueueSize();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取当前正在插补的运动指令段的ID
     *
     * @return 当前正在插补的运动指令段的ID
     * @retval -1 表示轨迹队列为空 \n
     * 像movePathBuffer运动中的buffer或者规划器(moveJoint和moveLine等)里的队列都属于轨迹队列
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getExecId(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * getExecId() -> number
     *
     * @par Lua示例
     * num = getExecId()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getExecId","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endchinese
     * \english
     * Get the ID of the currently interpolating motion instruction segment.
     *
     * @return The ID of the currently interpolating motion instruction segment.
     * @retval -1 Indicates the trajectory queue is empty. \n
     * Both the buffer in movePathBuffer motion and the queue in the planner
     * (such as moveJoint and moveLine) belong to the trajectory queue.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getExecId(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * getExecId() -> number
     *
     * @par Lua example
     * num = getExecId()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getExecId","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endenglish
     */
    int getExecId();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取指定ID的运动指令段的预期执行时间
     *
     * @param id 运动指令段ID
     * @return 返回预期执行时间
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDuration(self: pyaubo_sdk.MotionControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getDuration(id: number) -> number
     *
     * @par Lua示例
     * num = getDuration(16)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getDuration","params":[16],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     * Get the expected execution duration of the motion segment with the
     * specified ID.
     *
     * @param id Motion segment ID
     * @return Returns the expected execution duration
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getDuration(self: pyaubo_sdk.MotionControl, arg0: int) -> float
     *
     * @par Lua function prototype
     * getDuration(id: number) -> number
     *
     * @par Lua example
     * num = getDuration(16)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getDuration","params":[16],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getDuration(int id);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取指定ID的运动指令段的剩余执行时间
     *
     * @param id 运动指令段ID
     * @return 返回剩余执行时间
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getMotionLeftTime(self: pyaubo_sdk.MotionControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getMotionLeftTime(id: number) -> number
     *
     * @par Lua示例
     * num = getMotionLeftTime(16)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getMotionLeftTime","params":[16],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endchinese
     * \english
     * Get the remaining execution time of the motion segment with the specified
     * ID.
     *
     * @param id Motion segment ID
     * @return Returns the remaining execution time
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getMotionLeftTime(self: pyaubo_sdk.MotionControl, arg0: int) -> float
     *
     * @par Lua function prototype
     * getMotionLeftTime(id: number) -> number
     *
     * @par Lua example
     * num = getMotionLeftTime(16)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getMotionLeftTime","params":[16],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endenglish
     */
    double getMotionLeftTime(int id);

    /**
     * @ingroup MotionControl
     * \chinese
     * StopMove 用于临时停止机器人和外部轴的运动以及相关工艺进程。如果调用
     * StartMove 指令，则运动和工艺进程将恢复。
     *
     * 该指令可用于中断处理程序中，在发生中断时临时停止机器人。
     *
     * @param quick true: 以最快速度在路径上停止机器人。未指定 quick
     * 参数时，机器人将在路径上停止，但制动距离较长（与普通程序停止相同）。
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * StopMove(quick: bool,all_tasks: bool) -> number
     *
     * @par Lua示例
     * num = StopMove(true,true)
     *
     * \endchinese
     * \english
     * StopMove is used to stop robot and external axes movements and any
     * belonging process temporarily. If the instruction StartMove is given then
     * the movement and process resumes.
     *
     * This instruction can, for example, be used in a trap routine to stop the
     * robot temporarily when an interrupt occurs.
     *
     * @param quick true: Stops the robot on the path as fast as possible.
     * Without the optional parameter \Quick, the robot stops on the path, but
     * the braking distance is longer (same as for normal Program Stop).
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * StopMove(quick: bool,all_tasks: bool) -> number
     *
     * @par Lua example
     * num = StopMove(true,true)
     *
     * \endenglish
     */
    int stopMove(bool quick, bool all_tasks);

    /**
     * @ingroup MotionControl
     * \chinese
     * StartMove 用于在以下情况下恢复机器人、外部轴的运动以及相关工艺进程：
     * • 通过 StopMove 指令停止后。
     * • 执行 StorePath ... RestoPath 序列后。
     * • 发生异步运动错误（如 ERR_PATH_STOP）或特定工艺错误并在 ERROR
     * 处理器中处理后。
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * startMove() -> number
     *
     * @par Lua示例
     * num = startMove()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.startMove","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * StartMove is used to resume robot, external axes movement and belonging
     * process after the movement has been stopped
     *
     * • by the instruction StopMove.
     * • after execution of StorePath ... RestoPath sequence.
     * • after asynchronously raised movements errors, such as ERR_PATH_STOP or
     * specific process error after handling in the ERROR handler.
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * startMove() -> number
     *
     * @par Lua example
     * num = startMove()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.startMove","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int startMove();

    /**
     * @ingroup MotionControl
     * \chinese
     * storePath
     *
     * @param keep_sync
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * storePath(keep_sync: bool) -> number
     *
     * @par Lua示例
     * num = storePath()
     *
     * \endchinese
     * \english
     * storePath
     *
     * @param keep_sync
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * storePath(keep_sync: bool) -> number
     *
     * @par Lua example
     * num = storePath()
     *
     * \endenglish
     */
    int storePath(bool keep_sync);

    /**
     * @ingroup MotionControl
     * \chinese
     * ClearPath (清除路径) 清除当前运动路径层级（基础层级或 StorePath
     * 层级）上的所有运动路径。
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * clearPath() -> number
     *
     * @par Lua示例
     * num = clearPath()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.clearPath","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * ClearPath clears the whole motion path on the current motion path level
     * (base level or StorePath level).
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * clearPath() -> number
     *
     * @par Lua example
     * num = clearPath()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.clearPath","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int clearPath();

    /**
     * @ingroup MotionControl
     * \chinese
     * restoPath
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * restoPath() -> number
     *
     * @par Lua示例
     * num = restoPath()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.restoPath","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * restoPath
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * restoPath() -> number
     *
     * @par Lua example
     * num restoPath()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.restoPath","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int restoPath();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取当前运动指令段的执行进度
     *
     * @return 返回执行进度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getProgress(self: pyaubo_sdk.MotionControl) -> float
     *
     * @par Lua函数原型
     * getProgress() -> number
     *
     * @par Lua示例
     * num = getProgress()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getProgress","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     * Get the execution progress of the current motion instruction segment.
     *
     * @return Returns the execution progress.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getProgress(self: pyaubo_sdk.MotionControl) -> float
     *
     * @par Lua function prototype
     * getProgress() -> number
     *
     * @par Lua example
     * num = getProgress()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getProgress","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getProgress();

    /**
     * @ingroup MotionControl
     * \chinese
     * 当工件安装在另外一台机器人的末端或者外部轴上时，指定其名字和安装位置
     *
     * @note 暂未实现
     *
     * @param module_name 控制模块名字
     * @param mounting_pose 抓取的相对位置，
     * 如果是机器人，则相对于机器人末端中心点（非TCP点）
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setWorkObjectHold(self: pyaubo_sdk.MotionControl, arg0: str, arg1:
     * List[float]) -> int
     *
     * @par Lua函数原型
     * setWorkObjectHold(module_name: string, mounting_pose: table) -> nil
     *
     * @par Lua示例
     * setWorkObjectHold("object",{0.2,0.1,-0.4,3.14,0,-1.57})
     *
     * \endchinese
     * \english
     * Specify the name and mounting position when the workpiece is installed on
     * the end of another robot or external axis.
     *
     * @note Not implemented yet
     *
     * @param module_name Name of the control module
     * @param mounting_pose Relative position of the grasp,
     * if it is a robot, it is relative to the robot's end center point (not the
     * TCP point)
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setWorkObjectHold(self: pyaubo_sdk.MotionControl, arg0: str, arg1:
     * List[float]) -> int
     *
     * @par Lua function prototype
     * setWorkObjectHold(module_name: string, mounting_pose: table) -> nil
     *
     * @par Lua example
     * setWorkObjectHold("object",{0.2,0.1,-0.4,3.14,0,-1.57})
     *
     * \endenglish
     */
    int setWorkObjectHold(const std::string &module_name,
                          const std::vector<double> &mounting_pose);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取工件安装信息
     *
     * @note 暂未实现
     *
     * @return 返回一个包含控制模块名字和安装位姿的元组
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getWorkObjectHold(self: pyaubo_sdk.MotionControl) -> Tuple[str,
     * List[float]]
     *
     * @par Lua函数原型
     * getWorkObjectHold() -> table
     *
     * @par Lua示例
     * Object_table = getWorkObjectHold()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getWorkObjectHold","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":["",[]]}
     * \endchinese
     * \english
     * getWorkObjectHold
     *
     * @note Not implemented yet
     *
     * @return Returns a tuple containing the control module name and mounting
     * pose
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getWorkObjectHold(self: pyaubo_sdk.MotionControl) -> Tuple[str,
     * List[float]]
     *
     * @par Lua function prototype
     * getWorkObjectHold() -> table
     *
     * @par Lua example
     * Object_table = getWorkObjectHold()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getWorkObjectHold","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":["",[]]}
     * \endenglish
     */
    std::tuple<std::string, std::vector<double>> getWorkObjectHold();

    /**
     * @ingroup MotionControl
     * \chinese
     * @note 获取暂停点关节位置
     *
     * 常用于运行工程时发生碰撞后继续运动过程中(先通过resumeMoveJoint或resumeMoveLine运动到暂停位置,再恢复工程)
     *
     * @return 暂停关节位置
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getPauseJointPositions(self: pyaubo_sdk.MotionControl) -> List[float]
     *
     * @par Lua函数原型
     * getPauseJointPositions() -> table
     *
     * @par Lua示例
     * JointPositions = getPauseJointPositions()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getPauseJointPositions","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[8.2321e-13,-0.200999,1.33999,0.334999,1.206,-6.39383e-12]}
     * \endchinese
     * \english
     * @note Get the joint positions at the pause point.
     *
     * Commonly used during process recovery after a collision occurs (first
     * move to the pause position using resumeMoveJoint or resumeMoveLine, then
     * resume the process).
     *
     * @return Pause joint positions
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getPauseJointPositions(self: pyaubo_sdk.MotionControl) -> List[float]
     *
     * @par Lua function prototype
     * getPauseJointPositions() -> table
     *
     * @par Lua example
     * JointPositions = getPauseJointPositions()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getPauseJointPositions","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[8.2321e-13,-0.200999,1.33999,0.334999,1.206,-6.39383e-12]}
     * \endenglish
     */
    std::vector<double> getPauseJointPositions();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置继续运动参数
     *
     * @param q 继续运动起始位置
     * @param move_type 0:关节空间 1：笛卡尔空间
     * @param blend_radius 交融半径
     * @param qdmax 关节运动最大速度(6维度数据)
     * @param qddmax 关节运动最大加速度(6维度数据)
     * @param vmax 直线运动最大线速度,角速度(2维度数据)
     * @param amax 直线运动最大线加速度，角加速度(2维度数据)
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setResumeStartPoint(self: pyaubo_sdk.MotionControl,
     * arg0：List[float],arg1: int， arg2: float，arg3: List[float], arg4:
     * List[float],arg5:float,arg5:float) -> int
     *
     * @par Lua函数原型
     * setResumeStartPoint(q : table, move_type: number,blend_radius:
     * number, qdmax: table, qddmax:
     * table,vmax:number,amax:number) -> nilr
     *
     * @par Lua示例
     * setResumeStartPoint({0,0,0,0,0,0},1,1,{0,0,0,0,0,0},{0,0,0,0,0,0},{1,1},{1,1})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setResumeStartPoint","params":[[0,0,0,0,0,0],1,1,[0,0,0,0,0,0],[0,0,0,0,0,0],1,1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set resume motion parameters
     *
     * @param q Resume start position
     * @param move_type 0: Joint space, 1: Cartesian space
     * @param blend_radius Blend radius
     * @param qdmax Maximum joint speed (6 elements)
     * @param qddmax Maximum joint acceleration (6 elements)
     * @param vmax Maximum linear and angular speed for linear motion (2
     * elements)
     * @param amax Maximum linear and angular acceleration for linear motion (2
     * elements)
     * @return Returns 0 on success; otherwise returns error code
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setResumeStartPoint(self: pyaubo_sdk.MotionControl,
     * arg0: List[float], arg1: int, arg2: float, arg3: List[float], arg4:
     * List[float], arg5: float, arg6: float) -> int
     *
     * @par Lua function prototype
     * setResumeStartPoint(q: table, move_type: number, blend_radius:
     * number, qdmax: table, qddmax:
     * table, vmax: number, amax: number) -> nil
     *
     * @par Lua example
     * setResumeStartPoint({0,0,0,0,0,0},1,1,{0,0,0,0,0,0},{0,0,0,0,0,0},{1,1},{1,1})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setResumeStartPoint","params":[[0,0,0,0,0,0],1,1,[0,0,0,0,0,0],[0,0,0,0,0,0],1,1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setResumeStartPoint(const std::vector<double> &q, int move_type,
                            double blend_radius,
                            const std::vector<double> &qdmax,
                            const std::vector<double> &qddmax,
                            const std::vector<double> &vmax,
                            const std::vector<double> &amax);
    /**
     * @ingroup MotionControl
     * \chinese
     * 获取继续运动模式
     *
     * @return 0:继续运动起始点为暂停点 1:继续运动起始点为指定点
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getResumeMode(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * getResumeMode() -> int
     *
     * @par Lua示例
     * num = getResumeMode()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getResumeMode","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Get resume motion mode
     *
     * @return 0: Resume start point is the pause point; 1: Resume start point
     * is the specified point
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getResumeMode(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * getResumeMode() -> int
     *
     * @par Lua example
     * num = getResumeMode()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getResumeMode","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    int getResumeMode();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置伺服模式
     * 使用 setServoModeSelect 替代
     *
     * @param enable 是否使能
     * @return 成功返回0; 失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setServoMode(self: pyaubo_sdk.MotionControl, arg0: bool) -> int
     *
     * @par Lua函数原型
     * setServoMode(enable: boolean) -> nil
     *
     * @par Lua示例
     * setServoMode(true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setServoMode","params":[true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set servo mode
     * Use setServoModeSelect instead
     *
     * @param enable Whether to enable
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setServoMode(self: pyaubo_sdk.MotionControl, arg0: bool) -> int
     *
     * @par Lua function prototype
     * setServoMode(enable: boolean) -> nil
     *
     * @par Lua example
     * setServoMode(true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setServoMode","params":[true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    ARCS_DEPRECATED int setServoMode(bool enable);

    /**
     * @ingroup MotionControl
     * \chinese
     * 判断伺服模式是否使能
     * 使用 getServoModeSelect 替代
     *
     * @return 已使能返回true，反之则返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isServoModeEnabled(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua函数原型
     * isServoModeEnabled() -> boolean
     *
     * @par Lua示例
     * Servo_status = isServoModeEnabled()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isServoModeEnabled","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Determine whether the servo mode is enabled.
     * Use getServoModeSelect instead.
     *
     * @return Returns true if enabled, otherwise returns false.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isServoModeEnabled(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua function prototype
     * isServoModeEnabled() -> boolean
     *
     * @par Lua example
     * Servo_status = isServoModeEnabled()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isServoModeEnabled","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    ARCS_DEPRECATED bool isServoModeEnabled();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置伺服运动模式
     *
     * @param mode
     * 0-退出伺服模式
     * 1-(截断式)规划伺服模式
     * 2-透传模式(直接下发)
     * 3-透传模式(缓存)
     * 4-1ms透传模式(缓存)
     * 5-规划伺服模式
     * 6-(截断式)规划伺服模式, 可以叠加力控
     * 7-规划伺服模式，可以叠加力控
     * 伺服模式1添加路点后，会实时调整目标点和规划路线(当前的目标点被更新后，不能保证达到之前设定的目标点)
     * 伺服模式5添加路点后，能保证经过所有目标点
     * @return
     *
     * @par Lua函数原型
     * setServoModeSelect(0) -> nil
     *
     * @par Lua示例
     * setServoModeSelect(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setServoModeSelect","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set servo motion mode
     *
     * @param mode
     * 0 - Exit servo mode
     * 1 - Planning servo mode
     * 2 - Transparent mode (direct send)
     * 3 - Transparent mode (buffered)
     * @return
     *
     * @par Lua function prototype
     * setServoModeSelect(0) -> nil
     *
     * @par Lua example
     * setServoModeSelect(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setServoModeSelect","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setServoModeSelect(int mode);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取伺服运动模式
     *
     * @return
     *
     * @par Lua函数原型
     * getServoModeSelect() -> number
     *
     * @par Lua示例
     * num = getServoModeSelect()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getServoModeSelect","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the servo motion mode
     *
     * @return
     *
     * @par Lua function prototype
     * getServoModeSelect() -> number
     *
     * @par Lua example
     * num = getServoModeSelect()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getServoModeSelect","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getServoModeSelect();

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节空间伺服
     *
     * 目前可用参数只有 q 和 t;
     * @param q 关节角, 单位 rad,
     * @param a 加速度, 单位 rad/s^2,
     * @param v 速度，单位 rad/s,
     * @param t 运行时间，单位 s \n
     * t 值越大,机器臂运动越慢,反之，运动越快;
     * 该参数最优值为连续调用 servoJoint 接口的间隔时间。
     * @param lookahead_time 前瞻时间，单位 s \n
     * 指定机器臂开始减速前要运动的时长，用前瞻时间来平滑轨迹[0.03, 0.2],
     * 当 lookahead_time 小于一个控制周期时，越小则超调量越大,
     * 该参数最优值为一个控制周期。
     * @param gain 比例增益
     * 跟踪目标位置的比例增益[100, 200],
     * 用于控制运动的顺滑性和精度,
     * 比例增益越大，到达目标位置的时间越长，超调量越小。
     *
     * @retval 0 成功
     * @retval AUBO_BAD_STATE(1) 当前安全模式处于非
     * Normal、ReducedMode、Recovery 状态
     * @retval AUBO_QUEUE_FULL(2) 规划队列已满
     * @retval AUBO_BUSY(3) 上一条指令正在执行中
     * @retval -AUBO_BAD_STATE(-1)
     * 可能的原因包括但不限于：线程已分离、线程被终止、task_id
     * 未找到，或者当前机器人模式非 Running
     * @retval -AUBO_TIMEOUT(-4) 调用接口超时
     * @retval -AUBO_INVL_ARGUMENT(-5) 轨迹位置超限或速度超限
     * @retval -AUBO_REQUEST_IGNORE(-13) 当前处于非 servo 模式
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * servoJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float, arg4: float, arg5: float) -> int
     *
     * @par Lua函数原型
     * servoJoint(q: table, a: number, v: number, t: number, lookahead_time:
     * number, gain: number) -> nil
     *
     * @par Lua示例
     * servoJoint({0,0,0,0,0,0},0,0,10,0,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.servoJoint","params":[[0,0,0,0,0,0],0,0,10,0,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-13}
     *
     * \endchinese
     * \english
     * Joint space servo
     *
     * Currently only q and t parameters are available;
     * @param q Joint angles, unit: rad
     * @param a Acceleration, unit: rad/s^2
     * @param v Velocity, unit: rad/s
     * @param t Execution time, unit: s \n
     * The larger the t value, the slower the robot moves, and vice versa;
     * The optimal value for this parameter is the interval time for continuous
     * calls to the servoJoint interface.
     * @param lookahead_time Lookahead time, unit: s \n
     * Specifies the duration to move before the robot starts to decelerate,
     * used to smooth the trajectory [0.03, 0.2]. When lookahead_time is less
     * than one control cycle, the smaller it is, the greater the overshoot. The
     * optimal value for this parameter is one control cycle.
     * @param gain Proportional gain
     * Proportional gain for tracking the target position [100, 200],
     * used to control the smoothness and accuracy of the motion.
     * The larger the proportional gain, the longer it takes to reach the target
     * position, and the smaller the overshoot.
     *
     * @retval 0 Success
     * @retval AUBO_BAD_STATE(1) The current safety mode is not Normal,
     * ReducedMode, or Recovery
     * @retval AUBO_QUEUE_FULL(2) Planning queue is full
     * @retval AUBO_BUSY(3) The previous instruction is being executed
     * @retval -AUBO_BAD_STATE(-1)
     * Possible reasons include but are not limited to: thread has been
     * detached, thread terminated, task_id not found, or the current robot mode
     * is not Running
     * @retval -AUBO_TIMEOUT(-4) Interface call timeout
     * @retval -AUBO_INVL_ARGUMENT(-5) Trajectory position or velocity out of
     * range
     * @retval -AUBO_REQUEST_IGNORE(-13) Not in servo mode
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * servoJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float, arg4: float, arg5: float) -> int
     *
     * @par Lua function prototype
     * servoJoint(q: table, a: number, v: number, t: number, lookahead_time:
     * number, gain: number) -> nil
     *
     * @par Lua example
     * servoJoint({0,0,0,0,0,0},0,0,10,0,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.servoJoint","params":[[0,0,0,0,0,0],0,0,10,0,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-13}
     *
     * \endenglish
     */
    int servoJoint(const std::vector<double> &q, double a, double v, double t,
                   double lookahead_time, double gain);

    /**
     * @ingroup MotionControl
     * \chinese
     * 笛卡尔空间伺服
     *
     * 目前可用参数只有 pose 和 t;
     * @param pose 位姿, 单位 m,
     * @param a 加速度, 单位 m/s^2,
     * @param v 速度，单位 m/s,
     * @param t 运行时间，单位 s \n
     * t 值越大,机器臂运动越慢,反之，运动越快;
     * 该参数最优值为连续调用 servoCartesian 接口的间隔时间。
     * @param lookahead_time 前瞻时间，单位 s \n
     * 指定机器臂开始减速前要运动的时长，用前瞻时间来平滑轨迹[0.03, 0.2],
     * 当 lookahead_time 小于一个控制周期时，越小则超调量越大,
     * 该参数最优值为一个控制周期。
     * @param gain 比例增益
     * 跟踪目标位置的比例增益[100, 200],
     * 用于控制运动的顺滑性和精度,
     * 比例增益越大，到达目标位置的时间越长，超调量越小。
     *
     * @retval 0 成功
     * @retval AUBO_BAD_STATE(1) 当前安全模式处于非
     * Normal、ReducedMode、Recovery 状态
     * @retval AUBO_QUEUE_FULL(2) 规划队列已满
     * @retval AUBO_BUSY(3) 上一条指令正在执行中
     * @retval -AUBO_BAD_STATE(-1)
     * 可能的原因包括但不限于：线程已分离、线程被终止、task_id
     * 未找到，或者当前机器人模式非 Running
     * @retval -AUBO_TIMEOUT(-4) 调用接口超时
     * @retval -AUBO_INVL_ARGUMENT(-5) 轨迹位置超限或速度超限
     * @retval -AUBO_REQUEST_IGNORE(-13) 当前处于非 servo 模式
     * @retval -AUBO_IK_NO_CONVERGE(-23) 逆解计算不收敛，计算出错;
     * @retval -AUBO_IK_OUT_OF_RANGE(-24) 逆解计算超出机器人最大限制;
     * @retval AUBO_IK_CONFIG_DISMATCH(-25) 逆解输入配置存在错误;
     * @retval -AUBO_IK_JACOBIAN_FAILED(-26) 逆解雅可比矩阵计算失败;
     * @retval -AUBO_IK_NO_SOLU(-27) 目标点存在解析解，但均不满足选解条件;
     * @retval -AUBO_IK_UNKOWN_ERROR(-28) 逆解返回未知类型错误;
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * servoCartesian(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float, arg4: float, arg5: float) -> int
     *
     * @par Lua函数原型
     * servoCartesian(pose: table, a: number, v: number, t: number,
     * lookahead_time: number, gain: number) -> nil
     *
     * @par Lua示例
     * servoCartesian({0.58712,-0.15775,0.48703,2.76,0.344,1.432},0,0,10,0,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.servoCartesian","params":[[0.58712,-0.15775,0.48703,2.76,0.344,1.432],0,0,10,0,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-13}
     * \endchinese
     * \english
     * Cartesian space servo
     *
     * Currently, only pose and t parameters are available;
     * @param pose Pose, unit: m
     * @param a Acceleration, unit: m/s^2
     * @param v Velocity, unit: m/s
     * @param t Execution time, unit: s \n
     * The larger the t value, the slower the robot moves, and vice versa;
     * The optimal value for this parameter is the interval time for continuous
     * calls to the servoCartesian interface.
     * @param lookahead_time Lookahead time, unit: s \n
     * Specifies the duration to move before the robot starts to decelerate,
     * used to smooth the trajectory [0.03, 0.2]. When lookahead_time is less
     * than one control cycle, the smaller it is, the greater the overshoot. The
     * optimal value for this parameter is one control cycle.
     * @param gain Proportional gain
     * Proportional gain for tracking the target position [100, 200],
     * used to control the smoothness and accuracy of the motion,
     * The larger the proportional gain, the longer it takes to reach the target
     * position, and the smaller the overshoot.
     *
     * @retval 0 Success
     * @retval AUBO_BAD_STATE(1) The current safety mode is not Normal,
     * ReducedMode, or Recovery
     * @retval AUBO_QUEUE_FULL(2) Planning queue is full
     * @retval AUBO_BUSY(3) The previous instruction is being executed
     * @retval -AUBO_BAD_STATE(-1)
     * Possible reasons include but are not limited to: thread has been
     * detached, thread terminated, task_id not found, or the current robot mode
     * is not Running
     * @retval -AUBO_TIMEOUT(-4) Interface call timeout
     * @retval -AUBO_INVL_ARGUMENT(-5) Trajectory position or velocity out of
     * range
     * @retval -AUBO_REQUEST_IGNORE(-13) Not in servo mode
     * @retval -AUBO_IK_NO_CONVERGE(-23) Inverse kinematics calculation does not
     * converge, calculation error;
     * @retval -AUBO_IK_OUT_OF_RANGE(-24) Inverse kinematics calculation exceeds
     * robot maximum limits;
     * @retval AUBO_IK_CONFIG_DISMATCH(-25) Inverse kinematics input
     * configuration error;
     * @retval -AUBO_IK_JACOBIAN_FAILED(-26) Inverse kinematics Jacobian
     * calculation failed;
     * @retval -AUBO_IK_NO_SOLU(-27) Analytical solution exists for the target
     * point, but none meet the selection criteria;
     * @retval -AUBO_IK_UNKOWN_ERROR(-28) Inverse kinematics returned an unknown
     * error type;
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * servoCartesian(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float, arg4: float, arg5: float) -> int
     *
     * @par Lua function prototype
     * servoCartesian(pose: table, a: number, v: number, t: number,
     * lookahead_time: number, gain: number) -> nil
     *
     * @par Lua example
     * servoCartesian({0.58712,-0.15775,0.48703,2.76,0.344,1.432},0,0,10,0,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.servoCartesian","params":[[0.58712,-0.15775,0.48703,2.76,0.344,1.432],0,0,10,0,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-13}
     * \endenglish
     */
    int servoCartesian(const std::vector<double> &pose, double a, double v,
                       double t, double lookahead_time, double gain);

    /**
     * @ingroup MotionControl
     * \chinese
     * 伺服运动（带外部轴），用于执行离线轨迹、透传用户规划轨迹等
     *
     * @param q
     * @param extq
     * @param t
     * @param smooth_scale
     * @param delay_sacle
     * @return
     * \endchinese
     * \english
     * Servo motion (with external axes), used for executing offline
     * trajectories, pass-through user planned trajectories, etc.
     *
     * @param q
     * @param extq
     * @param t
     * @param smooth_scale
     * @param delay_sacle
     * @return
     * \endenglish
     */
    int servoJointWithAxes(const std::vector<double> &q,
                           const std::vector<double> &extq, double a, double v,
                           double t, double lookahead_time, double gain);

    int servoJointWithAxisGroup(const std::vector<double> &q, double a,
                                double v, double t, double lookahead_time,
                                double gain, const std::string &group_name,
                                const std::vector<double> &extq);

    /**
     * @ingroup MotionControl
     * \chinese
     * 伺服运动（带外部轴），用于执行离线轨迹、透传用户规划轨迹等
     * 与 servoJointWithAxes 区别在于接收笛卡尔空间位姿而不是关节角度
     * (由软件内部直接做逆解)
     *
     * @param pose
     * @param extq
     * @param t
     * @param smooth_scale
     * @param delay_sacle
     * @return
     * \endchinese
     * \english
     * Servo motion (with external axes), used for executing offline
     * trajectories, pass-through user planned trajectories, etc. The difference
     * from servoJointWithAxes is that it receives Cartesian poses instead of
     * joint angles (inverse kinematics is performed internally by the
     * software).
     *
     * @param pose
     * @param extq
     * @param t
     * @param smooth_scale
     * @param delay_sacle
     * @return
     * \endenglish
     */
    int servoCartesianWithAxes(const std::vector<double> &pose,
                               const std::vector<double> &extq, double a,
                               double v, double t, double lookahead_time,
                               double gain);

    int servoCartesianWithAxisGroup(const std::vector<double> &pose, double a,
                                    double v, double t, double lookahead_time,
                                    double gain, const std::string &group_name,
                                    const std::vector<double> &extq);

    /**
     * @ingroup MotionControl
     * \chinese
     * 跟踪运动，用于执行离线轨迹、透传用户规划轨迹等
     *
     * @param q
     * @param smooth_scale
     * @param delay_sacle
     * @return
     *
     * @par Lua函数原型
     * trackJoint(q: table,t: number,smooth_scale: number,delay_sacle: number)
     * -> nil
     *
     * @par Lua示例
     * trackJoint({0,0,0,0,0,0},0.01,0.5,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.trackJoint","params":[[0,0,0,0,0,0],0.01,0.5,1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Tracking motion, used for executing offline trajectories or passing
     * through user-planned trajectories, etc.
     *
     * @param q
     * @param smooth_scale
     * @param delay_sacle
     * @return
     *
     * @par Lua function prototype
     * trackJoint(q: table,t: number,smooth_scale: number,delay_sacle: number)
     * -> nil
     *
     * @par Lua example
     * trackJoint({0,0,0,0,0,0},0.01,0.5,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.trackJoint","params":[[0,0,0,0,0,0],0.01,0.5,1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int trackJoint(const std::vector<double> &q, double t, double smooth_scale,
                   double delay_sacle);

    /**
     * @ingroup MotionControl
     * \chinese
     * 跟踪运动，用于执行离线轨迹、透传用户规划轨迹等
     * 与 trackJoint 区别在于接收笛卡尔空间位姿而不是关节角度
     * (由软件内部直接做逆解)
     *
     * @param pose
     * @param t
     * @param smooth_scale
     * @param delay_sacle
     * @return
     *
     * @par Lua函数原型
     * trackCartesian(pose: table,t: number,smooth_scale: number,delay_sacle:
     * number) -> nil
     *
     * @par Lua示例
     * trackCartesian({0.58712,-0.15775,0.48703,2.76,0.344,1.432},0.01,0.5,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.trackCartesian","params":[[0.58712,-0.15775,0.48703,2.76,0.344,1.432],0.01,0.5,1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Tracking motion, used for executing offline trajectories or passing
     * through user-planned trajectories, etc. The difference from trackJoint is
     * that it receives Cartesian poses instead of joint angles (inverse
     * kinematics is performed internally by the software).
     *
     * @param pose
     * @param t
     * @param smooth_scale
     * @param delay_sacle
     * @return
     *
     * @par Lua function prototype
     * trackCartesian(pose: table,t: number,smooth_scale: number,delay_sacle:
     * number) -> nil
     *
     * @par Lua example
     * trackCartesian({0.58712,-0.15775,0.48703,2.76,0.344,1.432},0.01,0.5,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.trackCartesian","params":[[0.58712,-0.15775,0.48703,2.76,0.344,1.432],0.01,0.5,1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int trackCartesian(const std::vector<double> &pose, double t,
                       double smooth_scale, double delay_sacle);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节空间跟随
     *
     * @note 暂未实现
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * followJoint(self: pyaubo_sdk.MotionControl, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * followJoint(q: table) -> nil
     *
     * @par Lua示例
     * followJoint({0,0,0,0,0,0})
     *
     * \endchinese
     * \english
     * Joint space following
     *
     * @note Not implemented yet
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * followJoint(self: pyaubo_sdk.MotionControl, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * followJoint(q: table) -> nil
     *
     * @par Lua example
     * followJoint({0,0,0,0,0,0})
     *
     * \endenglish
     */
    int followJoint(const std::vector<double> &q);

    /**
     * @ingroup MotionControl
     * \chinese
     * 笛卡尔空间跟随
     *
     * @note 暂未实现
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * followLine(self: pyaubo_sdk.MotionControl, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * followLine(pose: table) -> nil
     *
     * @par Lua示例
     * followLine({0.58712,-0.15775,0.48703,2.76,0.344,1.432})
     *
     * \endchinese
     * \english
     * Cartesian space following
     *
     * @note Not implemented yet
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * followLine(self: pyaubo_sdk.MotionControl, arg0: List[float]) -> int
     *
     * @par Lua function prototype
     * followLine(pose: table) -> nil
     *
     * @par Lua example
     * followLine({0.58712,-0.15775,0.48703,2.76,0.344,1.432})
     *
     * \endenglish
     */
    int followLine(const std::vector<double> &pose);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节空间速度跟随
     *
     * 当机械臂还没达到目标速度的时候，给一个新的目标速度，机械臂会立刻达到新的目标速度
     *
     * @param qd 目标关节速度, 单位 rad/s
     * @param a 主轴的加速度, 单位 rad/s^2
     * @param t 函数返回所需要的时间, 单位 s \n
     * 如果 t = 0，当达到目标速度的时候，函数将返回；
     * 反之，则经过 t 时间后，函数返回，不管是否达到目标速度。\n
     * 如果没有达到目标速度，会减速到零。
     * 如果达到了目标速度就是按照目标速度匀速运动。
     * @retval 0 成功
     * @retval AUBO_BAD_STATE(1) 当前安全模式处于非
     * Normal、ReducedMode、Recovery 状态
     * @retval AUBO_BUSY(3) 上一条指令正在执行中
     * @retval -AUBO_BAD_STATE(-1)
     * 可能的原因包括但不限于：线程已分离、线程被终止、task_id
     * 未找到，或者当前机器人模式非 Running
     * @retval -AUBO_TIMEOUT(-4) 调用接口超时
     * @retval -AUBO_INVL_ARGUMENT(-5) 参数数组qd的长度小于当前机器臂的自由度
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * speedJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float) -> int
     *
     * @par Lua函数原型
     * speedJoint(qd: table, a: number, t: number) -> nil
     *
     * @par Lua示例
     * speedJoint({0.2,0,0,0,0,0}, 1.5,10)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.speedJoint","params":[[0.2,0,0,0,0,0],1.5,100],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Joint space velocity following
     *
     * When the robot arm has not yet reached the target velocity, giving a new
     * target velocity will cause the robot arm to immediately reach the new
     * target velocity.
     *
     * @param qd Target joint velocity, unit: rad/s
     * @param a Main axis acceleration, unit: rad/s^2
     * @param t Time required for the function to return, unit: s \n
     * If t = 0, the function returns when the target velocity is reached;
     * otherwise, the function returns after t seconds, regardless of whether
     * the target velocity is reached.\n If the target velocity is not reached,
     * it will decelerate to zero. If the target velocity is reached, it will
     * move at a constant speed.
     * @retval 0 Success
     * @retval AUBO_BAD_STATE(1) The current safety mode is not Normal,
     * ReducedMode, or Recovery
     * @retval AUBO_BUSY(3) The previous instruction is being executed
     * @retval -AUBO_BAD_STATE(-1)
     * Possible reasons include but are not limited to: thread has been
     * detached, thread terminated, task_id not found, or the current robot mode
     * is not Running
     * @retval -AUBO_TIMEOUT(-4) Interface call timeout
     * @retval -AUBO_INVL_ARGUMENT(-5) The length of the qd array is less than
     * the degrees of freedom of the current robot arm
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * speedJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float) -> int
     *
     * @par Lua function prototype
     * speedJoint(qd: table, a: number, t: number) -> nil
     *
     * @par Lua example
     * speedJoint({0.2,0,0,0,0,0}, 1.5,10)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.speedJoint","params":[[0.2,0,0,0,0,0],1.5,100],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int speedJoint(const std::vector<double> &qd, double a, double t);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节空间速度跟随(机械臂运行工程时发生碰撞,通过此接口移动到安全位置)
     *
     * 当机械臂还没达到目标速度的时候，给一个新的目标速度，机械臂会立刻达到新的目标速度
     *
     * @param qd 目标关节速度, 单位 rad/s
     * @param a 主轴的加速度, 单位 rad/s^2
     * @param t 函数返回所需要的时间, 单位 s
     * 如果 t = 0，当达到目标速度的时候，函数将返回；
     * 反之，则经过 t 时间后，函数返回，不管是否达到目标速度。
     * 如果没有达到目标速度，会减速到零。
     * 如果达到了目标速度就是按照目标速度匀速运动。
     * @return 成功返回0; 失败返回错误码
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resumeSpeedJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float) -> int
     *
     * @par Lua函数原型
     * resumeSpeedJoint(q: table, a: number, t: number) -> nil
     *
     * @par Lua示例
     * resumeSpeedJoint({0.2,0,0,0,0,0},1.5,10)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeSpeedJoint","params":[[0.2,0,0,0,0,0],1.5,100],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endchinese
     * \english
     * Joint space velocity following (used to move to a safe position after a
     * collision during process execution)
     *
     * When the robot arm has not yet reached the target velocity, giving a new
     * target velocity will cause the robot arm to immediately reach the new
     * target velocity.
     *
     * @param qd Target joint velocity, unit: rad/s
     * @param a Main axis acceleration, unit: rad/s^2
     * @param t Time required for the function to return, unit: s
     * If t = 0, the function returns when the target velocity is reached;
     * otherwise, the function returns after t seconds, regardless of whether
     * the target velocity is reached. If the target velocity is not reached, it
     * will decelerate to zero. If the target velocity is reached, it will move
     * at a constant speed.
     * @return Returns 0 on success; otherwise returns error code
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * resumeSpeedJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float) -> int
     *
     * @par Lua function prototype
     * resumeSpeedJoint(q: table, a: number, t: number) -> nil
     *
     * @par Lua example
     * resumeSpeedJoint({0.2,0,0,0,0,0},1.5,10)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeSpeedJoint","params":[[0.2,0,0,0,0,0],1.5,100],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endenglish
     */
    int resumeSpeedJoint(const std::vector<double> &qd, double a, double t);

    /**
     * @ingroup MotionControl
     * \chinese
     * 笛卡尔空间速度跟随
     *
     * 当机械臂还没达到目标速度的时候，给一个新的目标速度，机械臂会立刻达到新的目标速度
     *
     * @param xd 工具速度, 单位 m/s
     * @param a 工具位置加速度, 单位 m/s^2
     * @param t 函数返回所需要的时间, 单位 s \n
     * 如果 t = 0，当达到目标速度的时候，函数将返回；
     * 反之，则经过 t 时间后，函数返回，不管是否达到目标速度。
     * 如果没有达到目标速度，会减速到零。
     * 如果达到了目标速度就是按照目标速度匀速运动。
     * @retval 0 成功
     * @retval AUBO_BAD_STATE(1) 当前安全模式处于非
     * Normal、ReducedMode、Recovery 状态
     * @retval AUBO_BUSY(3) 上一条指令正在执行中
     * @retval -AUBO_BAD_STATE(-1)
     * 可能的原因包括但不限于：线程已分离、线程被终止、task_id
     * 未找到，或者当前机器人模式非 Running
     * @retval -AUBO_TIMEOUT(-4) 调用接口超时
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * speedLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1: float,
     * arg2: float) -> int
     *
     * @par Lua函数原型
     * speedLine(pose: table, a: number, t: number) -> nil
     *
     * @par Lua示例
     * speedLine({0.25,0,0,0,0,0},1.2,100)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.speedLine","params":[[0.25,0,0,0,0,0],1.2,100],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Cartesian space velocity following
     *
     * When the robot arm has not yet reached the target velocity, giving a new
     * target velocity will cause the robot arm to immediately reach the new
     * target velocity.
     *
     * @param xd Tool velocity, unit: m/s
     * @param a Tool position acceleration, unit: m/s^2
     * @param t Time required for the function to return, unit: s \n
     * If t = 0, the function returns when the target velocity is reached;
     * otherwise, the function returns after t seconds, regardless of whether
     * the target velocity is reached. If the target velocity is not reached, it
     * will decelerate to zero. If the target velocity is reached, it will move
     * at a constant speed.
     * @retval 0 Success
     * @retval AUBO_BAD_STATE(1) The current safety mode is not Normal,
     * ReducedMode, or Recovery
     * @retval AUBO_BUSY(3) The previous instruction is being executed
     * @retval -AUBO_BAD_STATE(-1)
     * Possible reasons include but are not limited to: thread has been
     * detached, thread terminated, task_id not found, or the current robot mode
     * is not Running
     * @retval -AUBO_TIMEOUT(-4) Interface call timeout
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * speedLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1: float,
     * arg2: float) -> int
     *
     * @par Lua function prototype
     * speedLine(pose: table, a: number, t: number) -> nil
     *
     * @par Lua example
     * speedLine({0.25,0,0,0,0,0},1.2,100)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.speedLine","params":[[0.25,0,0,0,0,0],1.2,100],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int speedLine(const std::vector<double> &xd, double a, double t);

    /**
     * @ingroup MotionControl
     * \chinese
     * 笛卡尔空间速度跟随(机械臂运行工程时发生碰撞,通过此接口移动到安全位置)
     *
     * 当机械臂还没达到目标速度的时候，给一个新的目标速度，机械臂会立刻达到新的目标速度
     *
     * @param xd 工具速度, 单位 m/s
     * @param a 工具位置加速度, 单位 m/s^2
     * @param t 函数返回所需要的时间, 单位 s \n
     * 如果 t = 0，当达到目标速度的时候，函数将返回；
     * 反之，则经过 t 时间后，函数返回，不管是否达到目标速度。
     * 如果没有达到目标速度，会减速到零。
     * 如果达到了目标速度就是按照目标速度匀速运动。
     * @return 成功返回0; 失败返回错误码
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resumeSpeedLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float) -> int
     *
     * @par Lua函数原型
     * resumeSpeedLine(pose: table, a: number, t: number) -> nil
     *
     * @par Lua示例
     * resumeSpeedLine({0.25,0,0,0,0,0},1.2,100)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeSpeedLine","params":[[0.25,0,0,0,0,0],1.2,100],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endchinese
     * \english
     * Cartesian space velocity following (used to move to a safe position after
     * a collision during process execution)
     *
     * When the robot arm has not yet reached the target velocity, giving a new
     * target velocity will cause the robot arm to immediately reach the new
     * target velocity.
     *
     * @param xd Tool velocity, unit: m/s
     * @param a Tool position acceleration, unit: m/s^2
     * @param t Time required for the function to return, unit: s \n
     * If t = 0, the function returns when the target velocity is reached;
     * otherwise, the function returns after t seconds, regardless of whether
     * the target velocity is reached. If the target velocity is not reached, it
     * will decelerate to zero. If the target velocity is reached, it will move
     * at a constant speed.
     * @return Returns 0 on success; otherwise returns error code
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * resumeSpeedLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float) -> int
     *
     * @par Lua function prototype
     * resumeSpeedLine(pose: table, a: number, t: number) -> nil
     *
     * @par Lua example
     * resumeSpeedLine({0.25,0,0,0,0,0},1.2,100)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeSpeedLine","params":[[0.25,0,0,0,0,0],1.2,100],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endenglish
     */
    int resumeSpeedLine(const std::vector<double> &xd, double a, double t);

    /**
     * @ingroup MotionControl
     * \chinese
     * 在关节空间做样条插值
     *
     * @param q 关节角度，如果传入参数维度为0，表示样条运动结束
     * @param a 加速度, 单位 rad/s^2,
     * 最大值可通过RobotConfig类中的接口getJointMaxAccelerations()来获取
     * @param v 速度， 单位 rad/s,
     * 最大值可通过RobotConfig类中的接口getJointMaxSpeeds()来获取
     * @param duration
     * @return 成功返回0; 失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * moveSpline(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float) -> int
     *
     * @par Lua函数原型
     * moveSpline(q: table, a: number, v: number, duration: number) -> nil
     *
     * @par Lua示例
     * moveSpline({-2.05177,-0.400292, 1.19625, 0.0285152, 1.57033,
     * -2.28774},1.3,1.0,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveSpline","params":[[0,0,0,0,0,0],1,1,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Perform spline interpolation in joint space
     *
     * @param q Joint angles. If the input vector is of size 0, it indicates the
     * end of the spline motion.
     * @param a Acceleration, unit: rad/s^2. The maximum value can be obtained
     * via RobotConfig::getJointMaxAccelerations().
     * @param v Velocity, unit: rad/s. The maximum value can be obtained via
     * RobotConfig::getJointMaxSpeeds().
     * @param duration
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * moveSpline(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float) -> int
     *
     * @par Lua function prototype
     * moveSpline(q: table, a: number, v: number, duration: number) -> nil
     *
     * @par Lua example
     * moveSpline({-2.05177,-0.400292, 1.19625, 0.0285152, 1.57033,
     * -2.28774},1.3,1.0,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveSpline","params":[[0,0,0,0,0,0],1,1,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int moveSpline(const std::vector<double> &q, double a, double v,
                   double duration);

    /**
     * @ingroup MotionControl
     * \chinese
     * 添加关节运动
     *
     * @param q 关节角, 单位 rad
     * @param a 加速度, 单位 rad/s^2,
     * 最大值可通过RobotConfig类中的接口getJointMaxAccelerations()来获取
     * @param v 速度， 单位 rad/s,
     * 最大值可通过RobotConfig类中的接口getJointMaxSpeeds()来获取
     * @param blend_radius 交融半径, 单位 m
     * @param duration 运行时间，单位 s \n
     * 通常当给定了速度和加速度，便能够确定轨迹的运行时间。
     * 如果想延长轨迹的运行时间，便要设置 duration 这个参数。
     * duration 可以延长轨迹运动的时间，但是不能缩短轨迹时间。\n
     * 当 duration = 0的时候，
     * 表示不指定运行时间，即没有明确完成运动的时间，将根据速度与加速度计算运行时间。
     * 如果duration不等于0，a 和 v 的值将被忽略。
     * @retval 0 成功
     * @retval AUBO_BAD_STATE(1) 当前安全模式处于非
     * Normal、ReducedMode、Recovery 状态
     * @retval AUBO_QUEUE_FULL(2) 规划队列已满
     * @retval AUBO_BUSY(3) 上一条指令正在执行中
     * @retval -AUBO_BAD_STATE(-1)
     * 可能的原因包括但不限于：线程已分离、线程被终止、task_id
     * 未找到，或者当前机器人模式非 Running
     * @retval -AUBO_TIMEOUT(-4) 调用接口超时
     * @retval -AUBO_INVL_ARGUMENT(-5) 参数数组q的长度小于当前机器臂的自由度
     * @retval AUBO_REQUEST_IGNORE(13) 参数数组q的长度太短且无需在该点停留
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * moveJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1: float,
     * arg2: float, arg3: float, arg4: float) -> int
     *
     * @par Lua函数原型
     * moveJoint(q: table, a: number, v: number, blend_radius: number, duration:
     * number) -> nil
     *
     * @par Lua示例
     * moveJoint({-2.05177,-0.400292, 1.19625, 0.0285152, 1.57033,
     * -2.28774},0.3,0.3,0,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveJoint","params":[[-2.05177,
     * -0.400292, 1.19625, 0.0285152, 1.57033, -2.28774],0.3,0.3,0,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Add joint motion
     *
     * @param q Joint angles, unit: rad
     * @param a Acceleration, unit: rad/s^2,
     * The maximum value can be obtained via
     * RobotConfig::getJointMaxAccelerations()
     * @param v Velocity, unit: rad/s,
     * The maximum value can be obtained via RobotConfig::getJointMaxSpeeds()
     * @param blend_radius Blend radius, unit: m
     * @param duration Execution time, unit: s \n
     * Normally, when speed and acceleration are given, the trajectory duration
     * can be determined. If you want to extend the trajectory duration, set the
     * duration parameter. Duration can extend the trajectory time, but cannot
     * shorten it.\n When duration = 0, it means the execution time is not
     * specified, and the time will be calculated based on speed and
     * acceleration. If duration is not 0, a and v values will be ignored.
     * @retval 0 Success
     * @retval AUBO_BAD_STATE(1) The current safety mode is not Normal,
     * ReducedMode, or Recovery
     * @retval AUBO_QUEUE_FULL(2) Planning queue is full
     * @retval AUBO_BUSY(3) The previous instruction is being executed
     * @retval -AUBO_BAD_STATE(-1)
     * Possible reasons include but are not limited to: thread has been
     * detached, thread terminated, task_id not found, or the current robot mode
     * is not Running
     * @retval -AUBO_TIMEOUT(-4) Interface call timeout
     * @retval -AUBO_INVL_ARGUMENT(-5) The length of q is less than the degrees
     * of freedom of the current robot arm
     * @retval AUBO_REQUEST_IGNORE(13) The length of q is too short and there is
     * no need to stop at that point
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * moveJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1: float,
     * arg2: float, arg3: float, arg4: float) -> int
     *
     * @par Lua function prototype
     * moveJoint(q: table, a: number, v: number, blend_radius: number, duration:
     * number) -> nil
     *
     * @par Lua example
     * moveJoint({-2.05177,-0.400292, 1.19625, 0.0285152, 1.57033,
     * -2.28774},0.3,0.3,0,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveJoint","params":[[-2.05177,
     * -0.400292, 1.19625, 0.0285152, 1.57033, -2.28774],0.3,0.3,0,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int moveJoint(const std::vector<double> &q, double a, double v,
                  double blend_radius, double duration);

    /**
     * @ingroup MotionControl
     * \chinese
     * 机器人与外部轴同步运动
     *
     * @param group_name
     * @param q
     * @param a
     * @param v
     * @param blend_radius
     * @param duration
     * @return
     * \endchinese
     * \english
     * Synchronous motion of robot and external axes
     *
     * @param group_name
     * @param q
     * @param a
     * @param v
     * @param blend_radius
     * @param duration
     * @return
     * \endenglish
     */
    int moveJointWithAxisGroup(const std::vector<double> &q, double a, double v,
                               double blend_radius, double duration,
                               const std::string &group_name,
                               const std::vector<double> &extq);

    /**
     * @ingroup MotionControl
     * \chinese
     * 通过关节运动移动到暂停点的位置
     *
     * @param q 关节角, 单位 rad
     * @param a 加速度, 单位 rad/s^2
     * @param v 速度， 单位 rad/s
     * @param duration 运行时间，单位 s \n
     * 通常当给定了速度和加速度，便能够确定轨迹的运行时间。
     * 如果想延长轨迹的运行时间，便要设置 duration 这个参数。
     * duration 可以延长轨迹运动的时间，但是不能缩短轨迹时间。\n
     * 当 duration = 0的时候，
     * 表示不指定运行时间，即没有明确完成运动的时间，将根据速度与加速度计算运行时间。
     * 如果duration不等于0，a 和 v 的值将被忽略。
     * @return 成功返回0；失败返回错误码
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resumeMoveJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float) -> int
     *
     * @par Lua函数原型
     * resumeMoveJoint(q: table, a: number, v: number, duration: number) -> nil
     *
     * @par Lua示例
     * resumeMoveJoint({-2.05177,-0.400292, 1.19625, 0.0285152, 1.57033,
     * -2.28774},1.3,1.0,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeMoveJoint","params":[[-2.05177,
     * -0.400292, 1.19625, 0.0285152, 1.57033, -2.28774],0.3,0.3,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endchinese
     * \english
     * Move to the pause point using joint motion.
     *
     * @param q Joint angles, unit: rad
     * @param a Acceleration, unit: rad/s^2
     * @param v Velocity, unit: rad/s
     * @param duration Execution time, unit: s \n
     * Normally, when speed and acceleration are given, the trajectory duration
     * can be determined. If you want to extend the trajectory duration, set the
     * duration parameter. Duration can extend the trajectory time, but cannot
     * shorten it.\n When duration = 0, it means the execution time is not
     * specified, and the time will be calculated based on speed and
     * acceleration. If duration is not 0, a and v values will be ignored.
     * @return Returns 0 on success; otherwise returns error code
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * resumeMoveJoint(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float) -> int
     *
     * @par Lua function prototype
     * resumeMoveJoint(q: table, a: number, v: number, duration: number) -> nil
     *
     * @par Lua example
     * resumeMoveJoint({-2.05177,-0.400292, 1.19625, 0.0285152, 1.57033,
     * -2.28774},1.3,1.0,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeMoveJoint","params":[[-2.05177,
     * -0.400292, 1.19625, 0.0285152, 1.57033, -2.28774],0.3,0.3,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endenglish
     */
    int resumeMoveJoint(const std::vector<double> &q, double a, double v,
                        double duration);

    /**
     * @ingroup MotionControl
     * \chinese
     * 添加直线运动
     *
     * @param pose 目标位姿
     * @param a 加速度(如果位置变化小于1mm,姿态变化大于 1e-4
     * rad,此加速度会被作为角加速度,单位 rad/s^2.否则为线加速度,单位 m/s^2)
     * 最大值可通过RobotConfig类中的接口getTcpMaxAccelerations()来获取
     * @param v 速度(如果位置变化小于1mm,姿态变化大于 1e-4
     * rad,此速度会被作为角速度,单位 rad/s.否则为线速度,单位 m/s)
     * 最大值可通过RobotConfig类中的接口getTcpMaxSpeeds()来获取
     * @param blend_radius 交融半径，单位 m，值介于0.001和1之间
     * @param duration 运行时间，单位 s \n
     * 通常当给定了速度和加速度，便能够确定轨迹的运行时间。
     * 如果想延长轨迹的运行时间，便要设置 duration 这个参数。
     * duration 可以延长轨迹运动的时间，但是不能缩短轨迹时间。\n
     * 当 duration = 0的时候，
     * 表示不指定运行时间，即没有明确完成运动的时间，将根据速度与加速度计算运行时间。
     * 如果duration不等于0，a 和 v 的值将被忽略。
     * @retval 0 成功
     * @retval AUBO_BAD_STATE(1) 当前安全模式处于非
     * Normal、ReducedMode、Recovery 状态
     * @retval AUBO_QUEUE_FULL(2) 轨迹队列已满
     * @retval AUBO_BUSY(3) 上一条指令正在执行中
     * @retval -AUBO_BAD_STATE(-1)
     * 可能的原因包括但不限于：线程已分离、线程被终止、task_id
     * 未找到，或者当前机器人模式非 Running
     * @retval -AUBO_TIMEOUT(-4) 调用接口超时
     * @retval -AUBO_INVL_ARGUMENT(-5) 参数数组 pose
     * 的长度小于当前机器臂的自由度
     * @retval AUBO_REQUEST_IGNORE(13) 参数数组 pose
     * 路径长度太短且无需在该点停留
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * moveLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1: float,
     * arg2: float, arg3: float, arg4: float) -> int
     *
     * @par Lua函数原型
     * moveLine(pose: table, a: number, v: number, blend_radius: number,
     * duration: number) -> nil
     *
     * @par Lua示例
     * moveLine({0.58815,0.0532,0.62391,2.46,0.479,1.619},1.3,1.0,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveLine","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],1.2,0.25,0,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Add linear motion
     *
     * @param pose Target pose
     * @param a Acceleration (if the position change is less than 1mm and the
     * posture change is greater than 1e-4 rad, this acceleration is treated as
     * angular acceleration in rad/s^2; otherwise, as linear acceleration in
     * m/s^2). The maximum value can be obtained via
     * RobotConfig::getTcpMaxAccelerations().
     * @param v Velocity (if the position change is less than 1mm and the
     * posture change is greater than 1e-4 rad, this velocity is treated as
     * angular velocity in rad/s; otherwise, as linear velocity in m/s). The
     * maximum value can be obtained via RobotConfig::getTcpMaxSpeeds().
     * @param blend_radius Blend radius, unit: m, value between 0.001 and 1
     * @param duration Execution time, unit: s \n
     * Normally, when speed and acceleration are given, the trajectory duration
     * can be determined. If you want to extend the trajectory duration, set the
     * duration parameter. Duration can extend the trajectory time, but cannot
     * shorten it.\n When duration = 0, it means the execution time is not
     * specified, and the time will be calculated based on speed and
     * acceleration. If duration is not 0, a and v values will be ignored.
     * @retval 0 Success
     * @retval AUBO_BAD_STATE(1) The current safety mode is not Normal,
     * ReducedMode, or Recovery
     * @retval AUBO_QUEUE_FULL(2) Trajectory queue is full
     * @retval AUBO_BUSY(3) The previous instruction is being executed
     * @retval -AUBO_BAD_STATE(-1) Possible reasons include but are not limited
     * to: thread has been detached, thread terminated, task_id not found, or
     * the current robot mode is not Running
     * @retval -AUBO_TIMEOUT(-4) Interface call timeout
     * @retval -AUBO_INVL_ARGUMENT(-5) The length of the pose array is less than
     * the degrees of freedom of the current robot arm
     * @retval AUBO_REQUEST_IGNORE(13) The length of the pose array is too short
     * and there is no need to stop at that point
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * moveLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1: float,
     * arg2: float, arg3: float, arg4: float) -> int
     *
     * @par Lua function prototype
     * moveLine(pose: table, a: number, v: number, blend_radius: number,
     * duration: number) -> nil
     *
     * @par Lua example
     * moveLine({0.58815,0.0532,0.62391,2.46,0.479,1.619},1.3,1.0,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveLine","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],1.2,0.25,0,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int moveLine(const std::vector<double> &pose, double a, double v,
                 double blend_radius, double duration);

    /**
     * @ingroup MotionControl
     * \chinese
     * 直线运动与外部轴同步运动
     *
     * @param group_name 外部轴组名称
     * @param pose 目标位姿
     * @param a 加速度
     * @param v 速度
     * @param blend_radius 交融半径
     * @param duration 运行时间
     * @return
     * \endchinese
     * \english
     * Linear motion synchronized with external axes
     *
     * @param group_name Name of the external axis group
     * @param pose Target pose
     * @param a Acceleration
     * @param v Velocity
     * @param blend_radius Blend radius
     * @param duration Execution time
     * @return
     * \endenglish
     */
    int moveLineWithAxisGroup(const std::vector<double> &pose, double a,
                              double v, double blend_radius, double duration,
                              const std::string &group_name,
                              const std::vector<double> &extq);

    /**
     * @ingroup MotionControl
     * \chinese
     * 添加工艺运动
     *
     * @param pose
     * @param a
     * @param v
     * @param blend_radius
     * @return 成功返回0；失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * moveProcess(pose: table, a: number, v: number, blend_radius: number,
     * duration: number) -> nil
     *
     * @par Lua示例
     * moveProcess({0.58815,0.0532,0.62391,2.46,0.479,1.619},1.2,0.25,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveProcess","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],1.2,0.25,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Add process motion
     *
     * @param pose
     * @param a
     * @param v
     * @param blend_radius
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * moveProcess(pose: table, a: number, v: number, blend_radius: number,
     * duration: number) -> nil
     *
     * @par Lua example
     * moveProcess({0.58815,0.0532,0.62391,2.46,0.479,1.619},1.2,0.25,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveProcess","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],1.2,0.25,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int moveProcess(const std::vector<double> &pose, double a, double v,
                    double blend_radius);

    /**
     * @ingroup MotionControl
     * \chinese
     * 通过直线运动移动到暂停点的位置
     *
     * @param pose 目标位姿
     * @param a 加速度, 单位 m/s^2
     * @param v 速度, 单位 m/s
     * @param duration 运行时间，单位 s \n
     * 通常当给定了速度和加速度，便能够确定轨迹的运行时间。
     * 如果想延长轨迹的运行时间，便要设置 duration 这个参数。
     * duration 可以延长轨迹运动的时间，但是不能缩短轨迹时间。\n
     * 当 duration = 0的时候，
     * 表示不指定运行时间，即没有明确完成运动的时间，将根据速度与加速度计算运行时间。
     * 如果duration不等于0，a 和 v 的值将被忽略。
     * @return 成功返回0；失败返回错误码
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resumeMoveLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float) -> int
     *
     * @par Lua函数原型
     * resumeMoveLine(pose: table, a: number, v: number,duration: number) -> nil
     *
     * @par Lua示例
     * resumeMoveLine({0.58815,0.0532,0.62391,2.46,0.479,1.619},1.2,0.25,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeMoveLine","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],1.2,0.25,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Move to the pause point using linear motion.
     *
     * @param pose Target pose
     * @param a Acceleration, unit: m/s^2
     * @param v Velocity, unit: m/s
     * @param duration Execution time, unit: s \n
     * Normally, when speed and acceleration are given, the trajectory duration
     * can be determined. If you want to extend the trajectory duration, set the
     * duration parameter. Duration can extend the trajectory time, but cannot
     * shorten it.\n When duration = 0, it means the execution time is not
     * specified, and the time will be calculated based on speed and
     * acceleration. If duration is not 0, a and v values will be ignored.
     * @return Returns 0 on success; otherwise returns error code
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * resumeMoveLine(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float) -> int
     *
     * @par Lua function prototype
     * resumeMoveLine(pose: table, a: number, v: number, duration: number) ->
     * nil
     *
     * @par Lua example
     * resumeMoveLine({0.58815,0.0532,0.62391,2.46,0.479,1.619},1.2,0.25,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeMoveLine","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],1.2,0.25,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int resumeMoveLine(const std::vector<double> &pose, double a, double v,
                       double duration);

    /**
     * @ingroup MotionControl
     * \chinese
     * 添加圆弧运动
     *
     * @todo 可以由多段圆弧组成圆周运动
     *
     * @param via_pose 圆弧运动途中点的位姿
     * @param end_pose 圆弧运动结束点的位姿
     * @param a 加速度(如果via_pose与上一个路点位置变化小于1mm,姿态变化大于 1e-4
     * rad, 此加速度会被作为角加速度,单位 rad/s^2.否则为线加速度,单位 m/s^2)
     * @param v 速度(如果via_pose与上一个路点位置变化小于1mm, 姿态变化大于 1e-4
     * rad, 此速度会被作为角速度, 单位 rad / s.否则为线速度, 单位 m / s)
     * @param blend_radius 交融半径，单位: m
     * @param duration 运行时间，单位: s \n
     * 通常当给定了速度和加速度，便能够确定轨迹的运行时间。
     * 如果想延长轨迹的运行时间，便要设置 duration 这个参数。
     * duration 可以延长轨迹运动的时间，但是不能缩短轨迹时间。\n
     * 当 duration = 0 的时候，
     * 表示不指定运行时间，即没有明确完成运动的时间，将根据速度与加速度计算运行时间。
     * 如果duration不等于0，a 和 v 的值将被忽略。
     * @return 成功返回0；失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * moveCircle(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * List[float], arg2: float, arg3: float, arg4: float, arg5: float) -> int
     *
     * @par Lua函数原型
     * moveCircle(via_pose: table, end_pose: table, a: number, v: number,
     * blend_radius: number, duration: number) -> nil
     *
     * @par Lua示例
     * moveCircle({0.440164,-0.00249391,0.398658,2.45651,0,1.5708},{0.440164,0.166256,0.297599,2.45651,0,1.5708},1.2,0.25,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveCircle","params":[[0.440164,-0.00249391,0.398658,2.45651,0,1.5708],[0.440164,0.166256,0.297599,2.45651,0,1.5708],1.2,0.25,0,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Add circular arc motion
     *
     * @todo Can be composed of multiple arcs to form a circular motion
     *
     * @param via_pose The pose of the via point during the arc motion
     * @param end_pose The pose of the end point of the arc motion
     * @param a Acceleration (if the position change between via_pose and the
     * previous waypoint is less than 1mm and the posture change is greater than
     * 1e-4 rad, this acceleration is treated as angular acceleration in
     * rad/s^2; otherwise, as linear acceleration in m/s^2)
     * @param v Velocity (if the position change between via_pose and the
     * previous waypoint is less than 1mm and the posture change is greater than
     * 1e-4 rad, this velocity is treated as angular velocity in rad/s;
     * otherwise, as linear velocity in m/s)
     * @param blend_radius Blend radius, unit: m
     * @param duration Execution time, unit: s \n
     * Normally, when speed and acceleration are given, the trajectory duration
     * can be determined. If you want to extend the trajectory duration, set the
     * duration parameter. Duration can extend the trajectory time, but cannot
     * shorten it.\n When duration = 0, it means the execution time is not
     * specified, and the time will be calculated based on speed and
     * acceleration. If duration is not 0, a and v values will be ignored.
     * @return Returns 0 on success; otherwise returns error code
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * moveCircle(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * List[float], arg2: float, arg3: float, arg4: float, arg5: float) -> int
     *
     * @par Lua function prototype
     * moveCircle(via_pose: table, end_pose: table, a: number, v: number,
     * blend_radius: number, duration: number) -> nil
     *
     * @par Lua example
     * moveCircle({0.440164,-0.00249391,0.398658,2.45651,0,1.5708},{0.440164,0.166256,0.297599,2.45651,0,1.5708},1.2,0.25,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveCircle","params":[[0.440164,-0.00249391,0.398658,2.45651,0,1.5708],[0.440164,0.166256,0.297599,2.45651,0,1.5708],1.2,0.25,0,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int moveCircle(const std::vector<double> &via_pose,
                   const std::vector<double> &end_pose, double a, double v,
                   double blend_radius, double duration);

    /**
     * @ingroup MotionControl
     * \chinese
     * moveCircle 与外部轴同步运动
     *
     * @param group_name 外部轴组名称
     * @param via_pose 圆弧运动途中点的位姿
     * @param end_pose 圆弧运动结束点的位姿
     * @param a 加速度
     * @param v 速度
     * @param blend_radius 交融半径
     * @param duration 运行时间
     * @return
     * \endchinese
     * \english
     * moveCircle with external axes synchronized motion
     *
     * @param group_name Name of the external axis group
     * @param via_pose The pose of the via point during the arc motion
     * @param end_pose The pose of the end point of the arc motion
     * @param a Acceleration
     * @param v Velocity
     * @param blend_radius Blend radius
     * @param duration Execution time
     * @return
     * \endenglish
     */
    int moveCircleWithAxisGroup(const std::vector<double> &via_pose,
                                const std::vector<double> &end_pose, double a,
                                double v, double blend_radius, double duration,
                                const std::string &group_name,
                                const std::vector<double> &extq);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置圆弧路径模式
     *
     * @param mode 模式 \n
     * 0:工具姿态相对于圆弧路径点坐标系保持不变 \n
     * 1:姿态线性变化,绕着空间定轴转动,从起始点姿态变化到目标点姿态 \n
     * 2:从起点姿态开始经过中间点姿态,变化到目标点姿态
     * @return 成功返回0；失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setCirclePathMode(self: pyaubo_sdk.MotionControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * setCirclePathMode(mode: number) -> nil
     *
     * @par Lua示例
     * setCirclePathMode(1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setCirclePathMode","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set circle path mode
     *
     * @param mode Mode \n
     * 0: Tool orientation remains unchanged relative to the arc path point
     * coordinate system \n 1: Orientation changes linearly, rotating around a
     * fixed axis in space, from the start orientation to the target orientation
     * \n 2: Orientation changes from the start orientation, through the via
     * point orientation, to the target orientation
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setCirclePathMode(self: pyaubo_sdk.MotionControl, arg0: int) -> int
     *
     * @par Lua function prototype
     * setCirclePathMode(mode: number) -> nil
     *
     * @par Lua example
     * setCirclePathMode(1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setCirclePathMode","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setCirclePathMode(int mode);

    /**
     * @ingroup MotionControl
     * \chinese
     * 高级圆弧或者圆周运动
     *
     * @param param 圆周运动参数
     * @return 成功返回0；失败返回错误码
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * moveCircle2(self: pyaubo_sdk.MotionControl, arg0:
     * arcs::common_interface::CircleParameters) -> int
     *
     * @par Lua函数原型
     * moveCircle2(param: table) -> nil
     *
     * @par Lua示例
     * moveCircle2({0.440164,-0.00249391,0.398658,2.45651,0,1.570},{0.440164,0.166256,0.297599,2.45651,0,1.5708},1.2,0.25,0,0,0,0,0,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveCircle2","params":[{"pose_via":[0.440164,-0.00249391,0.398658,2.45651,0,1.570],
     * "pose_to":[0.440164,0.166256,0.297599,2.45651,0,1.5708],"a":1.2,"v":0.25,"blend_radius":0,"duration":0,"helix":0,
     * "spiral":0,"direction":0,"loop_times":0}],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Advanced arc or circular motion
     *
     * @param param Circular motion parameters
     * @return Returns 0 on success; otherwise returns an error code:
     * AUBO_BAD_STATE
     * AUBO_BUSY
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * moveCircle2(self: pyaubo_sdk.MotionControl, arg0:
     * arcs::common_interface::CircleParameters) -> int
     *
     * @par Lua function prototype
     * moveCircle2(param: table) -> nil
     *
     * @par Lua example
     * moveCircle2({0.440164,-0.00249391,0.398658,2.45651,0,1.570},{0.440164,0.166256,0.297599,2.45651,0,1.5708},1.2,0.25,0,0,0,0,0,0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveCircle2","params":[{"pose_via":[0.440164,-0.00249391,0.398658,2.45651,0,1.570],
     * "pose_to":[0.440164,0.166256,0.297599,2.45651,0,1.5708],"a":1.2,"v":0.25,"blend_radius":0,"duration":0,"helix":0,
     * "spiral":0,"direction":0,"loop_times":0}],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int moveCircle2(const CircleParameters &param);

    /**
     * @ingroup MotionControl
     * \chinese
     * 新建一个路径点缓存
     *
     * @param name 指定路径的名字
     * @param type 路径的类型 \n
     *   1: toppra 时间最优路径规划 \n
     *   2: cubic_spline(录制的轨迹) \n
     *   3: 关节B样条插值，最少三个点
     * @param size 缓存区大小
     * @return 新建成功返回 AUBO_OK(0)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBufferAlloc(self: pyaubo_sdk.MotionControl, arg0: str, arg1: int,
     * arg2: int) -> int
     *
     * @par Lua函数原型
     * pathBufferAlloc(name: string, type: number, size: number) -> nil
     *
     * @par Lua示例
     * pathBufferAlloc("traje_name",5,100)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferAlloc","params":["rec",2,3],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Create a new path point buffer
     *
     * @param name Name of the path
     * @param type Type of the path \n
     *   1: toppra time-optimal path planning \n
     *   2: cubic_spline (recorded trajectory) \n
     *   3: Joint B-spline interpolation, at least three points
     * @param size Buffer size
     * @return Returns AUBO_OK(0) on success
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBufferAlloc(self: pyaubo_sdk.MotionControl, arg0: str, arg1: int,
     * arg2: int) -> int
     *
     * @par Lua function prototype
     * pathBufferAlloc(name: string, type: number, size: number) -> nil
     *
     * @par Lua exmaple
     * pathBufferAlloc("traje_name",5,100)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferAlloc","params":["rec",2,3],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int pathBufferAlloc(const std::string &name, int type, int size);

    /**
     * @ingroup MotionControl
     * \chinese
     * 向路径缓存添加路点
     *
     * @param name 路径缓存的名字
     * @param waypoints 路点
     * @return 成功返回0；失败返回错误码
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBufferAppend(self: pyaubo_sdk.MotionControl, arg0: str, arg1:
     * List[List[float]]) -> int
     *
     * @par Lua函数原型
     * pathBufferAppend(name: string, waypoints: table) -> nil
     *
     * @par Lua示例
     * pathBufferAppend("traje_name",{{-0.000000,0.000009,-0.000001,0.000002,0.000002,0.000000},{-0.000001,0.000010,-0.000002,0.000000,0.000003,0.000002}})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferAppend","params":["rec",[[-0.000000,0.000009,-0.000001,0.000002,0.000002,0.000000],[-0.000001,0.000010,-0.000002,0.000000,0.000003,0.000002]]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Add waypoints to the path buffer
     *
     * @param name Name of the path buffer
     * @param waypoints Waypoints
     * @return Returns 0 on success; otherwise returns an error code
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBufferAppend(self: pyaubo_sdk.MotionControl, arg0: str, arg1:
     * List[List[float]]) -> int
     *
     * @par Lua function prototype
     * pathBufferAppend(name: string, waypoints: table) -> nil
     *
     * @par Lua example
     * pathBufferAppend("traje_name",{{-0.000000,0.000009,-0.000001,0.000002,0.000002,0.000000},{-0.000001,0.000010,-0.000002,0.000000,0.000003,0.000002}})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferAppend","params":["rec",[[-0.000000,0.000009,-0.000001,0.000002,0.000002,0.000000],[-0.000001,0.000010,-0.000002,0.000000,0.000003,0.000002]]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int pathBufferAppend(const std::string &name,
                         const std::vector<std::vector<double>> &waypoints);

    /**
     * @ingroup MotionControl
     * \chinese
     * 计算、优化等耗时操作，传入的参数相同时不会重新计算
     *
     * @param name 通过pathBufferAlloc新建的路径点缓存的名字
     * @param a 关节加速度限制,需要和机器人自由度大小相同,单位 rad/s^2
     * @param v 关节速度限制,需要和机器人自由度大小相同,单位 rad/s
     * @param t 时间 \n
     * pathBufferAlloc 这个接口分配内存的时候要指定类型，
     * 根据pathBufferAlloc这个接口的类型:\n
     * 类型为1时,表示运动持续时间\n
     * 类型为2时,表示采样时间间隔\n
     * 类型为3时:t表示运动持续时间\n
     *     若 t=0,　则由使用软件内部默认的时间(推荐使用)\n
     *     若 t!=0, t需要设置为　路径点数*相邻点时间间隔(points *
     * interval,interval >= 0.01)
     * @return 成功返回0；失败返回错误码
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBufferEval(self: pyaubo_sdk.MotionControl, arg0: str, arg1:
     * List[float], arg2: List[float], arg3: float) -> int
     *
     * @par Lua函数原型
     * pathBufferEval(name: string, a: table, v: table, t: number) -> nil
     *
     * @par Lua示例
     * pathBufferEval("traje_name",{1,1,1,1,1,1},{1,1,1,1,1,1},0.02)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferEval","params":["rec",[1,1,1,1,1,1],[1,1,1,1,1,1],0.02],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Perform computation and optimization (time-consuming operations). If the
     * input parameters are the same, the calculation will not be repeated.
     *
     * @param name Name of the path point buffer created by pathBufferAlloc
     * @param a Joint acceleration limits, must match the robot DOF, unit:
     * rad/s^2
     * @param v Joint velocity limits, must match the robot DOF, unit: rad/s
     * @param t Time \n
     * When allocating memory with pathBufferAlloc, the type must be specified.
     * According to the type in pathBufferAlloc:\n
     * Type 1: t means motion duration\n
     * Type 2: t means sampling interval\n
     * Type 3: t means motion duration\n
     *     If t=0, the internal default time is used (recommended)\n
     *     If t!=0, t should be set to number_of_points *
     * interval_between_points (interval >= 0.01)
     * @return Returns 0 on success; otherwise returns an error code
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBufferEval(self: pyaubo_sdk.MotionControl, arg0: str, arg1:
     * List[float], arg2: List[float], arg3: float) -> int
     *
     * @par Lua function prototype
     * pathBufferEval(name: string, a: table, v: table, t: number) -> nil
     *
     * @par Lua example
     * pathBufferEval("traje_name",{1,1,1,1,1,1},{1,1,1,1,1,1},0.02)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferEval","params":["rec",[1,1,1,1,1,1],[1,1,1,1,1,1],0.02],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int pathBufferEval(const std::string &name, const std::vector<double> &a,
                       const std::vector<double> &v, double t);

    /**
     * @ingroup MotionControl
     * \chinese
     * 指定名字的buffer是否有效
     *
     * buffer需要满足三个条件有效: \n
     * 1、buffer存在，已经分配过内存 \n
     * 2、传进buffer的点要大于等于buffer的大小 \n
     * 3、要执行一次pathBufferEval
     *
     * @param name buffer的名字
     * @return 有效返回true; 无效返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBufferValid(self: pyaubo_sdk.MotionControl, arg0: str) -> bool
     *
     * @par Lua函数原型
     * pathBufferValid(name: string) -> boolean
     *
     * @par Lua示例
     * buffer_status = pathBufferValid("traje_name")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferValid","params":["rec"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     * \english
     * Whether the buffer with the specified name is valid
     *
     * The buffer must meet three conditions to be valid: \n
     * 1. The buffer exists and memory has been allocated \n
     * 2. The number of points passed into the buffer must be greater than or
     * equal to the buffer size \n
     * 3. pathBufferEval must be executed once
     *
     * @param name Name of the buffer
     * @return Returns true if valid; false otherwise
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBufferValid(self: pyaubo_sdk.MotionControl, arg0: str) -> bool
     *
     * @par Lua function prototype
     * pathBufferValid(name: string) -> boolean
     *
     * @par Lua example
     * buffer_status = pathBufferValid("traje_name")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferValid","params":["rec"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool pathBufferValid(const std::string &name);

    /**
     * @ingroup MotionControl
     * \chinese
     * 释放路径缓存
     *
     * @param name 缓存路径的名字
     * @return 成功返回0；失败返回错误码
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBufferFree(self: pyaubo_sdk.MotionControl, arg0: str) -> int
     *
     * @par Lua函数原型
     * pathBufferFree(name: string) -> nil
     *
     * @par Lua示例
     * pathBufferFree("traje_name")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferFree","params":["rec"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-5}
     *
     * \endchinese
     * \english
     * Release path buffer
     *
     * @param name Name of the path buffer
     * @return Returns 0 on success; otherwise returns an error code
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBufferFree(self: pyaubo_sdk.MotionControl, arg0: str) -> int
     *
     * @par Lua function prototype
     * pathBufferFree(name: string) -> nil
     *
     * @par Lua example
     * pathBufferFree("traje_name")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferFree","params":["rec"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-5}
     *
     * \endenglish
     */
    int pathBufferFree(const std::string &name);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节空间路径滤波器
     *
     * @brief pathBufferFilter
     *
     * @param name 缓存路径的名称
     * @param order　滤波器阶数(一般取2)
     * @param fd　截止频率，越小越光滑，但是延迟会大(一般取3-20)
     * @param fs　离散数据的采样频率(一般取20-500)
     *
     * @return 成功返回0
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBufferFilter(self: pyaubo_sdk.MotionControl, arg0: str, arg1: int,
     * arg2: float, arg3: float) -> int
     *
     * @par Lua函数原型
     * pathBufferFilter(name: string, order: number, fd: number, fs:number) ->
     * nil
     *
     * @par Lua示例
     * pathBufferFilter("traje_name",2,5,125)
     *
     * \endchinese
     * \english
     * Joint space path filter
     *
     * @brief pathBufferFilter
     *
     * @param name Name of the path buffer
     * @param order Filter order (usually 2)
     * @param fd Cutoff frequency, the smaller the smoother but with more delay
     * (usually 3-20)
     * @param fs Sampling frequency of discrete data (usually 20-500)
     *
     * @return Returns 0 on success
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBufferFilter(self: pyaubo_sdk.MotionControl, arg0: str, arg1: int,
     * arg2: float, arg3: float) -> int
     *
     * @par Lua function prototype
     * pathBufferFilter(name: string, order: number, fd: number, fs:number) ->
     * nil
     *
     * @par Lua example
     * pathBufferFilter("traje_name",2,5,125)
     *
     * \endenglish
     */
    int pathBufferFilter(const std::string &name, int order, double fd,
                         double fs);

    /**
     * @ingroup MotionControl
     * \chinese
     * 列出所有缓存路径的名字
     *
     * @return 返回所有缓存路径的名字
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBufferList(self: pyaubo_sdk.MotionControl) -> List[str]
     *
     * @par Lua函数原型
     * pathBufferList() -> table
     *
     * @par Lua示例
     * Buffer_table = pathBufferList()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferList","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endchinese
     * \english
     * List all cached path names
     *
     * @return Returns all cached path names
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBufferList(self: pyaubo_sdk.MotionControl) -> List[str]
     *
     * @par Lua function prototype
     * pathBufferList() -> table
     *
     * @par Lua example
     * Buffer_table = pathBufferList()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.pathBufferList","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endenglish
     */
    std::vector<std::string> pathBufferList();

    /**
     * @ingroup MotionControl
     * \chinese
     * 执行缓存的路径
     *
     * @param name 缓存路径的名字
     * @return 成功返回0；失败返回错误码
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * movePathBuffer(self: pyaubo_sdk.MotionControl, arg0: str) -> int
     *
     * @par Lua函数原型
     * movePathBuffer(name: string) -> nil
     *
     * @par Lua示例
     * movePathBuffer("traje_name")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.movePathBuffer","params":["rec"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Execute the cached path
     *
     * @param name Name of the cached path
     * @return Returns 0 on success; otherwise returns an error code
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * movePathBuffer(self: pyaubo_sdk.MotionControl, arg0: str) -> int
     *
     * @par Lua function prototype
     * movePathBuffer(name: string) -> nil
     *
     * @par Lua example
     * movePathBuffer("traje_name")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.movePathBuffer","params":["rec"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int movePathBuffer(const std::string &name);

    /**
     * @ingroup MotionControl
     * \chinese
     * 相贯线接口
     *
     * @param pose 由三个示教位姿组成(首先需要运动到起始点,起始点的要求:过主圆柱
     *            柱体轴心且与子圆柱体轴线平行的平面与子圆柱体在底部的交点)
     * p1:过子圆柱体轴线且与大圆柱体轴线平行的平面,与小圆柱体在左侧顶部的交点
     * p2:过子圆柱体轴线且与大圆柱体轴线平行的平面,与大圆柱体在左侧底部的交点
     * p3:过子圆柱体轴线且与大圆柱体轴线平行的平面,与大圆柱体在右侧底部的交点
     * @param v 速度
     * @param a 加速度
     * @param main_pipe_radius 主圆柱体半径
     * @param sub_pipe_radius  子圆柱体半径
     * @param normal_distance  两圆柱体轴线距离
     * @param normal_alpha     两圆柱体轴线的夹角
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
     * moveIntersection(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float, arg4: float, arg5: float, arg6: float)
     * -> int
     *
     * @par Lua函数原型
     * moveIntersection(poses: table, a: number, v: number,
     * main_pipe_radius: number, sub_pipe_radius: number, normal_distance:
     * number, normal_alpha: number) -> nil \endchinese \english Intersection
     * interface
     *
     * @param poses Consists of three taught poses (first, move to the starting
     * point. The starting point requirement: the intersection of the plane
     * passing through the main cylinder axis and parallel to the sub-cylinder
     * axis with the sub-cylinder at the bottom) p1: Intersection of the plane
     * passing through the sub-cylinder axis and parallel to the main cylinder
     * axis with the sub-cylinder at the left top p2: Intersection of the plane
     * passing through the sub-cylinder axis and parallel to the main cylinder
     * axis with the main cylinder at the left bottom p3: Intersection of the
     * plane passing through the sub-cylinder axis and parallel to the main
     * cylinder axis with the main cylinder at the right bottom
     * @param v Velocity
     * @param a Acceleration
     * @param main_pipe_radius Main cylinder radius
     * @param sub_pipe_radius  Sub cylinder radius
     * @param normal_distance  Distance between the two cylinder axes
     * @param normal_alpha     Angle between the two cylinder axes
     *
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * moveIntersection(self: pyaubo_sdk.MotionControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: float, arg4: float, arg5: float, arg6: float)
     * -> int
     *
     * @par Lua function prototype
     * moveIntersection(poses: table, a: number, v: number,
     * main_pipe_radius: number, sub_pipe_radius: number, normal_distance:
     * number, normal_alpha: number) -> nil \endenglish
     */
    int moveIntersection(const std::vector<std::vector<double>> &poses,
                         double a, double v, double main_pipe_radius,
                         double sub_pipe_radius, double normal_distance,
                         double normal_alpha);
    /**
     * @ingroup MotionControl
     * \chinese
     * 关节空间停止运动
     *
     * @param acc 关节加速度，单位: rad/s^2
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * stopJoint(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua函数原型
     * stopJoint(acc: number) -> nil
     *
     * @par Lua示例
     * stopJoint(2)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.stopJoint","params":[31],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Stop motion in joint space
     *
     * @param acc Joint acceleration, unit: rad/s^2
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * stopJoint(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua function prototype
     * stopJoint(acc: number) -> nil
     *
     * @par Lua example
     * stopJoint(2)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.stopJoint","params":[31],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int stopJoint(double acc);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关节空间停止运动(机械臂运行工程时发生碰撞,通过resumeSpeedJoint接口移动到安全位置后需要停止时调用此接口)
     *
     * @param acc 关节加速度，单位: rad/s^2
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resumeStopJoint(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua函数原型
     * resumeStopJoint(acc: number) -> nil
     *
     * @par Lua示例
     * resumeStopJoint(31)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeStopJoint","params":[31],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endchinese
     * \english
     * Stop motion in joint space (used after moving to a safe position via
     * resumeSpeedJoint following a collision during process execution)
     *
     * @param acc Joint acceleration, unit: rad/s^2
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * resumeStopJoint(self: pyaubo_sdk.MotionControl, arg0: float) -> int
     *
     * @par Lua function prototype
     * resumeStopJoint(acc: number) -> nil
     *
     * @par Lua example
     * resumeStopJoint(31)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeStopJoint","params":[31],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endenglish
     */
    int resumeStopJoint(double acc);

    /**
     * @ingroup MotionControl
     * \chinese
     * 停止 moveLine/moveCircle 等在笛卡尔空间的运动
     *
     * @param acc 工具加速度, 单位: m/s^2
     * @param acc_rot
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * stopLine(self: pyaubo_sdk.MotionControl, arg0: float, arg1: float) -> int
     *
     * @par Lua函数原型
     * stopLine(acc: number, acc_rot: number) -> nil
     *
     * @par Lua示例
     * stopLine(10,10)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.stopLine","params":[10,10],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Stop motions in Cartesian space such as moveLine/moveCircle.
     *
     * @param acc Tool acceleration, unit: m/s^2
     * @param acc_rot
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * stopLine(self: pyaubo_sdk.MotionControl, arg0: float, arg1: float) -> int
     *
     * @par Lua function prototype
     * stopLine(acc: number, acc_rot: number) -> nil
     *
     * @par Lua example
     * stopLine(10,10)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.stopLine","params":[10,10],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int stopLine(double acc, double acc_rot);

    /**
     * @ingroup MotionControl
     * \chinese
     * 笛卡尔空间停止运动(机械臂运行工程时发生碰撞,通过resumeSpeedLine接口移动到安全位置后需要停止时调用此接口)
     *
     * @param acc 位置加速度, 单位: m/s^2
     * @param acc_rot 姿态加速度，单位: rad/s^2
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resumeStopLine(self: pyaubo_sdk.MotionControl, arg0: float, arg1: float)
     * -> int
     *
     * @par Lua函数原型
     * resumeStopLine(acc: number, acc_rot: number) -> nil
     *
     * @par Lua示例
     * resumeStopLine(10,10)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeStopLine","params":[10,10],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endchinese
     * \english
     * Stop motion in Cartesian space (used after moving to a safe position via
     * resumeSpeedLine following a collision during process execution)
     *
     * @param acc Position acceleration, unit: m/s^2
     * @param acc_rot Orientation acceleration, unit: rad/s^2
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * resumeStopLine(self: pyaubo_sdk.MotionControl, arg0: float, arg1: float)
     * -> int
     *
     * @par Lua function prototype
     * resumeStopLine(acc: number, acc_rot: number) -> nil
     *
     * @par Lua example
     * resumeStopLine(10,10)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resumeStopLine","params":[10,10],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endenglish
     */
    int resumeStopLine(double acc, double acc_rot);

    /**
     * @ingroup MotionControl
     * \chinese
     *
     * \warning 调用 weaveStart 前，需提前开启 RuntimeMachine 规划器 start。
     *
     * 开始摆动：在 weaveStart 与 weaveEnd 之间的
     * moveLine/moveCircle/moveProcess 根据 params 执行摆动。
     *
     * @param params Json 字符串。
     *
     * @par 自 v0.29 起的字段
     * - "type": <string>                          —— 波形类型："SINE" |
     * "SPIRAL" | "TRIANGLE" | "TRAPEZOIDAL"（区分大小写）。
     * - "step": <number>                          ——
     * 相邻摆动采样的弧长步长，单位 m。
     * - "amplitude": [<number>,<number>]          —— 摆弧幅度左右侧，单位 m。
     * - "hold_distance": [<number>,<number>]      ——
     * 在幅度峰值处沿路径的停留距离，单位 m。
     * - "hold_time": [<number>,<number>]          ——
     * 在幅度峰值处的停留时间，单位 s。
     * - "angle": <number>                         ——
     * 叠加方向与法平面的夹角，单位 rad。
     * - "direction": <integer>                    ——
     * 起始摆动方向：0=上方，1=下方。
     * - "movep_uniform_vel": <bool>               —— moveProcess
     * 匀速规划，布尔量。
     *
     * @par 自 v0.31 起
     * - 与 v0.29 相同。
     *
     * @par 自 v0.32 起新增/变更
     * - "angle": [<number>,<number>]   ——运动叠加方向与法平面的夹角，单位 rad。
     * - "frequency": <number>          —— 摆动频率，单位 Hz（范围[0.1, 5]）。
     * - "ori_weave_range": [<number>,<number>,<number>]     —— 姿态摆动范围
     * [x,y,z]，单位 rad；常与阿基米德螺旋用于力控搜孔。
     * - "ori_weave_frequency": [<number>,<number>,<number>] —— 姿态摆动频率
     * [x,y,z]，单位 m^-1（按路径弧长计；范围 [0, 1]）。
     * - "adjust_cycle_num": <integer>             ——
     * 动态调节频率/幅值的过渡段数量。
     * - "azimuth": <number>                       —— 摆焊波形方位角，单位 rad。
     * - "ridge_height": <number>                  —— 中心上升高度，单位 m。
     *
     * \warning 可使用关系 **frequency = vel / step** 与外部速度 vel 关联（vel
     * 单位 m·s^-1）。
     * \warning **hold_time** 仅在 **SINE**下可用，且可左右不对称。
     * \warning "hold_distance"/"hold_time" 互斥，仅一个生效
     *
     * \note
     * - 数组约定："amplitude"/"hold_distance"/"hold_time" 为
     * [left,right]；"ori_weave_*" 为姿态 [x,y,z]。
     * - 所有角度均为弧度（rad）。
     *
     * @return 成功返回0; 失败返回错误码
     * - AUBO_BUSY
     * - AUBO_BAD_STATE
     * - -AUBO_INVL_ARGUMENT
     * - -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par 示例 v0.29/v0.31
     * \code{.json}
     * params = {
     *     "type": "SINE",
     *     "step": 0.005,
     *     "amplitude": [0.01, 0.01],
     *     "hold_distance": [0.001, 0.001],
     *     "hold_time": [0, 0],
     *     "angle": 0,
     *     "direction": 0,
     *     "movep_uniform_vel": false
     * }
     * \endcode
     *
     * @par 示例 v0.32
     * \code{.json}
     * params = {
     *     "type" : "SINE",  // "SINE" "SPIRAL" "TRIANGLE" "SAWTOOTH" "CRESCENT"
     *     "step" : 0.0,     // 可用 frequency = vel / step（vel: m·s^-1）
     *     "frequency" : 0.0, // [0.1, 5] Hz
     *     "amplitude" : [0.01, 0.01],               // m
     *     "hold_distance" : [0.001, 0.001],         // m
     *     "hold_time" : [0, 0],                     // s（仅 SINE）
     *     "angle" : [0, 0],                         // rad
     *     "direction" : 0,
     *     "ori_weave_range" : [0.001, 0.001, 0.001],          // rad
     *     "ori_weave_frequency": [0.001, 0.001, 0.001],       // m^-1
     *     "adjust_cycle_num": 0,
     *     "azimuth" : 0,                             // rad
     *     "ridge_height" : 0                         // m
     * }
     * \endcode
     *
     * @par Python 函数原型
     * \code{.py}
     * weaveStart(self: pyaubo_sdk.MotionControl, arg0: str) -> int
     * \endcode
     *
     * @par Python 示例
     * \code{.py}
     * robot_name = rpc_cli.getRobotNames()[0]
     * robot_interface = rpc_cli.getRobotInterface(robot_name)
     * robot_interface.getMotionControl().weaveStart(params)
     * \endcode
     *
     * @par Lua 函数原型
     * \code{.lua}
     * weaveStart(params: string) -> nil
     * \endcode
     *
     * @par Lua 示例（v0.29/0.31）
     * \code{.lua}
     * weaveStart("{\"type\":\"SINE\",\"step\":0.005,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"movep_uniform_vel\":false}")
     * \endcode
     *
     * @par Lua 示例（v0.32）
     * \code{.lua}
     * weaveStart("{\"type\":\"SINE\",\"step\":0.0,\"frequency\":2.0,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"ori_weave_range\":[0.001,0.001,0.001],\"ori_weave_frequency\":[0.001,0.001,0.001],\"adjust_cycle_num\":0,\"azimuth\":0,\"ridge_height\":0}")
     * \endcode
     *
     * @par JSON-RPC 请求示例（v0.29/0.31）
     * \code{.json}
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.weaveStart","params":["{\"type\":\"SINE\",\"step\":0.005,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"movep_uniform_vel\":false}"],"id":1}
     * \endcode
     *
     * @par JSON-RPC 请求示例（v0.32）
     * \code{.json}
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.weaveStart","params":["{\"type\":\"SINE\",\"step\":0.0,\"frequency\":2.0,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"ori_weave_range\":[0.001,0.001,0.001],\"ori_weave_frequency\":[0.001,0.001,0.001],\"adjust_cycle_num\":0,\"azimuth\":0,\"ridge_height\":0}"],"id":1}
     * \endcode
     *
     * @par JSON-RPC 响应示例
     * \code{.json}
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endcode
     * \endchinese
     *
     * \english
     * Start weaving: between weaveStart and weaveEnd,
     * moveLine/moveCircle/moveProcess follows params.
     *
     * \warning Start RuntimeMachine before calling weaveStart.
     *
     * @param params Json string.
     *
     * @par Since v0.29
     * - "type": <string>                          — Waveform: "SINE" | "SPIRAL"
     * | "TRIANGLE" | "TRAPEZOIDAL" (case-sensitive).
     * - "step": <number>                          — Arc-length sampling step,
     * m.
     * - "amplitude": [<number>,<number>]          — Left/right weave amplitude,
     * m.
     * - "hold_distance": [<number>,<number>]      — Dwell distance at peak
     * amplitude along path, m.
     * - "hold_time": [<number>,<number>]          — Dwell time at peak
     * amplitude, s.
     * - "angle": <number>                         — Angle to normal plane, rad.
     * - "direction": <integer>                    — Initial direction: 0=above
     * path, 1=below path.
     * - "movep_uniform_vel": <bool>               — Uniform-velocity planning
     * (boolean value).
     *
     * @par Since v0.31
     * - Same as v0.29.
     *
     * @par New/changed in v0.32
     * - "frequency": <number>                     — Weave frequency, Hz (range
     * [0.1, 5]).
     * - "ori_weave_range": [<number>,<number>,<number>]     — Attitude weave
     * range [x,y,z], rad; often used with Archimedean spiral for force-guided
     * hole finding.
     * - "ori_weave_frequency": [<number>,<number>,<number>] — Attitude weave
     * frequency [x,y,z], m^-1 (per unit arc; range [0, 1]).
     * - "adjust_cycle_num": <integer>             — Number of transition
     * cycles.
     * - "azimuth": <number>                       — Waveform azimuth, rad.
     * - "ridge_height": <number>                  — Center raise height, m.
     *
     * \warning **hold_time** is supported for **SINE** only and may be
     * asymmetric. \warning You may relate **frequency = vel / step** when an
     * external path speed vel (m·s^-1) is available.
     *
     * \note
     * - Two-element arrays are [left,right]; three-element arrays are attitude
     * [x,y,z].
     * - All angles are in radians (rad).
     *
     * @return Returns 0 on success; otherwise returns an error code:
     * - AUBO_BUSY
     * - AUBO_BAD_STATE
     * - -AUBO_INVL_ARGUMENT
     * - -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Example v0.29/v0.31
     * \code{.json}
     * params = {
     *     "type": "SINE",
     *     "step": 0.005,
     *     "amplitude": [0.01, 0.01],
     *     "hold_distance": [0.001, 0.001],
     *     "hold_time": [0, 0],
     *     "angle": 0,
     *     "direction": 0,
     *     "movep_uniform_vel": false
     * }
     * \endcode
     *
     * @par Example v0.32
     * \code{.json}
     * params = {
     *     "type" : "SINE",  // "SINE" "SPIRAL" "TRIANGLE" "TRAPEZOIDAL"
     *     "step" : 0.0,     // frequency = vel / step (vel: m·s^-1)
     *     "frequency" : 0.0, // [0.1, 5] Hz
     *     "amplitude" : [0.01, 0.01],               // m
     *     "hold_distance" : [0.001, 0.001],         // m
     *     "hold_time" : [0, 0],                     // s (SINE only)
     *     "angle" : 0,                               // rad
     *     "direction" : 0,
     *     "ori_weave_range" : [0.001, 0.001, 0.001],          // rad
     *     "ori_weave_frequency": [0.001, 0.001, 0.001],       // m^-1
     *     "adjust_cycle_num": 0,
     *     "azimuth" : 0,                             // rad
     *     "ridge_height" : 0                         // m
     * }
     * \endcode
     *
     * @par Python function prototype
     * \code{.py}
     * weaveStart(self: pyaubo_sdk.MotionControl, arg0: str) -> int
     * \endcode
     *
     * @par Python example
     * \code{.py}
     * robot_name = rpc_cli.getRobotNames()[0]
     * robot_interface = rpc_cli.getRobotInterface(robot_name)
     * robot_interface.getMotionControl().weaveStart(params)
     * \endcode
     *
     * @par Lua function prototype
     * \code{.lua}
     * weaveStart(params: string) -> nil
     * \endcode
     *
     * @par Lua example (v0.29/0.31)
     * \code{.lua}
     * weaveStart("{\"type\":\"SINE\",\"step\":0.005,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"movep_uniform_vel\":false}")
     * \endcode
     *
     * @par Lua example (v0.32)
     * \code{.lua}
     * weaveStart("{\"type\":\"SINE\",\"step\":0.0,\"frequency\":2.0,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"ori_weave_range\":[0.001,0.001,0.001],\"ori_weave_frequency\":[0.001,0.001,0.001],\"adjust_cycle_num\":0,\"azimuth\":0,\"ridge_height\":0}")
     * \endcode
     *
     * @par JSON-RPC request example (v0.29/0.31)
     * \code{.json}
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.weaveStart","params":["{\"type\":\"SINE\",\"step\":0.005,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"movep_uniform_vel\":false}"],"id":1}
     * \endcode
     *
     * @par JSON-RPC request example (v0.32)
     * \code{.json}
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.weaveStart","params":["{\"type\":\"SINE\",\"step\":0.0,\"frequency\":2.0,\"amplitude\":[0.01,0.01],\"hold_distance\":[0.001,0.001],\"hold_time\":[0,0],\"angle\":0,\"direction\":0,\"ori_weave_range\":[0.001,0.001,0.001],\"ori_weave_frequency\":[0.001,0.001,0.001],\"adjust_cycle_num\":0,\"azimuth\":0,\"ridge_height\":0}"],"id":1}
     * \endcode
     *
     * @par JSON-RPC response example
     * \code{.json}
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endcode
     * \endenglish
     */
    int weaveStart(const std::string &params);

    /**
     * @ingroup MotionControl
     * \chinese
     * 结束摆动
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.weaveEnd","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * End weaving
     *
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.weaveEnd","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int weaveEnd();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置未来路径上点的采样时间间隔
     *
     * @param sample_time 采样时间间隔 单位: m/s^2
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Set the sampling interval for points on the future path
     *
     * @param sample_time Sampling interval, unit: m/s^2
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int setFuturePointSamplePeriod(double sample_time);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取未来路径上的轨迹点
     *
     * @return 路点(100ms * 10)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getFuturePathPointsJoint","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endchinese
     * \english
     * Get trajectory points on the future path
     *
     * @return Waypoints (100ms * 10)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getFuturePathPointsJoint","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endenglish
     */
    std::vector<std::vector<double>> getFuturePathPointsJoint();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置传送带编码器参数
     *
     * @param encoder_id 预留
     * @param tick_per_meter
     * 线性传送带===>一米的脉冲值
     * 环形传送带===>一圈的脉冲值
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConveyorTrackEncoder(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * setConveyorTrackEncoder(encoder_id: bumber,tick_per_meter: number) -> int
     *
     * @par Lua示例
     * num = setConveyorTrackEncoder(1,40000)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackEncoder","params":[1,40000],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set conveyor encoder parameters
     *
     * @param encoder_id Reserved
     * @param tick_per_meter
     * Linear conveyor: pulses per meter
     * Circular conveyor: pulses per revolution
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConveyorTrackEncoder(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * setConveyorTrackEncoder(encoder_id: bumber,tick_per_meter: number) -> int
     *
     * @par Lua example
     * num = setConveyorTrackEncoder(1,40000)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackEncoder","params":[1,40000],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConveyorTrackEncoder(int encoder_id, int tick_per_meter);
    /**
     * @ingroup MotionControl
     * \chinese
     * 圆形传送带跟随
     *
     * @note 暂未实现
     *
     * @param encoder_id
     * 0-集成传感器
     * @param rotate_tool
     * @return
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Circular conveyor tracking
     *
     * @note Not implemented yet
     *
     * @param encoder_id
     * 0 - integrated sensor
     * @param rotate_tool
     * @return
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int conveyorTrackCircle(int encoder_id, const std::vector<double> &center,
                            bool rotate_tool);

    /**
     * @ingroup MotionControl
     * \chinese
     * 线性传送带跟随
     *
     * @param encoder_id 预留
     * @param direction 传送带相对机器人基坐标系的移动方向
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * conveyorTrackLine(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * conveyorTrackLine -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackLine","params":[1,[1.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Linear conveyor tracking
     *
     * @param encoder_id Reserved
     * @param direction The movement direction of the conveyor relative to the
     * robot base coordinate system
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * conveyorTrackLine(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * conveyorTrackLine -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackLine","params":[1,[1.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int conveyorTrackLine(int encoder_id, const std::vector<double> &direction);

    /**
     * @ingroup MotionControl
     * \chinese
     * 终止传送带跟随
     *
     * @param encoder_id 预留
     * @param a 预留
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * conveyorTrackStop(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * conveyorTrackStop -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackStop","params":[0,1.0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Stop conveyor tracking
     *
     * @param encoder_id Reserved
     * @param a Reserved
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * conveyorTrackStop(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * conveyorTrackStop -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackStop","params":[0,1.0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int conveyorTrackStop(int encoder_id, double a);

    /**
     * @ingroup MotionControl
     * \chinese
     * 切换传送带追踪物品
     * 如果当前物品正在处于跟踪状态，则将该物品出队，不再跟踪，返回true
     * 如果没有物品正在处于跟踪状态，返回false
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @param encoder_id 预留
     *
     * @par Python函数原型
     * conveyorTrackSwitch(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua函数原型
     * conveyorTrackSwitch() -> boolean
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackSwitch","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Switch conveyor tracking item.
     * If the current item is being tracked, it will be dequeued and no longer
     * tracked, returning true. If no item is currently being tracked, returns
     * false.
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @param encoder_id Reserved
     *
     * @par Python function prototype
     * conveyorTrackSwitch(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua function prototype
     * conveyorTrackSwitch() -> boolean
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackSwitch","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool conveyorTrackSwitch(int encoder_id);

    /**
     * @ingroup MotionControl
     * \chinese
     * 传送带上是否有物品可以跟踪
     * @param encoder_id 预留
     * @return
     * 如果队列第一个物品为跟踪状态，返回true
     * 如果队列第一个物品不为跟踪状态，则对队列中其余物品进行是否在启动窗口内的判断
     * 超出启动窗口则出队，直到有物品处于启动窗口内，使其变为跟踪状态返回true，
     * 队列中没有一个物品在启动窗口内返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * hasItemOnConveyorToTrack(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua函数原型
     * hasItemOnConveyorToTrack() -> boolean
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.hasItemOnConveyorToTrack","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":{true}}
     * \endchinese
     * \english
     * Whether there is an item on the conveyor that can be tracked
     * @param encoder_id Reserved
     * @return
     * If the first item in the queue is in tracking state, returns true.
     * If the first item is not in tracking state, checks the rest of the queue
     * for items within the start window. Items outside the start window are
     * dequeued until an item is found within the window, which is then set to
     * tracking state and returns true. If no item in the queue is within the
     * start window, returns false.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * hasItemOnConveyorToTrack(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua function prototype
     * hasItemOnConveyorToTrack() -> boolean
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.hasItemOnConveyorToTrack","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":{true}}
     * \endenglish
     */
    bool hasItemOnConveyorToTrack(int encoder_id);

    /**
     * @ingroup MotionControl
     * \chinese
     * 增加传送带队列
     *
     * @param encoder_id 预留
     * @param item_id 物品ID
     * @param offset 当前物品点位相对于模板物品点位的偏移值
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * conveyorTrackCreatItem(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1:int, arg2: List[float]) -> int
     *
     * @par Lua函数原型
     * conveyorTrackCreatItem(encoder_id: number, item_id: number, offset:
     * table) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackCreatItem","params":[0,2,
     * {0.0,0.0,0.0,0.0,0.0,0.0}],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endchinese
     * \english
     * Add an item to the conveyor queue
     *
     * @param encoder_id Reserved
     * @param item_id Item ID
     * @param offset Offset of the current item position relative to the
     * template item position
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * conveyorTrackCreatItem(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1:int, arg2: List[float]) -> int
     *
     * @par Lua function prototype
     * conveyorTrackCreatItem(encoder_id: number, item_id: number, offset:
     * table) -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackCreatItem","params":[0,2,
     * {0.0,0.0,0.0,0.0,0.0,0.0}],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endenglish
     */
    int conveyorTrackCreatItem(int encoder_id, int item_id,
                               const std::vector<double> &offset);
    /**
     * @ingroup MotionControl
     * \chinese
     * 设置传送带跟踪的补偿值
     *
     * @param encoder_id 预留
     * @param comp 传送带补偿值
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConveyorTrackCompensate(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: float) -> int
     *
     * @par Lua函数原型
     * setConveyorTrackCompensate(comp: number) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackCompensate","params":[0,
     * 0.1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the compensation value for conveyor tracking
     *
     * @param encoder_id Reserved
     * @param comp Conveyor compensation value
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConveyorTrackCompensate(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: float) -> int
     *
     * @par Lua function prototype
     * setConveyorTrackCompensate(comp: number) -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackCompensate","params":[0,
     * 0.1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setConveyorTrackCompensate(int encoder_id, double comp);

    /**
     * @ingroup MotionControl
     * \chinese
     * 判断传送带与机械臂之间是否达到相对静止
     *
     * @param encoder_id 预留
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isConveyorTrackSync(self: pyaubo_sdk.MotionControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * isConveyorTrackSync(encoder_id: number) -> bool
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isConveyorTrackSync","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Determine whether the conveyor and the robot arm have reached relative
     * rest
     *
     * @param encoder_id Reserved
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isConveyorTrackSync(self: pyaubo_sdk.MotionControl, arg0: int) -> bool
     *
     * @par Lua function prototype
     * isConveyorTrackSync(encoder_id: number) -> bool
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isConveyorTrackSync","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool isConveyorTrackSync(int encoder_id);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置传送带跟踪的最大距离限制
     *
     * @param encoder_id 预留
     * @param limit
     * 传送带跟踪的最大距离限制,单位：米
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConveyorTrackLimit(self: pyaubo_sdk.MotionControl, arg0: int, arg1:
     * double) -> int
     *
     * @par Lua函数原型
     * setConveyorTrackLimit(encoder_id: number, limit: number) -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackLimit","params":[0,
     * 1.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the maximum distance limit for conveyor tracking
     *
     * @param encoder_id Reserved
     * @param limit
     * Maximum distance limit for conveyor tracking, unit: meter
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConveyorTrackLimit(self: pyaubo_sdk.MotionControl, arg0: int, arg1:
     * double) -> int
     *
     * @par Lua function prototype
     * setConveyorTrackLimit(encoder_id: number, limit: number) -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackLimit","params":[0,
     * 1.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setConveyorTrackLimit(int encoder_id, double limit);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置传送带跟踪的启动窗口
     *
     * @param encoder_id 预留
     * @param min_window
     * 启动窗口的起始位置,单位：米
     * @param max_window
     * 启动窗口的结束位置,单位：米
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConveyorTrackStartWindow(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double, arg2: double) -> int
     *
     * @par Lua函数原型
     * setConveyorTrackStartWindow(encoder_id: number, min_window: number,
     * max_window: number) -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackStartWindow","params":[0,
     * 0.2, 1.0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the start window for conveyor tracking
     *
     * @param encoder_id Reserved
     * @param min_window
     * Start position of the window, unit: meter
     * @param max_window
     * End position of the window, unit: meter
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConveyorTrackStartWindow(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double, arg2: double) -> int
     *
     * @par Lua function prototype
     * setConveyorTrackStartWindow(encoder_id: number, min_window: number,
     * max_window: number) -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackStartWindow","params":[0,
     * 0.2, 1.0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConveyorTrackStartWindow(int encoder_id, double window_min,
                                    double window_max);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置传送带示教位置到同步开关之间的距离
     *
     * @param encoder_id 预留
     * @param offset
     * 传送带示教位置到同步开关之间的距离,单位：米
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConveyorTrackSensorOffset(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double) -> int
     *
     * @par Lua函数原型
     * setConveyorTrackSensorOffset(encoder_id: number, offset: number) -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackSensorOffset","params":[0,
     * 0.2],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the distance from the conveyor teaching position to the sync switch
     *
     * @param encoder_id Reserved
     * @param offset
     * Distance from the conveyor teaching position to the sync switch, unit:
     * meter
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConveyorTrackSensorOffset(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double) -> int
     *
     * @par Lua function prototype
     * setConveyorTrackSensorOffset(encoder_id: number, offset: number) -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackSensorOffset","params":[0,
     * 0.2],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConveyorTrackSensorOffset(int encoder_id, double offset);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置传送带同步分离，用于过滤掉同步开关中不需要的信号
     *
     * @param encoder_id 预留
     * @param distance
     * 从出现一个同步信号后到把一个新的同步信号接受为一个有效对象前走的最短距离,单位：米
     * @param time
     * 从出现一个同步信号后到把一个新的同步信号接受为一个有效对象前走的最短时间,单位：秒
     *
     * distance和time设置数值大于0即为生效
     * 当distance与time同时设置时，优先生效distance
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConveyorTrackSyncSeparation(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double, arg2: double) -> int
     *
     * @par Lua函数原型
     * setConveyorTrackSyncSeparation(encoder_id: number, distance: number,
     * time: number) -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackSyncSeparation","params":[0,
     * 0.05, 0.2],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set conveyor sync separation, used to filter out unwanted signals from
     * the sync switch.
     *
     * @param encoder_id Reserved
     * @param distance
     * The minimum distance to travel after a sync signal appears before
     * accepting a new sync signal as a valid object, unit: meter
     * @param time
     * The minimum time to elapse after a sync signal appears before accepting a
     * new sync signal as a valid object, unit: second
     *
     * If distance and time are both set greater than 0, the setting takes
     * effect. If both distance and time are set, distance takes precedence.
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConveyorTrackSyncSeparation(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double, arg2: double) -> int
     *
     * @par Lua function prototype
     * setConveyorTrackSyncSeparation(encoder_id: number, distance: number,
     * time: number) -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackSyncSeparation","params":[0,
     * 0.05, 0.2],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setConveyorTrackSyncSeparation(int encoder_id, double distance,
                                       double time);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置传送带运行速度阈值，用于过滤掉编码器突变值导致的位置突变
     *
     * @param encoder_id 预留
     * @param threshold
     * 传送带运行时期望容许的最大速度(默认为0.2),单位：米/秒
     *
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConveyorTrackVelThreshold(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double) -> int
     *
     * @par Lua函数原型
     * setConveyorTrackVelThreshold(encoder_id: number, threshold: number) ->
     * int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackVelThreshold","params":[0,
     * 0.2],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set the conveyor velocity threshold used to suppress position jumps
     * caused by abnormal encoder spikes.
     *
     * @param encoder_id Reserved
     * @param threshold
     * The maximum allowable conveyor speed during operation, unit:
     * meter/second. Default: 0.2 m/s.
     *
     * @return
     * 0 on success; otherwise a non-zero error code.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConveyorTrackVelThreshold(self: pyaubo_sdk.MotionControl, arg0: int,
     * arg1: double) -> int
     *
     * @par Lua function prototype
     * setConveyorTrackVelThreshold(encoder_id: number, threshold: number) ->
     * int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setConveyorTrackVelThreshold","params":[0,
     * 0.2],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setConveyorTrackVelThreshold(int encoder_id, double threshold);

    /**
     * \chinese
     * 传送带上工件的移动距离是否超过最大限值
     *
     * @param encoder_id 预留
     * @return
     * true : 移动距离超过了最大限值
     * false : 移动距离没有超过了最大限值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isConveyorTrackExceed(self: pyaubo_sdk.MotionControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * isConveyorTrackExceed(encoder_id: number) -> bool
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isConveyorTrackExceed","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     * \english
     * Whether the workpiece on the conveyor has moved beyond the maximum limit
     *
     * @param encoder_id Reserved
     * @return
     * true : The movement distance exceeds the maximum limit
     * false : The movement distance does not exceed the maximum limit
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isConveyorTrackExceed(self: pyaubo_sdk.MotionControl, arg0: int) -> bool
     *
     * @par Lua function prototype
     * isConveyorTrackExceed(encoder_id: number) -> bool
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isConveyorTrackExceed","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool isConveyorTrackExceed(int encoder_id);

    /**
     * @ingroup MotionControl
     * \chinese
     * 清空传动带队列中的所有对象
     *
     * @param encoder_id 预留
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * conveyorTrackClearItems(self: pyaubo_sdk.MotionControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * conveyorTrackClearItems(encoder_id: number) -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackClearItems","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Clear all items in the conveyor queue
     *
     * @param encoder_id Reserved
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * conveyorTrackClearItems(self: pyaubo_sdk.MotionControl, arg0: int) -> int
     *
     * @par Lua function prototype
     * conveyorTrackClearItems(encoder_id: number) -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.conveyorTrackClearItems","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int conveyorTrackClearItems(int encoder_id);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取传送带队列的编码器值
     *
     * @param encoder_id 预留
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConveyorTrackQueue(self: pyaubo_sdk.MotionControl, arg0: int) ->
     * List[int]
     * @par Lua函数原型
     * getConveyorTrackQueue(encoder_id: number) -> table
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getConveyorTrackQueue","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":{[-500,-200,150,-50]}}
     * \endchinese
     * \english
     * Get encoder values of the conveyor queue
     *
     * @param encoder_id Reserved
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConveyorTrackQueue(self: pyaubo_sdk.MotionControl, arg0: int) ->
     * List[int]
     * @par Lua function prototype
     * getConveyorTrackQueue(encoder_id: number) -> table
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getConveyorTrackQueue","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":{[-500,-200,150,-50]}}
     * \endenglish
     */
    std::vector<int> getConveyorTrackQueue(int encoder_id);
    /**
     *  \chinese
     * 获取下一个跟踪的传送带物品的id
     *
     * @param encoder_id 预留
     * @return
     * 返回物品id，没有next item返回 -1
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     *  getConveyorTrackNextItem(self: pyaubo_sdk.MotionControl, arg0: int) ->
     * int
     * @par Lua函数原型
     *  getConveyorTrackNextItem(encoder_id: number) -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getConveyorTrackNextItem","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":{10}}
     * \endchinese
     * \english
     * Get the ID of the next item on the conveyor to be tracked
     *
     * @param encoder_id Reserved
     * @return
     * Returns the item ID; returns -1 if there is no next item
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     *  getConveyorTrackNextItem(self: pyaubo_sdk.MotionControl, arg0: int) ->
     * int
     * @par Lua function prototype
     *  getConveyorTrackNextItem(encoder_id: number) -> int
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getConveyorTrackNextItem","params":[0],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":{10}}
     * \endenglish
     */

    int getConveyorTrackNextItem(int encoder_id);

    /**
     * @ingroup MotionControl
     * \chinese
     * 螺旋线运动
     *
     * @param param 封装的参数
     * @param blend_radius
     * @param v
     * @param a
     * @param t
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveSpiral",
     * "params":[{"spiral":0.005,"helix":0.005,"angle":18.84,"plane":0,"frame":[0,0,0,0,0,0]},0,0.25,1.2,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Spiral motion
     *
     * @param param Encapsulated parameters
     * @param blend_radius
     * @param v
     * @param a
     * @param t
     * @return Returns 0 on success; otherwise returns an error code
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.moveSpiral",
     * "params":[{"spiral":0.005,"helix":0.005,"angle":18.84,"plane":0,"frame":[0,0,0,0,0,0]},0,0.25,1.2,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int moveSpiral(const SpiralParameters &param, double blend_radius, double v,
                   double a, double t);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取前瞻段数
     *
     * @return 返回前瞻段数
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getLookAheadSize(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * getLookAheadSize() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getLookAheadSize","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endchinese
     * \english
     * Get look-ahead segment size
     *
     * @return Returns the look-ahead segment size
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getLookAheadSize(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * getLookAheadSize() -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getLookAheadSize","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endenglish
     */
    int getLookAheadSize();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置前瞻段数
     * 1.对于有较高速度平稳性要求的任务,如数控加工,涂胶,焊接等匀速需求,较长的前瞻段数可以提供更优的速度规划,产生的运动会更加平滑;
     * 2.对于快速响应的抓取类任务,更倾向于较短的前瞻段数,以提高反应速度,但可能因为进给的路径不够及时导致速度波动很大.
     *
     * @return 成功返回0
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setLookAheadSize(self: pyaubo_sdk.MotionControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * setLookAheadSize(eqradius: number) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setLookAheadSize","params":[1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set look-ahead segment size
     * 1. For tasks requiring high speed smoothness, such as CNC machining,
     * gluing, welding, etc., a longer look-ahead segment size can provide
     * better speed planning and smoother motion.
     * 2. For fast-response tasks such as picking, a shorter look-ahead segment
     * size is preferred to improve response speed, but may cause large speed
     * fluctuations due to insufficiently timely path feeding.
     *
     * @return Returns 0 on success
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setLookAheadSize(self: pyaubo_sdk.MotionControl, arg0: int) -> int
     *
     * @par Lua function prototype
     * setLookAheadSize(eqradius: number) -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setLookAheadSize","params":[1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setLookAheadSize(int size);

    /**
     * @ingroup MotionControl
     * \chinese
     * 更新摆动过程中的频率和振幅
     *
     * @param params Json字符串用于定义摆动参数
     * {
     *   "frequency": <num>,
     *   "amplitude": {<num>,<num>}
     * }
     *
     * @return 成功返回0
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Update frequency and amplitude during weaving process
     *
     * @param params Json string used to define weaving parameters
     * {
     *   "frequency": <num>,
     *   "amplitude": {<num>,<num>}
     * }
     *
     * @return Returns 0 on success
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int weaveUpdateParameters(const std::string &params);

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置关节电流环刚度系数
     *
     * @param stiffness 各个关节刚度系数，百分比。[0 -> 1]，值越大，表现为越硬。
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * enableJointSoftServo(self: pyaubo_sdk.RobotConfig, arg0: List[float]) ->
     * int
     *
     * @par Lua函数原型
     * enableJointSoftServo(stiffness: table) -> int
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.enableJointSoftServo","params":[[0.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set joint current loop stiffness coefficient
     *
     * @param stiffness Stiffness coefficient for each joint, as a percentage [0
     * -> 1]. The larger the value, the stiffer the joint.
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * enableJointSoftServo(self: pyaubo_sdk.RobotConfig, arg0: List[float]) ->
     * int
     *
     * @par Lua function prototype
     * enableJointSoftServo(stiffness: table) -> int
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotConfig.enableJointSoftServo","params":[[0.0,0.0,0.0,0.0,0.0,0.0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int enableJointSoftServo(const std::vector<double> &stiffness);

    /**
     * @ingroup MotionControl
     * \chinese
     * 关闭关节电流环刚度系数
     *
     * @return 返回0表示成功，其他为错误码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * disableJointSoftServo(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * disableJointSoftServo() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.disableJointSoftServo","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endchinese
     * \english
     * Disable joint current loop stiffness coefficient
     *
     * @return Returns 0 on success, otherwise error code
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * disableJointSoftServo(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua function prototype
     * disableJointSoftServo() -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.disableJointSoftServo","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endenglish
     */
    int disableJointSoftServo();

    /**
     * @ingroup MotionControl
     * \chinese
     * 判断关节电流环刚度系数是否使能
     *
     * @return 已使能返回true，反之则返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isJointSoftServoEnabled(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua函数原型
     * isJointSoftServoEnabled() -> boolean
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isJointSoftServoEnabled","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endchinese
     * \english
     * Determine whether the joint current loop stiffness coefficient is
     * enabled.
     *
     * @return Returns true if enabled, otherwise returns false.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isJointSoftServoEnabled(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua function prototype
     * isJointSoftServoEnabled() -> boolean
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isJointSoftServoEnabled","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endenglish
     */
    bool isJointSoftServoEnabled();

    /**
     * @ingroup MotionControl
     * \chinese
     * 打开振动抑制
     *
     * @param omega 振动抑制频率,长度一般为笛卡尔维度或关节自由度.为0时关闭抑制
     * \n
     * @param zeta 振动抑制阻尼比,长度一般为笛卡尔维度或关节自由度.为0时关闭抑制
     * \n
     * @param level
     * 振动抑制等级(1~3),等级越高抑制效果越明显响应速度相应变慢.等级0关闭振动抑制
     * \n
     * @retval 0 成功
     * @retval AUBO_BAD_STATE(1) 当前安全模式处于非
     * Normal、ReducedMode、Recovery 状态
     * @retval AUBO_QUEUE_FULL(2) 规划队列已满
     * @retval AUBO_BUSY(3) 上一条指令正在执行中
     * @retval -AUBO_BAD_STATE(-1)
     * 可能的原因包括但不限于：线程已分离、线程被终止、task_id
     * 未找到，或者当前机器人模式非 Running
     * @retval -AUBO_TIMEOUT(-4) 调用接口超时
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * enableVibrationSuppress(self: pyaubo_sdk.MotionControl, arg0:
     * list[float], arg1: list[float], arg2: int) -> int
     *
     * @par Lua函数原型
     * enableVibrationSuppress(omega: table, zeta: table, level: number) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.enableVibrationSuppress","params":[[0.5,0.5,0.5,0.5,0.5,0.5],[0.5,0.5,0.5,0.5,0.5,0.5],2],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     */
    int enableVibrationSuppress(const std::vector<double> &omega,
                                const std::vector<double> &zeta, int level);
    /**
     * @ingroup MotionControl
     * \chinese
     * 关闭振动抑制
     *
     * @return 已使能返回true，反之则返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * disbaleVibrationSuppress(self: pyaubo_sdk.MotionControl) -> int
     *
     * @par Lua函数原型
     * disbaleVibrationSuppress() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.disbaleVibrationSuppress","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endchinese
     */
    int disbaleVibrationSuppress();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置时间最优算法 默认关闭
     *
     * @param enable
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * setTimeOptimalEnable() -> bool
     *
     * @par Lua示例
     * setTimeOptimalEnable(true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setTimeOptimalEnable","params":[true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     *
     * @param enable
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * setTimeOptimalEnable() -> number
     *
     * @par Lua example
     * setTimeOptimalEnable(true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setTimeOptimalEnable","params":[true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setTimeOptimalEnable(bool enable);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取时间最优算法状态：
     *   true - 开启
     *   false - 关闭
     *
     * @return 返回时间最优算法状态
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isTimeOptimalEnabled(self: pyaubo_sdk.MotionControl) -> float
     *
     * @par Lua函数原型
     * isTimeOptimalEnabled() -> number
     *
     * @par Lua 示例
     * num = isTimeOptimalEnabled()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isTimeOptimalEnabled","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1.0}
     * \endchinese
     * \english
     * Get the time optimal algorithm state:
     *   true - enable
     *   false - disable
     *
     * @return Returns the time optimal algorithm state
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isTimeOptimalEnabled(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua function prototype
     * isTimeOptimalEnabled() -> boolean
     *
     * @par Lua example
     * flag = isTimeOptimalEnabled()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isTimeOptimalEnabled","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endenglish
     */
    bool isTimeOptimalEnabled();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取是否支持时间最优算法：
     *   true - 支持
     *   false - 不支持
     *
     * @return 返回是否支持时间最优算法
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isTimeOptimalEnabled(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua函数原型
     * isSupportedTimeOptimal() -> boolean
     *
     * @par Lua 示例
     * num = isSupportedTimeOptimal()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isSupportedTimeOptimal","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1.0}
     * \endchinese
     * \english
     * Check whether the time optimal algorithm is supported
     *   true - supported
     *   false - not supported
     *
     * @return Return whether the time-optimal algorithm is supported
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isSupportedTimeOptimal(self: pyaubo_sdk.MotionControl) -> bool
     *
     * @par Lua function prototype
     * isSupportedTimeOptimal() -> boolean
     *
     * @par Lua example
     * flag = isSupportedTimeOptimal()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.isSupportedTimeOptimal","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     * \endenglish
     */
    bool isSupportedTimeOptimal();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置TCP最大线速度
     *
     * @param v TCP最大线速度值，单位为m/s（米/秒）
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * setTcpMaxLinearVelocity(number) -> number
     *
     * @par Lua示例
     * setTcpMaxLinearVelocity(0.5)  -- 设置TCP最大线速度为0.5米/秒
     *
     * @par Python函数原型
     * setTcpMaxLinearVelocity(v: float) -> int
     *
     * @par Python示例
     * setTcpMaxLinearVelocity(0.5) -- 设置TCP最大线速度为0.5米/秒
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setTcpMaxLinearVelocity","params":[0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set TCP maximum linear velocity
     *
     * @param v TCP maximum linear velocity value, unit is m/s
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * setTcpMaxLinearVelocity(number) -> number
     *
     * @par Lua example
     * setTcpMaxLinearVelocity(0.5)  -- Set TCP maximum linear velocity to 0.5
     * meters per second
     *
     * @par Python function prototype
     * setTcpMaxLinearVelocity(v: float) -> int
     *
     * @par Python example
     * setTcpMaxLinearVelocity(0.5)  -- Set TCP maximum linear velocity to 0.5
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setTcpMaxLinearVelocity","params":[0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setTcpMaxLinearVelocity(double v);

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取TCP最大线速度
     *
     * @return 当前TCP最大线速度值，单位为m/s（米/秒）
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * getTcpMaxLinearVelocity() -> number
     *
     * @par Lua示例
     * local v = getTcpMaxLinearVelocity()  -- 获取TCP最大线速度
     *
     * @par Python函数原型
     * getTcpMaxLinearVelocity() -> float
     *
     * @par Python示例
     * v = getTcpMaxLinearVelocity()  # 获取TCP最大线速度
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getTcpMaxLinearVelocity","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.5}
     * \endchinese
     * \english
     * Get TCP maximum linear velocity
     *
     * @return Current TCP maximum linear velocity value, unit is m/s
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * getTcpMaxLinearVelocity() -> number
     *
     * @par Lua example
     * local v = getTcpMaxLinearVelocity()  -- Get TCP maximum linear velocity
     *
     * @par Python function prototype
     * getTcpMaxLinearVelocity() -> float
     *
     * @par Python example
     * v = getTcpMaxLinearVelocity()  # Get TCP maximum linear velocity
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getTcpMaxLinearVelocity","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.5}
     * \endenglish
     */
    double getTcpMaxLinearVelocity();

    /**
     * @ingroup MotionControl
     * \chinese
     * 重置 TCP 最大线速度
     *
     * 清除通过 setTcpMaxLinearVelocity 接口设置的 TCP 最大线速度覆盖值
     *
     * @return 成功返回 0；失败返回错误码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * resetTcpMaxLinearVelocity() -> number
     *
     * @par Lua示例
     * resetTcpMaxLinearVelocity()  -- 重置 TCP 最大线速度为安全配置中的值
     *
     * @par Python函数原型
     * resetTcpMaxLinearVelocity() -> int
     *
     * @par Python示例
     * resetTcpMaxLinearVelocity()  -- 重置 TCP 最大线速度为安全配置中的值
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resetTcpMaxLinearVelocity","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     *
     * \english
     * Reset TCP maximum linear velocity
     *
     * Clear the TCP maximum linear velocity override set by
     * setTcpMaxLinearVelocity
     *
     * @return Returns 0 on success; error code on failure.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * resetTcpMaxLinearVelocity() -> number
     *
     * @par Lua example
     * resetTcpMaxLinearVelocity()  -- Reset TCP maximum linear velocity to
     * the value in the safety configuration
     *
     * @par Python function prototype
     * resetTcpMaxLinearVelocity() -> int
     *
     * @par Python example
     * resetTcpMaxLinearVelocity()  -- Reset TCP maximum linear velocity
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.resetTcpMaxLinearVelocity","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int resetTcpMaxLinearVelocity();

    /**
     * @ingroup MotionControl
     * \chinese
     * 设置轨迹终止点（以当前轨迹段为界）
     *
     * 显式指定以当前正在执行的轨迹段为边界，终止后续轨迹段的交融（blending）。
     * 当前轨迹段将完整执行完毕，但不会与后续轨迹进行速度或位置上的平滑过渡，
     * 后续轨迹段将被视为新的独立轨迹起点。
     *
     * 该接口不会触发急停，也不会中断当前轨迹段的执行，仅影响轨迹段之间的交融行为。
     *
     * @return 成功返回 0；失败返回错误码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * setEndPath() -> number
     *
     * @par Lua示例
     * setEndPath()  -- 以当前轨迹段为界，终止后续轨迹交融
     *
     * @par Python函数原型
     * setEndPath() -> int
     *
     * @par Python示例
     * setEndPath()  # 以当前轨迹段为界，终止后续轨迹交融
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setEndPath","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     *
     * \english
     * Set end path (terminate blending at current trajectory segment)
     *
     * Explicitly specifies the currently executing trajectory segment as the
     * boundary at which trajectory blending is terminated. The current
     * trajectory segment will be executed completely, but no velocity or
     * position blending will be applied with subsequent trajectory segments.
     *
     * This interface does not trigger an emergency stop and does not interrupt
     * the execution of the current trajectory segment. It only affects the
     * blending behavior between trajectory segments.
     *
     * @return Returns 0 on success; error code on failure.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * setEndPath() -> number
     *
     * @par Lua example
     * setEndPath()  -- Terminate trajectory blending at the current segment
     *
     * @par Python function prototype
     * setEndPath() -> int
     *
     * @par Python example
     * setEndPath()  # Terminate trajectory blending at the current segment
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.setEndPath","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setEndPath();

    /**
     * @ingroup MotionControl
     * \chinese
     * 获取当前摆焊轨迹点方向
     *
     * 获取机器人当前执行轨迹点在摆焊（Weave）运动中的方向状态，
     * 用于指示该点位于摆焊坐标系 Y 轴的正半轴或负半轴区域。
     *
     * 当机器人正在执行摆焊轨迹时，该接口返回当前摆焊点所属的摆动方向，
     * 可用于判断摆焊运动处于正向摆动阶段或反向摆动阶段。
     *
     * 当机器人未执行摆焊轨迹时，该接口返回 0。
     *
     * 该接口为状态查询接口，不会影响当前轨迹执行，也不会改变机器人运动状态。
     *
     * @return 返回当前摆焊方向，对应 WeaveDirection 枚举值：
     * - 0 : NONE      当前未执行摆焊轨迹
     * - 1 : POSITIVE  当前位于摆焊坐标系 Y 轴正半轴区域
     * - 2 : NEGATIVE  当前位于摆焊坐标系 Y 轴负半轴区域
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * getWeaveDirection() -> number
     *
     * @par Lua示例
     * local dir = getWeaveDirection()
     * if dir == 1 then
     *     -- 正方向摆动
     * elseif dir == 2 then
     *     -- 负方向摆动
     * end
     *
     * @par Python函数原型
     * getWeaveDirection() -> int
     *
     * @par Python示例
     * dir = getWeaveDirection()
     * if dir == 1:
     *     # positive direction
     *     pass
     * elif dir == 2:
     *     # negative direction
     *     pass
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getWeaveDirection","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endchinese
     *
     * \english
     * Get current weave trajectory direction
     *
     * Retrieves the directional state of the current trajectory point during
     * weave motion, indicating whether the point is located on the positive or
     * negative side of the weave coordinate system Y-axis.
     *
     * When no weave trajectory is active, this interface returns 0.
     *
     * This is a state query interface and does not affect trajectory execution
     * or robot motion.
     *
     * @return Returns current weave direction corresponding to WeaveDirection
     * enum:
     * - 0 : NONE      No active weave trajectory
     * - 1 : POSITIVE  Positive Y-axis side
     * - 2 : NEGATIVE  Negative Y-axis side
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * getWeaveDirection() -> number
     *
     * @par Lua example
     * local dir = getWeaveDirection()
     *
     * @par Python function prototype
     * getWeaveDirection() -> int
     *
     * @par Python example
     * dir = getWeaveDirection()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.MotionControl.getWeaveDirection","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endenglish
     */
    int getWeaveDirection();

protected:
    void *d_;
};
using MotionControlPtr = std::shared_ptr<MotionControl>;
} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_MOTION_CONTROL_INTERFACE_H
