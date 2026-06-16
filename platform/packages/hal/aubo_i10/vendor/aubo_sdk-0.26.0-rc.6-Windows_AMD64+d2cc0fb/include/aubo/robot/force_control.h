/**
 * \chinese
 * @file  force_control.h
 * @brief 力控接口
 *
 * 力控的限制
 * 当机器人处于力控模式时，以下功能不可用：
 *
 * • 碰撞检测（选项 613-1）\n
 * • SoftMove（选项 885-1）\n
 * • 跟踪功能，如输送带跟踪（选项 606-1）、光学跟踪（6601）和焊接引导（815-2）\n
 * • 传感器同步或模拟同步\n
 * • 世界区域（选项 608-1）\n
 * • 独立轴（选项 610-1）\n
 * • 路径偏移（选项 612-1）\n
 * • 弧焊选项\n
 * • PickMaster 选项\n
 * • 关节软伺服（指令 SoftAct）\n
 * • 当机器人以 MultiMove 协调模式（选项 604-1）运行时，不能激活力控。\n
 * • 如果力控与 SafeMove（选项 810-2）或电子位置开关（选项 810-1）一起使用，必须使用操作安全范围功能。请参阅这些选项的相关手册。\n
 * • RAPID 指令如 FCAct、FCDeact、FCConditionWaitWhile 和 FCRefStop 只能从运动任务的普通级别调用。
 *
 * 应用：抛光、打磨、清洁\n
 * FC Pressure\n
 * 设置轨迹坐标系的 z 方向为力控轴，spring 设置为 0\n
 * 在还没接触前设置输出力为 0，spring 设置为固定值（根据 vel 确定）\n
 * 离开接触面：设置输出力为 0，spring 设置为固定值\n
 *
 * 活塞装配\n
 * Forward clutch hub\n
 * 设置力控终止模式
 *
 * 基于末端力传感器的拖动示教\n
 * spring = 0; force_ref = 0; 参考轨迹点任意
 * \endchinese
 * \english
 * @file  force_control.h
 * @brief Force control interface
 *
 * Force control limitations
 * When the robot is force controlled, the following functionality is not accessible:
 *
 * • Collision Detection (option 613-1) \n
 * • SoftMove (option 885-1) \n
 * • Tracking functionality like Conveyor Tracking (option 606-1), Optical Tracking (6601) and Weld Guide (815-2) \n
 * • Sensor Synchronization or Analog Synchronization \n
 * • World Zones (option 608-1) \n
 * • Independent Axes (option 610-1) \n
 * • Path Offset (option 612-1) \n
 * • Arc options \n
 * • PickMaster options \n
 * • Joint soft servo (instruction SoftAct) \n
 * • Force Control cannot be activated when the robot is running in MultiMove Coordinated mode (option 604-1). \n
 * • If Force Control is used together with SafeMove (option 810-2) or Electronic Position Switches (option 810-1), the function Operational Safety Range must be used. See the respective manual for these options. \n
 * • RAPID instructions such as FCAct, FCDeact, FCConditionWaitWhile and FCRefStop can only be called from normal level in a motion task.
 *
 * Applications: polishing, grinding, cleaning \n
 * FC Pressure \n
 * Set the z direction of the trajectory coordinate system as the force control axis, set spring to 0 \n
 * Before contact, set output force to 0, spring to a fixed value (determined by vel) \n
 * Leaving the contact surface: set output force to 0, spring to a fixed value \n
 *
 * Piston assembly \n
 * Forward clutch hub \n
 * Set force control termination mode
 *
 * Drag teaching based on end force sensor \n
 * spring = 0; force_ref = 0; reference trajectory point arbitrary
 * \endenglish
 */
#ifndef AUBO_SDK_FORCE_CONTROL_INTERFACE_H
#define AUBO_SDK_FORCE_CONTROL_INTERFACE_H

#include <vector>
#include <thread>

#include <aubo/global_config.h>
#include <aubo/type_def.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup ForceControl ForceControl(力控模块)
 * @ingroup RobotInterface
 * \chinese

 * 力控接口抽象类
 * \endchinese
 * \english
 * Abstract class for force control interface
 * \endenglish
 */
class ARCS_ABI_EXPORT ForceControl
{
public:
    ForceControl();
    virtual ~ForceControl();

    /**
     * @ingroup ForceControl
     * \chinese
     * 使能力控。
     * fcEnable 被用于使能力控。 在力控被使能的同时，
     * fcEnable 用于定义力控的坐标系，并调整力和力矩的阻尼。
     * 如果在 fcEnable 中未指定坐标系，
     * 则会创建一个默认的力控制坐标系，其方向与工作对象坐标系相同。
     * 所有力控制监管功能都被 fcEnable 激活。
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * fcEnable(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua函数原型
     * fcEnable() -> nil
     *
     * @par Lua示例
     * fcEnable()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.fcEnable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * 
     * \english
     * Start force control
     *
     * fcEnable is used to enable Force Control. At the same time as Force
     * Control is enabled, fcEnable is used to define the coordinate system
     * for Force Control, and tune the force and torque damping. If a coordinate
     * system is not specified in fcEnable a default force control coordinate
     * system is created with the same orientation as the work object coordinate
     * system. All Force Control supervisions are activated by fcEnable.
     *
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * fcEnable(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua Function Prototype
     * fcEnable() -> nil
     *
     * @par Lua example
     * fcEnable()
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.fcEnable","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */

    int fcEnable();

    /**
     * @ingroup ForceControl
     * \chinese
     * 失能力控。
     * fcDisable 被用于失能力控。 在成功失能力控之后，机器人将回到位置控制模式。
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * fcDisable(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua函数原型
     * fcDisable() -> nil
     *
     * @par Lua示例
     * fcDisable()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.fcDisable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     *
     * \english
     * End force control
     *
     * fcDisable is used to disable Force Control. After a successful
     * deactivation the robot is back in position control.
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * fcDisable(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua Function Prototype
     * fcDisable() -> nil
     *
     * @par Lua example
     * fcDisable()
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.fcDisable","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */

    int fcDisable();

    /**
     * @ingroup ForceControl
     * \chinese
     * 判断力控是否被使能
     *
     * @return 使能返回true，失能返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isFcEnabled(self: pyaubo_sdk.ForceControl) -> bool
     *
     * @par Lua函数原型
     * isFcEnabled() -> boolean
     *
     * @par Lua示例
     * Fc_status = isFcEnabled()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.isFcEnabled","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     * 
     * \english
     * Check if force control is enabled
     *
     * @return Returns true if enabled, false if disabled
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * isFcEnabled(self: pyaubo_sdk.ForceControl) -> bool
     *
     * @par Lua Function Prototype
     * isFcEnabled() -> boolean
     *
     * @par Lua example
     * Fc_status = isFcEnabled()
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.isFcEnabled","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool isFcEnabled();

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控参考(目标)值
     *
     * @param feature: 参考几何特征，用于生成力控参考坐标系
     * @param compliance: 柔性轴（方向）选择
     * @param wrench: 目标力/力矩
     * @param limits: 速度限制
     * @param type: 力控参考坐标系类型
     *
     * 使用说明：
     * 1. 基坐标系：
     *    feature = {0,0,0,0,0,0}
     *    type = TaskFrameType::NONE
     *
     * 2. 法兰坐标系：
     *    feature = {0,0,0,0,0,0}
     *    type = TaskFrameType::TOOL_FORCE
     *
     * 3. TCP坐标系：
     *    feature = tcp_offset
     *    type = TaskFrameType::TOOL_FORCE
     *
     * 4. 用户坐标系（FRAME_FORCE）：
     *    type = TaskFrameType::FRAME_FORCE
     *    feature 设为用户定义的参考坐标，例如 getTcpPose() 表示以当前 TCP 坐标作为力控坐标系。
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
     * setTargetForce(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[bool], arg2: List[float], arg3: List[float], arg4:
     * arcs::common_interface::TaskFrameType) -> int
     *
     * @par Lua函数原型
     * setTargetForce(feature: table, compliance: table, wrench: table, limits:
     * table, type: number) -> nil
     *
     * @par Lua示例
     * setTargetForce({0,0,0,0,0,0},{true,false,false,false,false,false},{10,0,0,0,0,0},{0,0,0,0,0,0},4)
     *
     * \endchinese
     * \english
     * Set force control reference (target) value
     *
     * @param feature: Reference geometric feature for generating force control reference frame
     * @param compliance: Compliance axis (direction) selection
     * @param wrench: Target force/torque
     * @param limits: Velocity limits
     * @param type: Force control reference frame type
     *
     * Usage Examples:
     * 1. Base Coordinate Frame:
     *    feature = {0,0,0,0,0,0}
     *    type = TaskFrameType::NONE
     *
     * 2. Flange Coordinate Frame:
     *    feature = {0,0,0,0,0,0}
     *    type = TaskFrameType::TOOL_FORCE
     *
     * 3. TCP Coordinate Frame:
     *    feature = tcp_offset
     *    type = TaskFrameType::TOOL_FORCE
     *
     * 4. User Coordinate Frame (FRAME_FORCE):
     *    type = TaskFrameType::FRAME_FORCE
     *    feature should be the user-defined reference frame,
     *    for example, getTcpPose() means setting the force control frame to current TCP pose.
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setTargetForce(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[bool], arg2: List[float], arg3: List[float], arg4:
     * arcs::common_interface::TaskFrameType) -> int
     *
     * @par Lua Function Prototype
     * setTargetForce(feature: table, compliance: table, wrench: table, limits:
     * table, type: number) -> nil
     *
     * @par Lua example
     * setTargetForce({0,0,0,0,0,0},{true,false,false,false,false,false},{10,0,0,0,0,0},{0,0,0,0,0,0},4)
     *
     * \endenglish
     */
    int setTargetForce(const std::vector<double> &feature,
                       const std::vector<bool> &compliance,
                       const std::vector<double> &wrench,
                       const std::vector<double> &limits,
                       TaskFrameType type = TaskFrameType::FRAME_FORCE);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控动力学模型
     *
     * @param env_stiff: 环境刚度，表示为接触轴方向上的工件刚度，取值范围[0, 1]，默认为0
     * @param damp_scale: 表征阻尼水平的参数，取值范围[0, 1]，默认为0.5
     * @param stiff_scale: 表征软硬程度的参数，取值范围[0, 1]，默认为0.5
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
     * setDynamicModel1(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> int
     *
     * @par Lua函数原型
     * setDynamicModel1(env_stiff: table, damp_scale: table, stiff_scale:
     * table) -> nil
     *
     * @par Lua示例
     * setDynamicModel1({0,0,0,0,0,0},{0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endchinese
     * \english
     * Set force control dynamics model
     *
     * @param env_stiff: Environment stiffness, representing the workpiece stiffness in the contact axis direction, range [0, 1], default 0
     * @param damp_scale: Parameter representing damping level, range [0, 1], default 0.5
     * @param stiff_scale: Parameter representing stiffness level, range [0, 1], default 0.5
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setDynamicModel1(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> int
     *
     * @par Lua Function Prototype
     * setDynamicModel1(env_stiff: table, damp_scale: table, stiff_scale:
     * table) -> nil
     *
     * @par Lua example
     * setDynamicModel1({0,0,0,0,0,0},{0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endenglish
     */
    int setDynamicModel1(const std::vector<double> &env_stiff,
                         const std::vector<double> &damp_scale,
                         const std::vector<double> &stiff_scale);

    /**
     * @ingroup ForceControl
     * \chinese
     * 计算力控动力学模型
     *
     * @param env_stiff: 环境刚度，表示为接触轴方向上的工件刚度，取值范围[0, 1]，默认为0
     * @param damp_scale: 表征阻尼水平的参数，取值范围[0, 1]，默认为0.5
     * @param stiff_scale: 表征软硬程度的参数，取值范围[0, 1]，默认为0.5
     *
     * @return 力控动力学模型MDK
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * fcCalDynamicModel(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> Tuple[List[float], List[float], List[float]]
     *
     * @par Lua函数原型
     * fcCalDynamicModel(env_stiff: table, damp_scale: table, stiff_scale: table) -> table
     *
     * @par Lua示例
     * fc_table = fcCalDynamicModel({0,0,0,0,0,0},{0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endchinese
     * \english
     * Calculate force control dynamics model
     *
     * @param env_stiff: Environment stiffness, representing the workpiece stiffness in the contact axis direction, range [0, 1], default 0
     * @param damp_scale: Parameter representing damping level, range [0, 1], default 0.5
     * @param stiff_scale: Parameter representing stiffness level, range [0, 1], default 0.5
     *
     * @return Force control dynamics model MDK
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * fcCalDynamicModel(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> Tuple[List[float], List[float], List[float]]
     *
     * @par Lua Function Prototype
     * fcCalDynamicModel(env_stiff: table, damp_scale: table, stiff_scale: table) -> table
     *
     * @par Lua example
     * fc_table = fcCalDynamicModel({0,0,0,0,0,0},{0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endenglish
     */
    DynamicsModel fcCalDynamicModel(const std::vector<double> &env_stiff,
                                    const std::vector<double> &damp_scale,
                                    const std::vector<double> &stiff_scale);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控搜孔场景下的动力学模型
     *
     * @param damp_scale: 表征阻尼水平的参数，取值范围[0, 1]，默认为0.5
     * @param stiff_scale: 表征软硬程度的参数，取值范围[0, 1]，默认为0.5
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
     * setDynamicModelSearch(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float]) -> int
     *
     * @par Lua函数原型
     * setDynamicModelSearch(damp_scale: table, stiff_scale: table) -> nil
     *
     * @par Lua示例
     * setDynamicModelSearch({0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endchinese
     * \english
     * Set force control dynamics model for hole searching scenario
     *
     * @param damp_scale: Parameter representing damping level, range [0, 1], default 0.5
     * @param stiff_scale: Parameter representing stiffness level, range [0, 1], default 0.5
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setDynamicModelSearch(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float]) -> int
     *
     * @par Lua Function Prototype
     * setDynamicModelSearch(damp_scale: table, stiff_scale: table) -> nil
     *
     * @par Lua example
     * setDynamicModelSearch({0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endenglish
     */
    int setDynamicModelSearch(const std::vector<double> &damp_scale,
                              const std::vector<double> &stiff_scale);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控插/拔孔场景下的动力学模型
     *
     * @param damp_scale: 表征阻尼水平的参数，取值范围[0, 1]，默认为0.5
     * @param stiff_scale: 表征软硬程度的参数，取值范围[0, 1]，默认为0.5
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
     * setDynamicModelInsert(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float]) -> int
     *
     * @par Lua函数原型
     * setDynamicModelInsert(damp_scale: table, stiff_scale: table) -> nil
     *
     * @par Lua示例
     * setDynamicModelInsert({0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endchinese
     * \english
     * Set force control dynamics model for insertion/extraction scenario
     *
     * @param damp_scale: Parameter representing damping level, range [0, 1], default 0.5
     * @param stiff_scale: Parameter representing stiffness level, range [0, 1], default 0.5
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setDynamicModelInsert(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float]) -> int
     *
     * @par Lua Function Prototype
     * setDynamicModelInsert(damp_scale: table, stiff_scale: table) -> nil
     *
     * @par Lua example
     * setDynamicModelInsert({0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endenglish
     */
    int setDynamicModelInsert(const std::vector<double> &damp_scale,
                              const std::vector<double> &stiff_scale);
    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控接触场景下的动力学模型
     *
     * @param env_stiff: 表征环境刚度的参数，取值范围[0, 1]，默认为0
     * @param damp_scale: 表征阻尼水平的参数，取值范围[0, 1]，默认为0.5
     * @param stiff_scale: 表征软硬程度的参数，取值范围[0, 1]，默认为0.5
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
     * setDynamicModelContact(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> int
     *
     * @par Lua函数原型
     * setDynamicModelContact(env_stiff: table, damp_scale: table, stiff_scale:
     * table) -> nil
     *
     * @par Lua示例
     * setDynamicModelContact({0,0,0,0,0,0},{0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endchinese
     * \english
     * Set force control dynamics model for contact scenario
     *
     * @param env_stiff: Parameter representing environment stiffness, range [0, 1], default 0
     * @param damp_scale: Parameter representing damping level, range [0, 1], default 0.5
     * @param stiff_scale: Parameter representing stiffness level, range [0, 1], default 0.5
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setDynamicModelContact(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> int
     *
     * @par Lua Function Prototype
     * setDynamicModelContact(env_stiff: table, damp_scale: table, stiff_scale:
     * table) -> nil
     *     
     * @par Lua example
     * setDynamicModelContact({0,0,0,0,0,0},{0.5,0.5,0.5,0.5,0.5,0.5},{0.5,0.5,0.5,0.5,0.5,0.5})
     *
     * \endenglish
     */
    int setDynamicModelContact(const std::vector<double> &env_stiff,
                               const std::vector<double> &damp_scale,
                               const std::vector<double> &stiff_scale);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控动力学模型
     *
     * @param m 质量参数
     * @param d 阻尼参数
     * @param k 刚度参数
     *
     * 参数单位说明：
     * - 质量：
     *   - 笛卡尔空间：单位为 kg，长度为工作空间维度（一般为6），顺序为 [x, y, z, Rx, Ry, Rz]
     *   - 关节空间：单位为 kg·m²，长度为机器人自由度（一般为6），顺序为 [J1, J2, J3, J4, J5, J6]
     * - 阻尼：
     *   - 笛卡尔空间：单位为 N·s/m，顺序为 [x, y, z, Rx, Ry, Rz]
     *   - 关节空间：单位为 N·m·s/rad，顺序为 [J1, J2, J3, J4, J5, J6]
     * - 刚度：
     *   - 笛卡尔空间：单位为 N/m，顺序为 [x, y, z, Rx, Ry, Rz]
     *   - 关节空间：单位为 N·m/rad，顺序为 [J1, J2, J3, J4, J5, J6]
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
     * setDynamicModel(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float], arg2: List[float]) -> int
     *
     * @par Lua函数原型
     * setDynamicModel(m: table, d: table, k: table) -> nil
     *
     * @par Lua示例
     * setDynamicModel({20.0, 20.0, 20.0, 10.0, 10.0, 10.0},{2000, 0, 0, 0, 0, 0},{0, 0, 0, 0, 0, 0})
     *
     * \endchinese
     * \english
     * Set force control dynamics model
     *
     * @param m Mass parameters
     * @param d Damping parameters
     * @param k Stiffness parameters
     *
     * Parameter unit description:
     * - Mass:
     *   - Cartesian space: unit is kg, length is 6, order is [x, y, z, Rx, Ry, Rz]
     *   - Joint space: unit is kg·m², length is 6, order is [J1, J2, J3, J4, J5, J6]
     * - Damping:
     *   - Cartesian space: unit is N·s/m, order is [x, y, z, Rx, Ry, Rz]
     *   - Joint space: unit is N·m·s/rad, order is [J1, J2, J3, J4, J5, J6]
     * - Stiffness:
     *   - Cartesian space: unit is N/m, order is [x, y, z, Rx, Ry, Rz]
     *   - Joint space: unit is N·m/rad, order is [J1, J2, J3, J4, J5, J6]
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setDynamicModel(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float], arg2: List[float]) -> int
     *
     * @par Lua Function Prototype
     * setDynamicModel(m: table, d: table, k: table) -> nil
     *
     * @par Lua example
     * setDynamicModel({20.0, 20.0, 20.0, 10.0, 10.0, 10.0},{2000, 0, 0, 0, 0, 0},{0, 0, 0, 0, 0, 0})
     *
     * \endenglish
     */
    int setDynamicModel(const std::vector<double> &m,
                        const std::vector<double> &d,
                        const std::vector<double> &k);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控阈值
     *
     * @param thresholds: 力控阈值
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
     * fcSetSensorThresholds(self: pyaubo_sdk.ForceControl, arg0:
     * List[float]) -> int
     *
     * @par Lua函数原型
     * fcSetSensorThresholds(thresholds: table) -> nil
     *
     * @par Lua示例
     * fcSetSensorThresholds({1.0,1.0,1.0,0.5,0.5,0.5})
     *
     * \endch
     * \endchinese
     * \english
     * Set force control thresholds
     *
     * @param thresholds: Force control thresholds
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * fcSetSensorThresholds(self: pyaubo_sdk.ForceControl, arg0:
     * List[float]) -> int
     *
     * @par Lua Function Prototype
     * fcSetSensorThresholds(thresholds: table) -> nil
     *
     * @par Lua example
     * fcSetSensorThresholds({1.0,1.0,1.0,0.5,0.5,0.5})
     *
     * \endenglish
     */
    int fcSetSensorThresholds(const std::vector<double> &thresholds);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控最大受力限制
     *
     * @param limits: 力限制
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
     * fcSetSensorLimits(self: pyaubo_sdk.ForceControl, arg0:
     * List[float]) -> int
     *
     * @par Lua函数原型
     * fcSetSensorLimits(limits: table) -> nil
     *
     * @par Lua示例
     * fcSetSensorLimits({200.0,200.0,200.0,50.0,50.0,50.0})
     *
     * \endchinese
     * \english
     * Set force control maximum force limits
     *
     * @param limits: Force limits
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * fcSetSensorLimits(self: pyaubo_sdk.ForceControl, arg0:
     * List[float]) -> int
     *
     * @par Lua Function Prototype
     * fcSetSensorLimits(limits: table) -> nil
     *
     * @par Lua example
     * fcSetSensorLimits({200.0,200.0,200.0,50.0,50.0,50.0})
     *
     * \endenglish
     */
    int fcSetSensorLimits(const std::vector<double> &limits);

    /**
     * @ingroup ForceControl
     * \chinese
     * 获取力控阈值
     *
     * @return 力控最小力阈值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getFcSensorThresholds(self: pyaubo_sdk.ForceControl) -> list
     *
     * @par Lua函数原型
     * getFcSensorThresholds() -> table
     *
     * @par Lua函数示例
     * Fc_Thresholds = getFcSensorThresholds()
     *
     * \endchinese
     * \english
     * Get force control thresholds
     *
     * @return Minimum force control thresholds
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * getFcSensorThresholds(self: pyaubo_sdk.ForceControl) -> list
     *
     * @par Lua Function Prototype
     * getFcSensorThresholds() -> table
     *
     * @par Lua example
     * Fc_Thresholds = getFcSensorThresholds()
     *
     * \endenglish
     */
    std::vector<double> getFcSensorThresholds();

    /**
     * @ingroup ForceControl
     * \chinese
     * 获取最大力限制
     *
     * @return 力控最大力限制
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getFcSensorLimits(self: pyaubo_sdk.ForceControl) -> list
     *
     * @par Lua函数原型
     * getFcSensorLimits() -> table
     *
     * @par Lua示例
     * Fc_Limits = getFcSensorLimits()
     *
     * \endchinese
     * \english
     * Get maximum force limits
     *
     * @return Force control maximum force limits
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * getFcSensorLimits(self: pyaubo_sdk.ForceControl) -> list
     *
     * @par Lua Function Prototype
     * getFcSensorLimits() -> table
     *
     * @par Lua example
     * Fc_Limits = getFcSensorLimits()
     *
     * \endenglish
     */
    std::vector<double> getFcSensorLimits();

    /**
     * @ingroup ForceControl
     * \chinese
     * 获取力控动力学模型
     *
     * @return 力控动力学模型
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDynamicModel(self: pyaubo_sdk.ForceControl) -> Tuple[List[float],
     * List[float], List[float]]
     *
     * @par Lua函数原型
     * getDynamicModel() -> table
     *
     * @par Lua示例
     * Fc_Model = getDynamicModel()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.getDynamicModel","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[],[20.0,20.0,20.0,5.0,5.0,5.0],[]]}
     * \endchinese
     * \english
     * Get force control dynamics model
     *
     * @return Force control dynamics model
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * getDynamicModel(self: pyaubo_sdk.ForceControl) -> Tuple[List[float],
     * List[float], List[float]]
     *
     * @par Lua Function Prototype
     * getDynamicModel() -> table
     *
     * @par Lua example
     * Fc_Model = getDynamicModel()
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.getDynamicModel","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":[[],[20.0,20.0,20.0,5.0,5.0,5.0],[]]}
     * \endenglish
     */
    DynamicsModel getDynamicModel();

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控终止条件：力，当测量的力在设置的范围之内，力控算法将保持运行，直到设置的条件不满足，力控将退出
     * 
     * The condition is lateractivated by calling the instruction
     * FCCondWaitWhile, which will wait and hold the program execution while the
     * specified condition is true. This allows the reference force, torque and
     * movement to continue until the force is outside the specified limits.
     *
     * A force condition is set up by defining minimum and maximum limits for
     * the force in the directions of the force control coordinate system. Once
     * activated with FCCondWaitWhile, the program execution will continue to
     * wait while the measured force is within its specified limits.
     *
     * It is possible to specify that the condition is fulfilled when the force
     * is outside the specified limits instead. This is done by using the switch
     * argument Outside. The condition on force is specified in the force
     * control coordinate system. This coordinate system is setup by the user in
     * the instruction FCAct.
     *
     * @param min 各方向最小的力/力矩
     * @param max 各方向最大的力/力矩
     * @param outside false 在设置条件的范围之内有效
     *          true  在设置条件的范围之外有效
     * @param timeout
     * 时间限制，单位s(秒)，从开始力控到达该时间时，不管是否满足力控终止条件，都会终止力控
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
     * setCondForce(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float], arg2: bool, arg3: float) -> int
     *
     * @par Lua函数原型
     * setCondForce(min: table, max: table, outside: boolean, timeout: number)
     * -> nil
     * @par Lua示例
     * setCondForce({0.1,0.1,0.1,0.1,0.1,0.1},{50,50,50,5,5,5},{true,true,true,true,true,true},10)
     *
     * \endchinese
     * \english
     * Set force control termination condition: Force. When the measured force is within
     * the specified range, the force control algorithm will continue to run until the set 
     * condition is not met, at which point force control will exit.
     * 
     * The condition is lateractivated by calling the instruction
     * FCCondWaitWhile, which will wait and hold the program execution while the
     * specified condition is true. This allows the reference force, torque and
     * movement to continue until the force is outside the specified limits.
     *
     * A force condition is set up by defining minimum and maximum limits for
     * the force in the directions of the force control coordinate system. Once
     * activated with FCCondWaitWhile, the program execution will continue to
     * wait while the measured force is within its specified limits.
     *
     * It is possible to specify that the condition is fulfilled when the force
     * is outside the specified limits instead. This is done by using the switch
     * argument Outside. The condition on force is specified in the force
     * control coordinate system. This coordinate system is setup by the user in
     * the instruction FCAct.
     *
     * @param min Minimum force/torque in each direction
     * @param max Maximum force/torque in each direction
     * @param outside false: valid within the specified range
     *                true:  valid outside the specified range
     * @param timeout
     * Time limit in seconds; when this time is reached from the start of force control,
     * force control will terminate regardless of whether the end condition is met
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setCondForce(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float], arg2: bool, arg3: float) -> int
     *
     * @par Lua Function Prototype
     * setCondForce(min: table, max: table, outside: boolean, timeout: number)
     * -> nil
     * @par Lua example
     * setCondForce({0.1,0.1,0.1,0.1,0.1,0.1},{50,50,50,5,5,5},{true,true,true,true,true,true},10)
     *
     * \endenglish
     */
    int setCondForce(const std::vector<double> &min,
                     const std::vector<double> &max, bool outside,
                     double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置力控终止条件：姿态，当测量的姿态在设置的范围之内，力控算法将保持运行，直到设置的条件不满足，力控将退出.
     * 
     * setCondOrient is used to set up an end condition for the tool orientation.
     * The condition is lateractivated by calling the instruction
     * FCCondWaitWhile, which will wait and hold the program execution while the
     * specified condition is true. This allows the reference force, torque and
     * movement to continue until the orientation is outside the specified
     * limits.
     *
     * An orientation condition is set up by defining a maximum angle and a
     * maximum rotation from a reference orientation. The reference orientation
     * is either defined by the current z direction of the tool, or by
     * specifying an orientation in relation to the z direction of the work
     * object.
     *
     * Once activated, the tool orientation must be within the limits (or
     * outside, if the argument Outside is used).
     *
     * @param frame
     * @param max_angle
     * @param max_rot
     * @param outside
     * @param timeout
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
     * setCondOrient(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: bool, arg4: float) -> int
     *
     * @par Lua函数原型
     * setCondOrient(frame: table, max_angle: number, max_rot: number, outside:
     * boolean, timeout: number) -> nil
     *
     * @par Lua示例
     * setCondOrient({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},30.0,20.0,true,10.0)
     *
     * \endchinese
     * 
     * \english
     * setCondOrient is used to set up an end condition for the tool orientation.
     * The condition will wait and hold the program execution while the
     * specified condition is true. This allows the reference force, torque and
     * movement to continue until the orientation is outside the specified
     * limits.
     *
     * An orientation condition is set up by defining a maximum angle and a
     * maximum rotation from a reference orientation. The reference orientation
     * is either defined by the current z direction of the tool, or by
     * specifying an orientation in relation to the z direction of the work
     * object.
     *
     * Once activated, the tool orientation must be within the limits (or
     * outside, if the argument Outside is used).
     *
     * @param frame
     * @param max_angle
     * @param max_rot
     * @param outside
     * @param timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setCondOrient(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: bool, arg4: float) -> int
     *
     * @par Lua Function Prototype
     * setCondOrient(frame: table, max_angle: number, max_rot: number, outside:
     * boolean, timeout: number) -> nil
     *
     * @par Lua example
     * setCondOrient({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},30.0,20.0,true,10.0)
     *
     * \endenglish
     */
    int setCondOrient(const std::vector<double> &frame, double max_angle,
                      double max_rot, bool outside, double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 指定力控有效平面，x-y平面，z方向有效
     *
     * @param plane={A,B,C,D}
     *        平面表示方法 Ax +By +Cz + D = 0
     *        其中,n = (A, B, C)是平面的法向量，
     *        D 是将平面平移到坐标原点所需距离（所以D=0时，平面过原点）
     * @param timeout
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
     * setCondPlane(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float) -> int
     *
     * @par Lua函数原型
     * setCondPlane(plane: table, timeout: number) -> nil
     *
     * @par Lua示例
     * setCondPlane({0.1, 0.3, 0.1, 0.3},10.0)
     *
     * \endchinese
     * \english
     * Specify a valid force control plane, x-y plane, z direction is valid
     *
     * @param plane={A,B,C,D}
     *        Plane equation: Ax + By + Cz + D = 0
     *        where n = (A, B, C) is the normal vector of the plane,
     *        D is the distance required to move the plane to the origin (so D=0 means the plane passes through the origin)
     * @param timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setCondPlane(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float) -> int
     *
     * @par Lua Function Prototype
     * setCondPlane(plane: table, timeout: number) -> nil
     *
     * @par Lua example
     * setCondPlane({0.1, 0.3, 0.1, 0.3},10.0)
     *
     * \endenglish
     */
    int setCondPlane(const std::vector<double> &plane, double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 指定力控有效圆柱体，提供中心轴和圆柱半径，可以指定圆柱内部还是外部
     *
     * @param axis
     * @param radius
     * @param outside
     * @param timeout
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
     * setCondCylinder(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: bool, arg3: float) -> int
     *
     * @par Lua函数原型
     * setCondCylinder(axis: table, radius: number, outside: boolean, timeout:
     * number) -> nil
     *
     * @par Lua示例
     * setCondCylinder({0,1,0},10.0,true,5,0)
     *
     * \endchinese
     * \english
     * Specify a valid force control cylinder by providing the central axis and cylinder radius, and specify whether the inside or outside of the cylinder is valid.
     *
     * @param axis
     * @param radius
     * @param outside
     * @param timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setCondCylinder(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: bool, arg3: float) -> int
     *
     * @par Lua Function Prototype
     * setCondCylinder(axis: table, radius: number, outside: boolean, timeout:
     * number) -> nil
     *
     * @par Lua example
     * setCondCylinder({0,1,0},10.0,true,5,0)
     *
     * \endenglish
     */
    int setCondCylinder(const std::vector<double> &axis, double radius,
                        bool outside, double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 指定力控有效球体，提供球心和半径，可以指定球体内部还是外部
     *
     * @param center
     * @param radius
     * @param outside
     * @param timeout
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
     * setCondSphere(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: bool, arg3: float) -> int
     *
     * @par Lua函数原型
     * setCondSphere(center: table, radius: number, outside: boolean, timeout:
     * number) -> nil
     *
     * @par Lua示例
     * setCondSphere({0.2, 0.5, 0.1, 1.57, 0, 0},10.0,true,5,0)
     *
     * \endchinese
     * \english
     * Specify a valid force control sphere by providing the center and radius, and specify whether the inside or outside of the sphere is valid.
     *
     * @param center
     * @param radius
     * @param outside
     * @param timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setCondSphere(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: bool, arg3: float) -> int
     *
     * @par Lua Function Prototype
     * setCondSphere(center: table, radius: number, outside: boolean, timeout:
     * number) -> nil
     *
     * @par Lua example
     * setCondSphere({0.2, 0.5, 0.1, 1.57, 0, 0},10.0,true,5,0)
     *
     * \endenglish
     */
    int setCondSphere(const std::vector<double> &center, double radius,
                      bool outside, double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置TCP速度的终止条件。该条件可通过调用FCCondWaitWhile指令激活，
     * 在指定条件为真时，程序将等待并保持执行。这样可以使参考力、力矩和运动继续，
     * 直到速度超出指定范围。
     *
     * 通过定义TCP在工作对象所有方向上的最小和最大速度限制来设置TCP速度条件。
     * 一旦通过FCCondWaitWhile激活，程序将在测量速度处于指定范围内时继续等待。
     *
     * 也可以指定当速度超出指定范围时条件成立，通过使用outside参数实现。
     * TCP速度条件在工作对象坐标系中指定。
     *
     * @param min 最小速度
     * @param max 最大速度
     * @param outside 是否在范围外有效
     * @param timeout 超时时间
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
     * setCondTcpSpeed(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float], arg2: bool, arg3: float) -> int
     *
     * @par Lua函数原型
     * setCondTcpSpeed(min: table, max: table, outside: boolean, timeout:
     * number) -> nil
     *
     * @par Lua示例
     * setCondTcpSpeed({0.2, 0.2, 0.2, 0.2, 0.2, 0.2},{1.2, 1.2, 1.2, 1.2, 1.2, 1.2},true,5,0)
     *
     * \endchinese
     * \english
     * setCondTcpSpeed is used to setup an end condition for the TCP speed. The
     * condition is later activated by calling the instruction FCCondWaitWhile,
     * which will wait and hold the program execution while the specified
     * condition is true. This allows the reference force, torque and movement
     * to continue until the speed is outside the specified limits.
     *
     * A TCP speed condition is set up by defining minimum and maximum limits
     * for the TCP speed in all directions of the work object. Once activated
     * with FCCondWaitWhile, the program execution will continue to wait while
     * the measured speed is within its specified limits.
     *
     * It is possible to specify that the condition is fulfilled when the speed
     * is outside the specified limits instead. This is done by using the
     * switch argument Outside. The condition on TCP speed is specified in the
     * work object coordinate system.
     *
     * @param min
     * @param max
     * @param outside
     * @param timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setCondTcpSpeed(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float], arg2: bool, arg3: float) -> int
     *
     * @par Lua Function Prototype
     * setCondTcpSpeed(min: table, max: table, outside: boolean, timeout:
     * number) -> nil
     *
     * @par Lua example
     * setCondTcpSpeed({0.2, 0.2, 0.2, 0.2, 0.2, 0.2},{1.2, 1.2, 1.2, 1.2, 1.2, 1.2},true,5,0)
     *
     * \endenglish
     */
    int setCondTcpSpeed(const std::vector<double> &min,
                        const std::vector<double> &max, bool outside,
                        double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 力控终止条件-距离
     *
     * @param distance 距离
     * @param timeout 超时时间
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * setCondDistance(distance: number, timeout: number)
     *
     * @par Lua示例
     * setCondDistance(0.2, 10.0)
     *
     * \endchinese
     * \english
     * Force control termination condition - distance
     *
     * @param distance Distance
     * @param timeout Timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua Function Prototype
     * setCondDistance(distance: number, timeout: number)
     *
     * @par Lua example
     * setCondDistance(0.2, 10.0)
     *
     * \endenglish
     */
    int setCondDistance(double distance, double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 高级力控终止条件
     *
     * @param type 类型
     * @param args 参数
     * @param timeout 超时时间
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * setCondAdvanced(type: number, args: table, timeout: number)
     *
     * @par Lua示例
     * setCondAdvanced(1, {0,1,0,0,0,0},10)
     *
     * \endchinese
     * \english
     * Advanced force control termination condition
     *
     * @param type Type
     * @param args Arguments
     * @param timeout Timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua Function Prototype
     * setCondAdvanced(type: number, args: table, timeout: number)
     *
     * @par Lua example
     * setCondAdvanced(1, {0,1,0,0,0,0},10)
     *
     * \endenglish
     */
    int setCondAdvanced(const std::string &type,
                        const std::vector<double> &args, double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * 激活力控终止条件
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setCondActive(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua函数原型
     * setCondActive() -> nil
     *
     * @par Lua示例
     * setCondActive()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.setCondActive","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Activate force control termination condition
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setCondActive(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua Function Prototype
     * setCondActive() -> nil
     *
     * @par Lua example
     * setCondActive()
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.setCondActive","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int setCondActive();

    /**
     * @ingroup ForceControl
     * \chinese
     * 力控终止条件是否已经满足
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isCondFullfiled(self: pyaubo_sdk.ForceControl) -> bool
     *
     * @par Lua函数原型
     * isCondFullfiled() -> boolean
     *
     * @par Lua示例
     * status = isCondFullfiled()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.isCondFullfiled","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     * \english
     * Check if the force control termination condition has been fulfilled
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * isCondFullfiled(self: pyaubo_sdk.ForceControl) -> bool
     *
     * @par Lua Function Prototype
     * isCondFullfiled() -> boolean
     *
     * @par Lua example
     * status = isCondFullfiled()
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.isCondFullfiled","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool isCondFullfiled();

    /**
     * @ingroup ForceControl
     * \chinese
     * setSupvForce 用于在力控中设置力监督。监督在通过 FCAct 指令激活力控时被激活。
     *
     * 力监督通过在力控坐标系的各个方向上定义最小和最大力限制来设置。
     * 一旦激活，如果力超出允许的范围，监督将停止执行。力监督在力控坐标系中指定。
     * 该坐标系由用户通过 FCAct 指令设置。
     *
     * @param min 最小力限制
     * @param max 最大力限制
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
     * setSupvForce(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float]) -> int
     *
     * @par Lua函数原型
     * setSupvForce(min: table, max: table) -> nil
     *
     * @par Lua示例
     * setSupvForce({0.1 ,0.1 ,0.1 ,0.1 ,0.1 ,0.1}, {10.0 ,10.0 ,10.0 ,10.0 ,10.0 ,10.0})
     *
     * \endchinese
     * \english
     * setSupvForce is used to set up force supervision in Force Control. The
     * supervision is activated when Force Control is activated with the
     * instruction FCAct.
     *
     * The force supervision is set up by defining minimum and maximum limits
     * for the force in the directions of the force control coordinate system.
     * Once activated, the supervision will stop the execution if the force is
     * outside the allowed values. The force supervision is specified in the
     * force control coordinate system. This coordinate system is setup by the
     * user with the instruction FCAct.
     *
     * @param min
     * @param max
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setSupvForce(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float]) -> int
     *
     * @par Lua Function Prototype
     * setSupvForce(min: table, max: table) -> nil
     *
     * @par Lua example
     * setSupvForce({0.1 ,0.1 ,0.1 ,0.1 ,0.1 ,0.1}, {10.0 ,10.0 ,10.0 ,10.0 ,10.0 ,10.0})
     *
     * \endenglish
     */
    int setSupvForce(const std::vector<double> &min,
                     const std::vector<double> &max);

    /**
     * @ingroup ForceControl
     * \chinese
     * setSupvOrient 用于设置工具姿态的监督条件。
     * 当通过 FCAct 指令激活力控时，监督条件被激活。
     *
     * 姿态监督通过定义相对于参考姿态的最大角度和最大旋转来设置。
     * 参考姿态可以由工具当前的z方向定义，也可以通过指定相对于工作对象z方向的姿态来定义。
     *
     * 一旦激活，工具姿态必须在限制范围内，否则监督将停止执行。
     *
     * @param frame
     * @param max_angle
     * @param max_rot
     * @param outside
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
     * setSupvOrient(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: bool) -> int
     *
     * @par Lua函数原型
     * setSupvOrient(frame: table, max_angle: number, max_rot: number,
     * outside: boolean) -> nil
     * \endchinese
     * \english
     * setSupvOrient is used to set up an supervision for the tool orientation.
     * The supervision is activated when Force Control is activated with the
     * instruction FCAct.
     *
     * An orientation supervision is set up by defining a maximum angle and a
     * maximum rotation from a reference orientation. The reference orientation
     * is either defined by the current z direction of the tool, or by
     * specifying an orientation in relation to the z direction of the work
     * object.
     *
     * Once activated, the tool orientation must be within the limits otherwise
     * the supervision will stop the execution.
     *
     * @param frame
     * @param max_angle
     * @param max_rot
     * @param outside
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setSupvOrient(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * float, arg2: float, arg3: bool) -> int
     *
     * @par Lua Function Prototype
     * setSupvOrient(frame: table, max_angle: number, max_rot: number,
     * outside: boolean) -> nil
     * \endenglish
     */
    int setSupvOrient(const std::vector<double> &frame, double max_angle,
                      double max_rot, bool outside);

    /**
     * @ingroup ForceControl
     * \chinese
     * setSupvPosBox 用于在力控中设置位置监督。监督在通过 FCAct 指令激活力控时被激活。
     * 位置监督通过为TCP定义空间体积来设置。一旦激活，如果TCP超出该体积，监督将停止执行。
     *
     * @param frame
     * @param box
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
     * setSupvPosBox(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float[6]]) -> int
     *
     * @par Lua函数原型
     * setSupvPosBox(frame: table, box: table) -> nil
     * \endchinese
     * \english
     * setSupvPosBox is used to set up position supervision in Force Control.
     * Supervision is activated when Force Control is activated with the
     * instruction FCAct. Position supervision is set up by defining a volume in
     * space for the TCP. Once activated, the supervision will stop the
     * execution if the TCP is outside this volume.
     *
     * @param frame
     * @param box
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setSupvPosBox(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float[6]]) -> int
     *
     * @par Lua Function Prototype
     * setSupvPosBox(frame: table, box: table) -> nil
     * \endenglish
     */
    int setSupvPosBox(const std::vector<double> &frame, const Box &box);

    /**
     * @ingroup ForceControl
     * \chinese
     *
     * @param frame
     * @param cylinder
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
     * setSupvPosCylinder(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float[5]]) -> int
     *
     * @par Lua函数原型
     * setSupvPosCylinder(frame: table, cylinder: table) -> nil
     *
     * \endchinese
     * \english
     *
     * @param frame
     * @param cylinder
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setSupvPosCylinder(self: pyaubo_sdk.ForceControl, arg0: List[float],
     * arg1: List[float[5]]) -> int
     *
     * @par Lua Function Prototype
     * setSupvPosCylinder(frame: table, cylinder: table) -> nil
     *
     * \endenglish
     */
    int setSupvPosCylinder(const std::vector<double> &frame,
                           const Cylinder &cylinder);

    /**
     * @ingroup ForceControl
     * \chinese
     *
     * @param frame
     * @param sphere
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
     * setSupvPosSphere(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float[3]]) -> int
     *
     * @par Lua函数原型
     * setSupvPosSphere(frame: table, sphere: table) -> nil
     *
     * \endchinese
     * \english
     *
     * @param frame
     * @param sphere
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setSupvPosSphere(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1:
     * List[float[3]]) -> int
     *
     * @par Lua Function Prototype
     * setSupvPosSphere(frame: table, sphere: table) -> nil
     *
     * \endenglish
     */
    int setSupvPosSphere(const std::vector<double> &frame,
                         const Sphere &sphere);

    /**
     * @ingroup ForceControl
     * \chinese
     * setSupvReoriSpeed 用于在力控中设置重新定向速度监督。监督在通过 FCAct 指令激活力控时被激活。
     *
     * 重新定向速度监督通过定义工作对象坐标系轴周围重新定向速度的最小和最大限制来设置。
     * 一旦激活，如果重新定向速度的值过高，监督将停止执行。
     *
     * 有两种速度监督：FCSupvReoriSpeed 和 FCSupvTCPSpeed，后者在第199页的 FCSupvTCPSpeed 部分有描述。
     * 可能需要两种监督，因为：
     * - 机器人轴可以在 TCP 静止时高速旋转。
     * - 当 TCP 距离旋转轴较远时，轴的微小旋转可能导致 TCP 的高速运动。
     *
     * @param speed_limit 速度限制
     * @param outside 是否在范围外有效
     * @param timeout 超时时间
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
     * setSupvReoriSpeed(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1: bool, arg2: float) -> int
     *
     * @par Lua函数原型
     * setSupvReoriSpeed(speed_limit: table, outside: boolean, timeout: number) -> nil
     * \endchinese
     * \english
     * setSupvReoriSpeed is used to set up reorientation speed supervision in Force Control. The supervision is activated when Force Control is activated with the instruction FCAct.
     *
     * The reorientation speed supervision is set up by defining minimum and maximum limits for the reorientation speed around the axis of the work object coordinate system. Once activated, the supervision will stop the execution if the values of the reorientation speed are too high.
     *
     * There are two speed supervisions: FCSupvReoriSpeed and FCSupvTCPSpeed, which is described in section FCSupvTCPSpeed on page 199.
     * Both supervisions may be required because:
     * - A robot axis can rotate with high speed while the TCP is stationary.
     * - The TCP can be far from the rotating axis and a small axis rotation may result in a high speed movement of the TCP.
     *
     * @param speed_limit
     * @param outside
     * @param timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setSupvReoriSpeed(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1: bool, arg2: float) -> int
     *
     * @par Lua Function Prototype
     * setSupvReoriSpeed(speed_limit: table, outside: boolean, timeout: number) -> nil
     * \endenglish
     */
    int setSupvReoriSpeed(const std::vector<double> &speed_limit, bool outside,
                          double timeout);

    /**
     * @ingroup ForceControl
     * \chinese
     * setSupvTcpSpeed 用于在力控中设置TCP速度监督。监督在通过 FCAct 指令激活力控时被激活。
     * TCP速度监督通过定义工作对象坐标系各方向上的最小和最大速度限制来设置。
     * 一旦激活，如果检测到过高的TCP速度值，监督将停止执行。
     *
     * 有两种速度监督：FCSupvTCPSpeed 和 FCSupvReoriSpeed，后者在第197页的 FCSupvReoriSpeed 部分有描述。
     *
     * 可能需要两种监督，因为：
     * - 机器人轴可以在TCP静止时高速旋转。
     * - 当TCP距离旋转轴较远时，轴的微小旋转可能导致TCP的高速运动。
     *
     * @param speed_limit 速度限制
     * @param outside 是否在范围外有效
     * @param timeout 超时时间
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
     * setSupvTcpSpeed(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1: bool, arg2: float) -> int
     *
     * @par Lua函数原型
     * setSupvTcpSpeed(speed_limit: table, outside: boolean, timeout: number) -> nil
     * \endchinese
     * \english
     * setSupvTcpSpeed is used to set up TCP speed supervision in Force Control.
     * The supervision is activated when Force Control is activated with the
     * instruction FCAct. The TCP speed supervision is set up by defining
     * minimum and maximum limits for the TCP speed in the directions of the
     * work object coordinate system. Once activated, the supervision will stop
     * the execution if too high TCP speed values are detected.
     *
     * There are two speed supervisions: FCSupvTCPSpeed and FCSupvReoriSpeed,
     * which is described in section FCSupvReoriSpeed on page 197.
     *
     * Both supervisions may be required because:
     * - A robot axis can rotate with high speed while the TCP is stationary.
     * - The TCP can be far from the rotating axis and a small axis rotation may
     *   result in a high speed movement of the TCP.
     *
     * @param speed_limit
     * @param outside
     * @param timeout
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setSupvTcpSpeed(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1: bool, arg2: float) -> int
     *
     * @par Lua Function Prototype
     * setSupvTcpSpeed(speed_limit: table, outside: boolean, timeout: number) -> nil
     * \endenglish
     */
    int setSupvTcpSpeed(const std::vector<double> &speed_limit, bool outside,
                        double timeout);

    // 设置低通滤波器
    // --- force frame filter: 过滤测量到的力/力矩
    // +++ force loop filter: 力控输出参考速度的滤波器

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置低通滤波器
     *
     * --- force frame filter: 过滤测量到的力/力矩
     * +++ force loop filter: 力控输出参考速度的滤波器
     *
     * @param cutoff_freq 截止频率
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
     * setLpFilter(self: pyaubo_sdk.ForceControl, arg0: List[float]) -> int
     *
     * @par Lua函数原型
     * setLpFilter(cutoff_freq: table) -> nil
     * \endchinese
     * \english
     * Set low-pass filter
     *
     * --- force frame filter: filter measured force/torque
     * +++ force loop filter: filter for force control output reference speed
     *
     * FCSetLPFilterTune is used to change the response of force loop according to
     * the description in Damping and LP-filter on page 103.
     *
     * @param cutoff_freq Cutoff frequency
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setLpFilter(self: pyaubo_sdk.ForceControl, arg0: List[float]) -> int
     *
     * @par Lua Function Prototype
     * setLpFilter(cutoff_freq: table) -> nil
     * \endenglish
     */
    int setLpFilter(const std::vector<double> &cutoff_freq);

    /**
     * @ingroup ForceControl
     * \chinese
     * 重置低通滤波器
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resetLpFilter(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua函数原型
     * resetLpFilter() -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.resetLpFilter","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Reset low-pass filter
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * resetLpFilter(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua Function Prototype
     * resetLpFilter() -> nil
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.resetLpFilter","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int resetLpFilter();

    /**
     * @ingroup ForceControl
     * \chinese
     * speedChangeEnable 用于激活 FC SpeedChange 功能，并设置期望的参考力和恢复行为。
     * 当 FC SpeedChange 功能被激活时，机器人速度会根据测量信号与参考值的接近程度自动降低或提高。
     *
     * @param ref_force 参考力
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
     * speedChangeEnable(self: pyaubo_sdk.ForceControl, arg0: float) -> int
     *
     * @par Lua函数原型
     * speedChangeEnable(ref_force: number) -> nil
     * \endchinese
     * \english
     * The speedChangeEnable is used to activate FC SpeedChange function with desired
     * reference and recover behavior. When FC SpeedChange function is active,
     * the robot speed will be reduced/increased in order to keep the measured
     * signal close to the reference.
     *
     * @param ref_force
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * speedChangeEnable(self: pyaubo_sdk.ForceControl, arg0: float) -> int
     *
     * @par Lua Function Prototype
     * speedChangeEnable(ref_force: number) -> nil
     * \endenglish
     */
    int speedChangeEnable(double ref_force);

    /**
     * @ingroup ForceControl
     * \chinese
     * 停用 FC SpeedChange 功能。
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * speedChangeDisable(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua函数原型
     * speedChangeDisable() -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.speedChangeDisable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Deactivate FC SpeedChange function.
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * speedChangeDisable(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua Function Prototype
     * speedChangeDisable() -> nil
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.speedChangeDisable","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int speedChangeDisable();

    /**
     * @ingroup ForceControl
     * \chinese
     * speedChangeTune 用于将 FC SpeedChange 系统参数设置为新值。
     *
     * @param speed_levels 速度级别
     * @param speed_ratio_min 最小速度比例
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
     * speedChangeTune(self: pyaubo_sdk.ForceControl, arg0: int, arg1: float) -> int
     *
     * @par Lua函数原型
     * speedChangeTune(speed_levels: number, speed_ratio_min: number) -> nil
     * \endchinese
     * \english
     * speedChangeTune is used to set FC SpeedChange system parameters to a new value.
     *
     * @param speed_levels
     * @param speed_ratio_min
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * speedChangeTune(self: pyaubo_sdk.ForceControl, arg0: int, arg1: float) -> int
     *
     * @par Lua Function Prototype
     * speedChangeTune(speed_levels: number, speed_ratio_min: number) -> nil
     * \endenglish
     */
    int speedChangeTune(int speed_levels, double speed_ratio_min);

    /* Defines how many Newtons are required to make the robot move 1 m/s. The
       higher the value, the less responsive the robot gets.
       The damping can be tuned (as a percentage of the system parameter values)
       by the RAPID instruction FCAct. */
    // 设置阻尼系数，阻尼的系统参数需要通过配置文件设置
    // [damping_fx, damping_fy, damping_fz, damping_tx, damping_ty, damping_tz]
    // A value between min and 10,000,000 Ns/m.
    // A value between minimum and 10,000,000 Nms/rad.

    /**
     * @ingroup ForceControl
     * \chinese
     * setDamping 用于在力控坐标系中调整阻尼。可调参数包括扭矩x方向到扭矩z方向的阻尼（见第255页）以及力x方向到力z方向的阻尼（见第254页）。
     *
     * 阻尼可以通过配置文件或FCAct指令设置。不同之处在于本指令可在力控激活时使用。FCSetDampingTune调整的是FCAct指令设置的实际值，而不是配置文件中的值。
     *
     * @param damping 阻尼参数
     * @param ramp_time 斜坡时间
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
     * setDamping(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1: float) -> int
     *
     * @par Lua函数原型
     * setDamping(damping: table, ramp_time: number) -> nil
     * \endchinese
     * \english
     * setDamping is used to tune the damping in the force control coordinate systems. The parameters tuned are those described in Damping in Torque x Direction - Damping in Torque z Direction on page 255 and Damping in Force x Direction - Damping in Force z Direction on page 254.
     *
     * Damping can be set in the configuration file or by the instruction FCAct. The difference is that this instruction can be used when force control is active. FCSetDampingTune tunes the actual values set by the instruction FCAct, not the value in the configuration file.
     *
     * @param damping
     * @param ramp_time
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * setDamping(self: pyaubo_sdk.ForceControl, arg0: List[float], arg1: float) -> int
     *
     * @par Lua Function Prototype
     * setDamping(damping: table, ramp_time: number) -> nil
     * \endenglish
     */
    int setDamping(const std::vector<double> &damping, double ramp_time);

    /**
     * @ingroup ForceControl
     * \chinese
     * 重置阻尼参数
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * resetDamping(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua函数原型
     * resetDamping() -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.resetDamping","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Reset damping parameters
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python Function Prototype
     * resetDamping(self: pyaubo_sdk.ForceControl) -> int
     *
     * @par Lua Function Prototype
     * resetDamping() -> nil
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.resetDamping","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int resetDamping();

    /**
     * @ingroup ForceControl
     * \chinese
     * 启用软浮动功能。
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.softFloatEnable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Enable soft float function.
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.softFloatEnable","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int softFloatEnable();

    /**
     * @ingroup ForceControl
     * \chinese
     * 停用软浮动功能。
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.softFloatDisable","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endchinese
     * \english
     * Disable soft float function.
     *
     * @return Return 0 if succeeded; return error code if failed
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.softFloatDisable","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     * \endenglish
     */
    int softFloatDisable();

    /**
     * @ingroup ForceControl
     * \chinese
     * 返回是否开启了软浮动
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.isSoftFloatEnabled","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     * \english
     * Returns whether soft float is enabled
     *
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC Request example
     * {"jsonrpc":"2.0","method":"rob1.ForceControl.isSoftFloatEnabled","params":[],"id":1}
     *
     * @par JSON-RPC Response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool isSoftFloatEnabled();

    /**
     * @ingroup ForceControl
     * \chinese
     * 设置软浮动参数
     *
     * @param joint_softfloat 是否在关节空间启用软浮动
     * @param select 选择哪些自由度启用软浮动
     * @param stiff_percent 刚度百分比
     * @param stiff_damp_ratio 刚度阻尼比
     * @param force_threshold 力阈值
     * @param force_limit 力限制
     * @return 返回0表示成功，其他为错误码
     * \endchinese
     * \english
     * Set soft float parameters
     *
     * @param joint_softfloat Whether to enable soft float in joint space
     * @param select Select which degrees of freedom to enable soft float
     * @param stiff_percent Stiffness percentage
     * @param stiff_damp_ratio Stiffness damping ratio
     * @param force_threshold Force threshold
     * @param force_limit Force limit
     * @return Return 0 if succeeded, otherwise error code
     * \endenglish
     */
    int setSoftFloatParams(bool joint_space, const std::vector<bool> &select,
                           const std::vector<double> &stiff_percent,
                           const std::vector<double> &stiff_damp_ratio,
                           const std::vector<double> &force_threshold,
                           const std::vector<double> &force_limit);

    /**
     * @ingroup ForceControl
     * \chinese
     * 检测工具和外部物体的接触
     *
     * @param direction
     * 预期的接触方向，如果所有的元素为0，表示检测所有方向的接触
     * @return
     * 返回从当前点回退到碰撞开始点的周期步数，如果返回值为0，表示没有接触
     * \endchinese
     * \english
     * Detect contact between the tool and external objects
     *
     * @param direction
     * Expected contact direction. If all elements are 0, detect contact in all directions.
     * @return
     * Returns the number of cycle steps back from the current point to the collision start point. If the return value is 0, no contact is detected.
     * \endenglish
     */
    int toolContact(const std::vector<bool> &direction);

    /**
     * @ingroup ForceControl
     * \chinese
     * @brief 获取历史关节角度
     *
     * 根据给定的周期步数，从关节状态历史中回退指定数量的周期，获取当时的关节角度数据。
     *
     * @param steps
     * 需要回退的周期数（单位：控制周期数），值越大表示获取越早的历史数据
     * @return std::vector<double>
     * 对应时间点的各关节角度（单位：弧度）
     * \endchinese
     * \english
     * @brief Get historical joint positions
     *
     * According to the given number of cycle steps, go back the specified number of cycles from the joint state history to obtain the joint position data at that time.
     *
     * @param steps
     * Number of cycles to go back (unit: control cycles), the larger the value, the earlier the historical data is obtained
     * @return std::vector<double>
     * Joint positions (unit: radians) at the corresponding time point
     * \endenglish
     */
    std::vector<double> getActualJointPositionsHistory(int steps);

protected:
    void *d_{ nullptr };
};
using ForceControlPtr = std::shared_ptr<ForceControl>;
} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_FORCE_CONTROL_INTERFACE_H
