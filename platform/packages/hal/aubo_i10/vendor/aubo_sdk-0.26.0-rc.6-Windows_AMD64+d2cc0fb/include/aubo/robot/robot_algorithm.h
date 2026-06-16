/** @file  robot_algorithm.h
 *  @brief 机器人算法相关的对外接口
 */
#ifndef AUBO_SDK_ROBOT_ALGORITHM_INTERFACE_H
#define AUBO_SDK_ROBOT_ALGORITHM_INTERFACE_H

#include <string>
#include <vector>
#include <memory>
#include <functional>

#include <aubo/global_config.h>
#include <aubo/type_def.h>

namespace arcs {
namespace common_interface {

// clang-format off

/**
 * @defgroup RobotAlgorithm RobotAlgorithm (机器人算法工具)
 * @ingroup RobotInterface
 * \chinese
 * 机器人算法相关的对外接口
 * \endchinese
 * \english
 * Interfaces related to robot algorithms
 * \endenglish
 */
class ARCS_ABI_EXPORT RobotAlgorithm
{
public:
    RobotAlgorithm();
    virtual ~RobotAlgorithm();

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 力传感器标定算法(三点标定法)
     *
     * @param force 力数据
     * @param q 关节角度
     * @return 标定结果
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * calibrateTcpForceSensor(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * List[List[float]], arg1: List[List[float]]) -> Tuple[List[float],
     * List[float], float, List[float]]
     *
     * @par Lua函数原型
     * calibrateTcpForceSensor(force: table, q: table) -> table
     *
     * @par Lua示例
     * cal_table = calibrateTcpForceSensor({10.0,10.0,10.0,-1.2,-1.2,-1.2}, {3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * \endchinese
     * \english
     * Force sensor calibration algorithm (three-point calibration method)
     *
     * @param force Force data
     * @param q Joint angles
     * @return Calibration result
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * calibrateTcpForceSensor(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * List[List[float]], arg1: List[List[float]]) -> Tuple[List[float],
     * List[float], float, List[float]]
     *
     * @par Lua function prototype
     * calibrateTcpForceSensor(force: table, q: table) -> table
     *
     * @par Lua example
     * cal_table = calibrateTcpForceSensor({10.0,10.0,10.0,-1.2,-1.2,-1.2}, {3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * \endenglish
      */
    ForceSensorCalibResult calibrateTcpForceSensor(
        const std::vector<std::vector<double>> &forces,
        const std::vector<std::vector<double>> &poses);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 力传感器标定算法(三点标定法)
     * @param forces
     * @param poses
     * @return force_offset, com, mass, angle error
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Force sensor calibration algorithm (three-point calibration method)
     * @param forces
     * @param poses
     * @return force_offset, com, mass, angle error
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    ForceSensorCalibResultWithError calibrateTcpForceSensor2(
        const std::vector<std::vector<double>> &forces,
        const std::vector<std::vector<double>> &poses);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 力传感器偏置标定算法
     *
     * @param force 力数据
     * @param poses 位姿
     * @param mass 质量, 单位: kg
     * @param cog 重心, 单位: m, 形式为(CoGx, CoGy, CoGz)
     * @return 标定结果
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Force sensor offset calibration algorithm
     *
     * @param forces Force data
     * @param poses
     * @param m Mass, unit: kg
     * @param cog Center of gravity, unit: m, format (CoGx, CoGy, CoGz)
     * @return Calibration result
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
      */
    ResultWithErrno calibrateTcpForceSensor3(
        const std::vector<std::vector<double>> &forces,
        const std::vector<std::vector<double>> &poses, const double &mass,
        const std::vector<double>&cog);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 基于电流的负载辨识算法接口
     *
     * 需要采集空载时运行激励轨迹的位置、速度、电流以及带负载时运行激励轨迹的位置、速度、电流
     *
     * @param data_file_no_payload
     * 空载时运行激励轨迹各关节数据的文件路径（.csv格式），共18列，依次为6个关节位置、6个关节速度、6个关节电流
     * @param data_file_with_payload
     * 带负载运行激励轨迹各关节数据的文件路径（.csv格式），共18列，依次为6个关节位置、6个关节速度、6个关节电流
     * @return 辨识的结果
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * payloadIdentify(self: pyaubo_sdk.RobotAlgorithm, arg0: List[List[float]],
     * arg1: List[List[float]]) -> Tuple[List[float], List[float], float,
     * List[float]]
     *
     * @par Lua函数原型
     * payloadIdentify(data_with_payload: table, data_with_payload: table) ->
     * table
     * \endchinese
     * \english
     * Payload identification algorithm interface based on current
     *
     * Requires collecting position, velocity, and current data when running the excitation trajectory without load, as well as with load.
     *
     * @param data_file_no_payload
     * File path of joint data when running the excitation trajectory without load (.csv format), 18 columns in total: 6 joint positions, 6 joint velocities, 6 joint currents
     * @param data_file_with_payload
     * File path of joint data when running the excitation trajectory with load (.csv format), 18 columns in total: 6 joint positions, 6 joint velocities, 6 joint currents
     * @return Identification result
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * payloadIdentify(self: pyaubo_sdk.RobotAlgorithm, arg0: List[List[float]],
     * arg1: List[List[float]]) -> Tuple[List[float], List[float], float,
     * List[float]]
     *
     * @par Lua function prototype
     * payloadIdentify(data_with_payload: table, data_with_payload: table) ->
     * table
     * \endenglish
     */
    int payloadIdentify(const std::string &data_file_no_payload,
                        const std::string &data_file_with_payload);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 新版基于电流的负载辨识算法接口
     *
     * 需要采集带载时运行最少三个点的位置、速度、加速度、电流、温度、末端传感器数据、底座数据
     *
     * @param data
     * 带负载的各关节数据的文件路径（.csv格式），共42列，末端传感器数据、底座数据默认为0
     * @return 辨识的结果
     * \endchinese
     * \english
     * New version of payload identification algorithm interface based on current
     *
     * Requires collecting at least three points of position, velocity, acceleration, current, temperature, end sensor data, and base data when running with load
     *
     * @param data
     * File path of joint data with load (.csv format), 42 columns in total, end sensor data and base data default to 0
     * @return Identification result
     * \endenglish
     */
    int payloadIdentify1(const std::string &file_name);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 负载辨识是否计算完成
     * @return 完成返回0; 正在进行中返回1; 计算失败返回<0;
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.payloadCalculateFinished","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Whether payload identification calculation is finished
     * @return 0 if finished; 1 if in progress; <0 if failed;
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.payloadCalculateFinished","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int payloadCalculateFinished();

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 获取负载辨识结果
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.getPayloadIdentifyResult","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,[],[],[]]}
     *
     * \endchinese
     * \english
     * Get the result of payload identification
     * @return
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.getPayloadIdentifyResult","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,[],[],[]]}
     *
     * \endenglish
     */
    Payload getPayloadIdentifyResult();

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 关节摩擦力模型辨识算法接口
     *
     * @param q 关节角度
     * @param qd 关节速度
     * @param qdd 关节加速度
     * @param temp 关节温度
     * @return 是否辨识成功
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * frictionModelIdentify(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * List[List[float]], arg1: List[List[float]], arg2: List[List[float]],
     * arg3: List[List[float]]) -> bool
     *
     * @par Lua函数原型
     * frictionModelIdentify(q: table, qd: table, qdd: table, temp: table) ->
     * boolean
     * 
     * @par Lua示例
     * Identify_result = frictionModelIdentify({3.083,1.227,1.098,0.670,-1.870,-0.397},
     * {10.0,10.0,10.0,10.0,10.0,10.0},{20.0,20.0,20.0,20.0,20.0,20.0},{30.0,30.0,30.0,30.0,30.0,30.0})
     *
     * \endchinese
     * \english
     * Joint friction model identification algorithm interface
     *
     * @param q Joint positions
     * @param qd Joint velocities
     * @param qdd Joint accelerations
     * @param temp Joint temperatures
     * @return Whether identification succeeded
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * frictionModelIdentify(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * List[List[float]], arg1: List[List[float]], arg2: List[List[float]],
     * arg3: List[List[float]]) -> bool
     *
     * @par Lua function prototype
     * frictionModelIdentify(q: table, qd: table, qdd: table, temp: table) ->
     * boolean
     *
     * @par Lua example
     * Identify_result = frictionModelIdentify({3.083,1.227,1.098,0.670,-1.870,-0.397},
     * {10.0,10.0,10.0,10.0,10.0,10.0},{20.0,20.0,20.0,20.0,20.0,20.0},{30.0,30.0,30.0,30.0,30.0,30.0})
     *
     * \endenglish
     */
    bool frictionModelIdentify(const std::vector<std::vector<double>> &q,
                               const std::vector<std::vector<double>> &qd,
                               const std::vector<std::vector<double>> &qdd,
                               const std::vector<std::vector<double>> &temp);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 工件坐标系标定算法接口(需要在调用之前正确的设置机器人的TCP偏移)
     * 输入多组关节角度和标定类型，输出工件坐标系位姿(相对于机器人基坐标系)
     *
     * @param q 关节角度
     * @param type 标定类型
     * @return 计算结果(工件坐标系位姿)以及错误代码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * calibWorkpieceCoordinatePara(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * List[List[float]], arg1: int) -> Tuple[List[float], int]
     *
     * @par Lua函数原型
     * calibWorkpieceCoordinatePara(q: table, type: number) -> table, number
     *
     * @par Lua示例
     * coord_pose,coord_num = calibWorkpieceCoordinatePara({3.083,1.227,1.098,0.670,-1.870,-0.397},1)
     *
     * \endchinese
     * \english
     * Workpiece coordinate calibration algorithm interface (requires correct TCP offset set before calling)
     * Input multiple sets of joint angles and calibration type, output workpiece coordinate pose (relative to robot base)
     *
     * @param q Joint angles
     * @param type Calibration type
     * @return Calculation result (workpiece coordinate pose) and error code
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * calibWorkpieceCoordinatePara(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * List[List[float]], arg1: int) -> Tuple[List[float], int]
     *
     * @par Lua function prototype
     * calibWorkpieceCoordinatePara(q: table, type: number) -> table, number
     *
     * @par Lua example 
     * coord_pose,coord_num = calibWorkpieceCoordinatePara({3.083,1.227,1.098,0.670,-1.870,-0.397},1)
     *
     * \endenglish
     */
    ResultWithErrno calibWorkpieceCoordinatePara(
        const std::vector<std::vector<double>> &q, int type);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 动力学正解
     *
     * @param q 关节角
     * @param torqs
     * @return 计算结果以及错误代码
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * forwardDynamics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float], arg1:
     * List[float]) -> Tuple[List[float], int]
     *
     * @par Lua函数原型
     * forwardDynamics(q: table, torqs: table) -> table, number
     *
     * @par Lua示例
     * Dynamics, fk_result = forwardDynamics({3.083,1.227,1.098,0.670,-1.870,-0.397},{0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * \endchinese
     * \english
     * Forward dynamics
     *
     * @param q Joint angles
     * @param torqs
     * @return Calculation result and error code
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * forwardDynamics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float], arg1:
     * List[float]) -> Tuple[List[float], int]
     *
     * @par Lua function prototype
     * forwardDynamics(q: table, torqs: table) -> table, number
     *
     * @par Lua example
     * Dynamics, fk_result = forwardDynamics({3.083,1.227,1.098,0.670,-1.870,-0.397},{0.0,0.0,0.0,0.0,0.0,0.0})
     *
     * \endenglish
     */
    ResultWithErrno forwardDynamics(const std::vector<double> &q,
                                    const std::vector<double> &torqs);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 动力学正解，基于给定的TCP偏移
     *
     * @param q 关节角
     * @param torqs
     * @param tcp_offset TCP偏移
     * @return 计算结果以及错误代码，同forwardDynamics
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * forwardDynamics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float], arg1:
     * List[float], arg2: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua函数原型
     * forwardDynamics1(q: table, torqs: table, tcp_offset: table) -> table, number
     *
     * @par Lua示例
     * Dynamics, fk_result = forwardDynamics1({3.083,1.227,1.098,0.670,-1.870,-0.397},{0.0,0.0,0.0,0.0,0.0,0.0},{0.0,0.13201,0.03879,0,0,0})
     *
     * \endchinese
     * \english
     * Forward dynamics based on the given TCP offset
     *
     * @param q Joint angles
     * @param torqs
     * @param tcp_offset TCP offset
     * @return Calculation result and error code, same as forwardDynamics
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * forwardDynamics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float], arg1:
     * List[float], arg2: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua function prototype
     * forwardDynamics1(q: table, torqs: table, tcp_offset: table) -> table, number
     *
     * @par Lua example
     * Dynamics, fk_result = forwardDynamics1({3.083,1.227,1.098,0.670,-1.870,-0.397},{0.0,0.0,0.0,0.0,0.0,0.0},{0.0,0.13201,0.03879,0,0,0})
     *
     * \endenglish
     */
    ResultWithErrno forwardDynamics1(const std::vector<double> &q,
                                     const std::vector<double> &torqs,
                                     const std::vector<double> &tcp_offset);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学正解, 基于激活的TCP偏移(最近的通过 setTcpOffset 设置的参数)
     * 输入关节角度，输出TCP位姿
     *
     * @param q 关节角
     * @return TCP位姿和正解结果是否有效
     * 返回值的第一个参数为正解结果，第二个为正解错误码，错误码返回值列表如下
     * 0 - 成功
     * -1 - 机械臂状态不对(未初始化完成，可尝试再次调用)
     * -5 - 输入的关节角无效(维度错误)
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * forwardKinematics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float]) ->
     * Tuple[List[float], int]
     *
     * @par Lua函数原型
     * forwardKinematics(q: table) -> table, number
     *
     * @par Lua示例
     * pose, fk_result = forwardKinematics({3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardKinematics","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[0.7137448715395925,0.08416057568819092,0.6707994191515292,2.4599818776908724,0.4789772388601265,1.6189630435878408],0]}
     * \endchinese
     * \english
     * Forward kinematics, based on the activated TCP offset (the most recently set via setTcpOffset)
     * Input joint angles, output TCP pose
     *
     * @param q Joint angles
     * @return TCP pose and whether the result is valid
     * The first parameter of the return value is the forward kinematics result, the second is the error code. Error codes are as follows:
     * 0 - Success
     * -1 - The status of the robot is incorrect (not initialized yet, you can try calling it again)
     * -5 - The input joint angles is invalid (dimension error)
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * forwardKinematics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float]) ->
     * Tuple[List[float], int]
     *
     * @par Lua function prototype
     * forwardKinematics(q: table) -> table, number
     *
     * @par Lua example
     * pose, fk_result = forwardKinematics({3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardKinematics","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[0.7137448715395925,0.08416057568819092,0.6707994191515292,2.4599818776908724,0.4789772388601265,1.6189630435878408],0]}
     * \endenglish
     */
    ResultWithErrno forwardKinematics(const std::vector<double> &q);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学正解
     * 输入关节角度，输出TCP位姿
     * @param q 关节角
     * @param tcp_offset tcp偏移
     * @return TCP位姿和正解结果是否有效
     * 返回值的第一个参数为正解结果，第二个为正解错误码，错误码返回值列表如下
     * 0 - 成功
     * -1 - 机械臂状态不对(未初始化完成，可尝试再次调用)
     * -5 - 输入的关节角或tcp偏移无效(维度错误)
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * forwardKinematics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua函数原型
     * forwardKinematics1(q: table, tcp_offset: table) -> table, number
     *     
     * @par Lua示例
     * pose, fk_result = forwardKinematics1({3.083,1.227,1.098,0.670,-1.870,-0.397},{0.0,0.13201,0.03879,0,0,0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardKinematics1","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627],[0.0,
     * 0.13201,0.03879,0,0,0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[0.7137636726659518,0.0837705432006433,0.6710022027216355,2.459981877690872,0.4789772388601267,1.6189630435878408],0]}
     *
     * @since 0.24.1
     * \endchinese
     * \english
     * Forward kinematics
     * Input joint angles, output TCP pose
     *
     * @param q Joint angles
     * @param tcp_offset TCP offset
     * @return TCP pose and whether the result is valid
     * The first parameter of the return value is the forward kinematics result, the second is the error code. Error codes are as follows:
     * 0 - Success
     * -1 - The status of the robot is incorrect (not initialized yet, you can try calling it again)
     * -5 - The input joint angles or tcp offset is invalid (dimension error)
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * forwardKinematics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua function prototype
     * forwardKinematics1(q: table, tcp_offset: table) -> table, number
     *     
     * @par Lua example
     * pose, fk_result = forwardKinematics1({3.083,1.227,1.098,0.670,-1.870,-0.397},{0.0,0.13201,0.03879,0,0,0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardKinematics1","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627],[0.0,
     * 0.13201,0.03879,0,0,0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[0.7137636726659518,0.0837705432006433,0.6710022027216355,2.459981877690872,0.4789772388601267,1.6189630435878408],0]}
     *
     * @since 0.24.1
     * \endenglish
     */
    ResultWithErrno forwardKinematics1(const std::vector<double> &q,
                                       const std::vector<double> &tcp_offset);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学正解(忽略 TCP 偏移值)
     *
     * @param q 关节角
     * @return 法兰盘中心位姿和正解结果是否有效
     * 返回值的第一个参数为正解结果，第二个为正解错误码，错误码返回值列表如下
     * 0 - 成功
     * -1 - 机械臂状态不对(未初始化完成，可尝试再次调用)
     * -5 - 输入的关节角无效(维度错误)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * forwardToolKinematics(q: table) -> table, number
     *     
     * @par Lua示例
     * pose, fk_result = forwardToolKinematics({3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardToolKinematics","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[0.5881351149440136,0.05323734739426938,0.623922550656701,2.4599818776908724,0.4789772388601265,1.6189630435878408],0]}
     * \endchinese
     * \english
     * Forward kinematics (ignoring TCP offset)
     *
     * @param q Joint angles
     * @return Flange center pose and whether the result is valid
     * The first parameter of the return value is the forward kinematics result, the second is the error code. Error codes are as follows:
     * 0 - Success
     * -1 - The status of the robot is incorrect (not initialized yet, you can try calling it again)
     * -5 - The input joint angles is invalid (dimension error)
     *
     * @par Lua function prototype
     * forwardToolKinematics(q: table) -> table, number
     *     
     * @par Lua example
     * pose, fk_result = forwardToolKinematics({3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardToolKinematics","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[0.5881351149440136,0.05323734739426938,0.623922550656701,2.4599818776908724,0.4789772388601265,1.6189630435878408],0]}
     * \endenglish
     */
    ResultWithErrno forwardToolKinematics(const std::vector<double> &q);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学正解, 基于激活的TCP偏移(最近的通过 setTcpOffset 设置的参数)
     * 输入关节角度，输出各连杆位姿
     *
     * @param q 关节角
     * @return 各个连杆位姿和正解结果是否有效
     * 返回值的第一个参数为正解结果，第二个为正解错误码，错误码返回值列表如下
     * 0 - 成功
     * -1 - 机械臂状态不对(未初始化完成，可尝试再次调用)
     * -5 - 输入的关节角无效(维度错误)
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * forwardKinematicsAll(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float]) ->
     * Tuple[List[List[float]], int]
     *
     * @par Lua函数原型
     * forwardKinematicsAll(q: table) -> table, number
     *
     * @par Lua示例
     * poses, fk_result = forwardKinematicsAll({3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardKinematicsAll","params":{"q":[-7.32945e-11,-0.261799,1.74533,0.436332,1.5708,-2.14136e-10]},"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[[0.0010004,0.0,0.122,0.0,0.0,3.141592653589793],
     * [0.0010003999910823934,-0.12166795404953117,0.12205392567412496,1.5690838552993878,-1.3089969602251492,0.0016541204887245322],
     * [0.10659809449330016,-0.12166124765791932,0.5161518260534821,-1.5718540206872664,0.43633111081725523,-0.002370419930605744],
     * [0.4482255342315581,-0.1226390142692,0.3568490758201224,-0.000788980482890453,1.5665204619271216,-1.5719618592940798],
     * [0.5519603828181741,-0.12282266347465487,0.35639753697117343,1.5707938201843654,0.0042721909279596635,1.569044569428874],
     * [0.5513243939877184,-0.12401224959696328,0.2615193425222568,-3.1349118101994096,0.004272190926529066,1.569044569643007],
     * [0.7494883076798231,-0.025647479212994567,-0.04023458911333461,-3.1349118101994096,0.004272190926529066,1.569044569643007]],0]}
     * \endchinese
     * \english
     * Forward kinematics, based on the activated TCP offset (the most recently set via setTcpOffset)
     * Input joint angles, output links poses
     *
     * @param q Joint angles
     * @return links poses and whether the result is valid
     * The first parameter of the return value is the forward kinematics result, the second is the error code. Error codes are as follows:
     * 0 - Success
     * -1 - The status of the robot is incorrect (not initialized yet, you can try calling it again)
     * -5 - The input joint angles is invalid (dimension error)
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * forwardKinematicsAll(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float]) ->
     * Tuple[List[List[float]], int]
     *
     * @par Lua function prototype
     * forwardKinematicsAll(q: table) -> table, number
     *
     * @par Lua example
     * pose, fk_result = forwardKinematicsAll({3.083,1.227,1.098,0.670,-1.870,-0.397})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.forwardKinematicsAll","params":{"q":[-7.32945e-11,-0.261799,1.74533,0.436332,1.5708,-2.14136e-10]},"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[[0.0010004,0.0,0.122,0.0,0.0,3.141592653589793],
     * [0.0010003999910823934,-0.12166795404953117,0.12205392567412496,1.5690838552993878,-1.3089969602251492,0.0016541204887245322],
     * [0.10659809449330016,-0.12166124765791932,0.5161518260534821,-1.5718540206872664,0.43633111081725523,-0.002370419930605744],
     * [0.4482255342315581,-0.1226390142692,0.3568490758201224,-0.000788980482890453,1.5665204619271216,-1.5719618592940798],
     * [0.5519603828181741,-0.12282266347465487,0.35639753697117343,1.5707938201843654,0.0042721909279596635,1.569044569428874],
     * [0.5513243939877184,-0.12401224959696328,0.2615193425222568,-3.1349118101994096,0.004272190926529066,1.569044569643007],
     * [0.7494883076798231,-0.025647479212994567,-0.04023458911333461,-3.1349118101994096,0.004272190926529066,1.569044569643007]],0]}
     * \endenglish
     */
    ResultWithErrno1 forwardKinematicsAll(const std::vector<double> &q);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学逆解
     * 输入TCP位姿和参考关节角度，输出关节角度
     *
     * @param qnear 参考关节角
     * @param pose TCP位姿
     * @return 关节角和逆解结果是否有效
     * 返回值的第一个参数为逆解结果，第二个为逆解错误码，错误码返回列表如下
     * 0 - 成功
     * -1 - 机械臂状态不对(未初始化完成，可尝试再次调用)
     * -5 - 输入的参考关节角或TCP位姿无效(维度错误)
     * -23 - 逆解计算不收敛，计算出错
     * -24 - 逆解计算超出机器人最大限制
     * -25 - 逆解输入配置存在错误
     * -26 - 逆解雅可比矩阵计算失败
     * -27 - 目标点存在解析解，但均不满足选解条件
     * -28 - 逆解返回未知类型错误
     * 若错误码非0,则返回值的第一个参数为输入参考关节角qnear
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * inverseKinematics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua函数原型
     * inverseKinematics(qnear: table, pose: table) -> table, int
     *
     * @par Lua示例
     * joint,ik_result = inverseKinematics({0,0,0,0,0,0},{0.81665,-0.20419,0.43873,-3.135,0.004,1.569})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematics","params":[[0,0,0,0,0,0],[0.71374,0.08417,0.6708,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627],0]}
     * \endchinese
     * \english
     * Inverse kinematics
     * Input TCP pose and reference joint angles, output joint angles
     *
     * @param qnear Reference joint angles
     * @param pose TCP pose
     * @return Joint angles and whether the inverse kinematics result is valid
     * The first parameter of the return value is the inverse kinematics result, the second is the error code. Error codes are as follows:
     * 0 - Success
     * -1 - The status of the robot is incorrect (not initialized yet, you can try calling it again)
     * -5 - The input reference joint angles or tcp pose is invalid (dimension error)
     * -23 - Inverse kinematics calculation does not converge, calculation error
     * -24 - Inverse kinematics calculation exceeds robot limits
     * -25 - Inverse kinematics input configuration error
     * -26 - Inverse kinematics Jacobian calculation failed
     * -27 - Analytical solution exists but none satisfy the selection criteria
     * -28 - Unknown error in inverse kinematics
     * If the error code is not 0, the first parameter of the return value is the input reference joint angles qnear
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * inverseKinematics(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua function prototype
     * inverseKinematics(qnear: table, pose: table) -> table, int
     *
     * @par Lua example
     * joint,ik_result = inverseKinematics({0,0,0,0,0,0},{0.81665,-0.20419,0.43873,-3.135,0.004,1.569})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematics","params":[[0,0,0,0,0,0],[0.71374,0.08417,0.6708,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627],0]}
     * \endenglish
     */
    ResultWithErrno inverseKinematics(const std::vector<double> &qnear,
                                      const std::vector<double> &pose);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学逆解
     * 输入TCP位姿和参考关节角度，输出关节角度
     *
     * @param qnear 参考关节角
     * @param pose TCP位姿
     * @param tcp_offset TCP偏移
     * @return 关节角和逆解结果是否有效，同 inverseKinematics
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * inverseKinematics1(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua函数原型
     * inverseKinematics1(qnear: table, pose: table, tcp_offset: table) -> table, int
     *
     * @par Lua示例
     * joint,ik_result = inverseKinematics1({0,0,0,0,0,0},{0.81665,-0.20419,0.43873,-3.135,0.004,1.569},{0.04,-0.035,0.1,0,0,0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematics1","params":[[0,0,0,0,0,0],[0.71374,0.08417,0.6708,2.46,0.479,1.619],[0.0,
     * 0.13201,0.03879,0,0,0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[3.084454549595208,1.2278265883747776,1.0986586440159576,0.6708221281915528,-1.8712459848518375,-0.3965111476861782],0]}
     * \endchinese
     * \english
     * Inverse kinematics
     * Input TCP pose and reference joint angles, output joint angles
     *
     * @param qnear Reference joint angles
     * @param pose TCP pose
     * @param tcp_offset TCP offset
     * @return Joint angles and whether the result is valid, same as inverseKinematics
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * inverseKinematics1(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: List[float], arg2: List[float]) -> Tuple[List[float], int]
     *
     * @par Lua function prototype
     * inverseKinematics1(qnear: table, pose: table, tcp_offset: table) -> table, int
     *
     * @par Lua example
     * joint,ik_result = inverseKinematics1({0,0,0,0,0,0},{0.81665,-0.20419,0.43873,-3.135,0.004,1.569},{0.04,-0.035,0.1,0,0,0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematics1","params":[[0,0,0,0,0,0],[0.71374,0.08417,0.6708,2.46,0.479,1.619],[0.0,
     * 0.13201,0.03879,0,0,0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[3.084454549595208,1.2278265883747776,1.0986586440159576,0.6708221281915528,-1.8712459848518375,-0.3965111476861782],0]}
     * \endenglish
     */
    ResultWithErrno inverseKinematics1(const std::vector<double> &qnear,
                                       const std::vector<double> &pose,
                                       const std::vector<double> &tcp_offset);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 求出所有的逆解, 基于激活的 TCP 偏移
     *
     * @param pose TCP位姿
     * @return 关节角和逆解结果是否有效
     * 返回的错误码同inverseKinematics
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematicsAll","params":[[0.71374,0.08417,0.6708,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627],
     * [3.081056801097411,0.17985038037652645,-1.0991717292664145,-0.4806460200109001,-1.869182975312333,-0.402066016835411],
     * [0.4090095277807992,-0.1623365054641728,1.081775890307679,0.26993250263224805,0.9738255833642309,0.000572556627720845],
     * [0.4116449425067969,-1.1931664523907126,-1.0822709833775688,-0.8665964106161371,0.9732141569888207,0.006484919654891586]],0]}
     * \endchinese
     * \english
     * Solve all inverse kinematics solutions based on the activated TCP offset
     *
     * @param pose TCP pose
     * @return Joint angles and whether the result is valid
     * The returned error code is the same as inverseKinematics
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematicsAll","params":[[0.71374,0.08417,0.6708,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627],
     * [3.081056801097411,0.17985038037652645,-1.0991717292664145,-0.4806460200109001,-1.869182975312333,-0.402066016835411],
     * [0.4090095277807992,-0.1623365054641728,1.081775890307679,0.26993250263224805,0.9738255833642309,0.000572556627720845],
     * [0.4116449425067969,-1.1931664523907126,-1.0822709833775688,-0.8665964106161371,0.9732141569888207,0.006484919654891586]],0]}
     * \endenglish
     */
    ResultWithErrno1 inverseKinematicsAll(const std::vector<double> &pose);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 求出所有的逆解, 基于提供的 TCP 偏移
     *
     * @param pose TCP位姿
     * @param tcp_offset TCP偏移
     * @return 关节角和逆解结果是否有效，同 inverseKinematicsAll
     * 返回的错误码同inverseKinematics
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematicsAll1","params":[[0.71374,0.08417,0.6708,2.46,0.479,1.619],[0.0,
     * 0.13201,0.03879,0,0,0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[[3.084454549595208,1.2278265883747776,1.0986586440159576,0.6708221281915528,-1.8712459848518375,-0.3965111476861782],
     * [3.0818224058231602,0.17980369843203092,-1.0997576631122077,-0.48102131527371267,-1.8697135490338517,-0.40149459722060593],
     * [0.40972960018231047,-0.16226026285489026,1.0823403816496,0.2700204411869427,0.9734251963887868,0.0012903686498106507],
     * [0.41236549588802296,-1.193621392918341,-1.0828346680836718,-0.8671097369314354,0.972815367289568,0.007206851371073478]],0]}
     * \endchinese
     * \english
     * Solve all inverse kinematics solutions based on the provided TCP offset
     *
     * @param pose TCP pose
     * @param tcp_offset TCP offset
     * @return Joint angles and whether the result is valid, same as inverseKinematicsAll
     * The returned error code is the same as inverseKinematics
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseKinematicsAll1","params":[[0.71374,0.08417,0.6708,2.46,0.479,1.619],[0.0,
     * 0.13201,0.03879,0,0,0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[[3.084454549595208,1.2278265883747776,1.0986586440159576,0.6708221281915528,-1.8712459848518375,-0.3965111476861782],
     * [3.0818224058231602,0.17980369843203092,-1.0997576631122077,-0.48102131527371267,-1.8697135490338517,-0.40149459722060593],
     * [0.40972960018231047,-0.16226026285489026,1.0823403816496,0.2700204411869427,0.9734251963887868,0.0012903686498106507],
     * [0.41236549588802296,-1.193621392918341,-1.0828346680836718,-0.8671097369314354,0.972815367289568,0.007206851371073478]],0]}
     * \endenglish
     */
    ResultWithErrno1 inverseKinematicsAll1(
        const std::vector<double> &pose, const std::vector<double> &tcp_offset);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学逆解(忽略 TCP 偏移值)
     *
     * @param qnear 参考关节角
     * @param pose 法兰盘中心的位姿
     * @return 关节角和逆解结果是否有效
     * 返回值的第一个参数为逆解结果，第二个为逆解错误码，错误码返回列表如下
     * 0 - 成功
     * -1 - 机械臂状态不对(未初始化完成，可尝试再次调用)
     * -5 - 输入的参考关节角或位姿无效(维度错误)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * inverseToolKinematics(qnear: table, pose: table) -> table, int
     *
     * @par Lua示例
     * joint, ik_result = inverseToolKinematics({0,0,0,0,0,0},{0.58815,0.0532,0.62391,2.46,0.479,1.619})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseToolKinematics","params":[[0,0,0,0,0,0],[0.58815,0.0532,0.62391,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[3.083609363838651,1.22736129158332,1.098095443698268,0.6705395395487186,-1.8706605026855632,-0.39714507002376465],0]}
     * \endchinese
     * \english
     * Inverse kinematics (ignoring TCP offset)
     *
     * @param qnear Reference joint angles
     * @param pose Flange center pose
     * @return Joint angles and whether the result is valid
     * The first parameter of the return value is the inverse kinematics result, the second is the error code. Error codes are as follows:
     * 0 - Success
     * -1 - The status of the robot is incorrect (not initialized yet, you can try calling it again)
     * -5 - The input reference joint angles or pose is invalid (dimension error)
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua function prototype
     * inverseToolKinematics(qnear: table, pose: table) -> table, int
     *
     * @par Lua example
     * joint, ik_result = inverseToolKinematics({0,0,0,0,0,0},{0.58815,0.0532,0.62391,2.46,0.479,1.619})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseToolKinematics","params":[[0,0,0,0,0,0],[0.58815,0.0532,0.62391,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[3.083609363838651,1.22736129158332,1.098095443698268,0.6705395395487186,-1.8706605026855632,-0.39714507002376465],0]}
     * \endenglish
     */
    ResultWithErrno inverseToolKinematics(const std::vector<double> &qnear,
                                          const std::vector<double> &pose);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 运动学逆解(忽略 TCP 偏移值)
     *
     * @param qnear 参考关节角
     * @param pose 法兰盘中心的位姿
     * @return 关节角和逆解结果是否有效
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseToolKinematicsAll","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[[3.083609363838651,1.22736129158332,1.098095443698268,0.6705395395487186,-1.8706605026855632,-0.39714507002376465],
     * [3.0809781797426523,0.17987122696706134,-1.0991932793263717,-0.4807053707530958,-1.8691282890274434,-0.40212516672751814],
     * [0.40892195618737215,-0.16235398607358653,1.081812753177426,0.27003586475871766,0.9738744130114284,0.00048462518316674287],
     * [0.41155633414333076,-1.1932173012004512,-1.082306542045813,-0.8665312056504818,0.9732632365861417,0.0063958311601771175]],0]}
     * \endchinese
     * \english
     * Inverse kinematics (ignoring TCP offset)
     *
     * @param qnear Reference joint angles
     * @param pose Flange center pose
     * @return Joint angles and whether the result is valid
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.inverseToolKinematicsAll","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[[3.083609363838651,1.22736129158332,1.098095443698268,0.6705395395487186,-1.8706605026855632,-0.39714507002376465],
     * [3.0809781797426523,0.17987122696706134,-1.0991932793263717,-0.4807053707530958,-1.8691282890274434,-0.40212516672751814],
     * [0.40892195618737215,-0.16235398607358653,1.081812753177426,0.27003586475871766,0.9738744130114284,0.00048462518316674287],
     * [0.41155633414333076,-1.1932173012004512,-1.082306542045813,-0.8665312056504818,0.9732632365861417,0.0063958311601771175]],0]}
     * \endenglish
     */
    ResultWithErrno1 inverseToolKinematicsAll(const std::vector<double> &pose);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 根据输入的关节角计算并返回对应的机械臂构型
     *
     * 机械臂构型由三个维度的状态组合而成，各维度定义如下：
     * - 肩部方向：LEFT(肩部朝左) / RIGHT(肩部朝右)
     * - 肘部方向：UP(肘部朝上) / DOWN(肘部朝下)
     * - 腕部状态：FLIP(腕部翻转) / NOFLIP(腕部不翻转)
     *
     * 三个维度两两组合共形成8种基础构型（L/R + U/D + F/N），该接口会根据输入的关节角解析出当前对应的构型类型，
     * 并返回其枚举值对应的整数形式及错误码（注：接口返回的是组合构型值，如LUF对应0，而非单独的LEFT/UP/FLIP枚举值）。
     *
     * @param q 输入的关节角数组，6轴机械臂为6个元素，单位：弧度(rad)
     * @return 机械臂构型结果及错误码（类型为ResultWithErrno3，即std::tuple<int, int>）：
     *         - 第一个int：机械臂构型枚举(RobotConfiguration)对应的整数值，取值范围及含义：
     *           -1 (NONE)   - 无效构型
     *            0 (LUF)    - LEFT+UP+FLIP（左肩、肘上、腕翻转）
     *            1 (LUN)    - LEFT+UP+NOFLIP（左肩、肘上、腕不翻转）
     *            2 (LDF)    - LEFT+DOWN+FLIP（左肩、肘下、腕翻转）
     *            3 (LDN)    - LEFT+DOWN+NOFLIP（左肩、肘下、腕不翻转）
     *            4 (RUF)    - RIGHT+UP+FLIP（右肩、肘上、腕翻转）
     *            5 (RUN)    - RIGHT+UP+NOFLIP（右肩、肘上、腕不翻转）
     *            6 (RDF)    - RIGHT+DOWN+FLIP（右肩、肘下、腕翻转）
     *            7 (RDN)    - RIGHT+DOWN+NOFLIP（右肩、肘下、腕不翻转）
     *         - 第二个int：错误码，错误码含义如下：
     *           0  - 成功：构型计算完成，返回有效构型值
     *          -1  - 机械臂状态异常：未初始化完成，可尝试重新初始化后调用
     *          -5  - 输入参数无效：关节角数组维度错误（非6个元素）或数值超出合理范围
     *
     * @throws arcs::common_interface::AuboException 输入参数非法（如空数组、元素数量错误）时抛出
     *
     * @par Python函数原型
     * getRobotConfiguration(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float]) -> Tuple[int, int]
     *
     * @par Lua函数原型
     * getRobotConfiguration(q: table) -> number, number
     *
     * @par Lua示例
     * -- 输入6轴关节角（单位：rad），获取构型及错误码
     * local joint_angles = {3.083,1.227,1.098,0.670,-1.870,-0.397}
     * local config_val, err_code = getRobotConfiguration(joint_angles)
     * if err_code == 0 then
     *     print("机械臂构型值：", config_val)  -- 示例输出：4（对应RUF，右肩、肘上、腕翻转）
     * else
     *     print("获取构型失败，错误码：", err_code)
     * end
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.getRobotConfiguration","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[4,0]}
     * \endchinese
     * \english
     * Calculate and return the corresponding robot configuration based on input joint angles
     *
     * The robot configuration consists of three dimensions of states, with the following definitions for each dimension:
     * - Shoulder direction: LEFT (Shoulder to the left) / RIGHT (Shoulder to the right)
     * - Elbow direction: UP (Elbow up) / DOWN (Elbow down)
     * - Wrist state: FLIP (Wrist flipped) / NOFLIP (Wrist not flipped)
     *
     * The combination of the three dimensions forms 8 basic configurations (L/R + U/D + F/N). This interface parses the current
     * configuration type from the input joint angles and returns its integer value corresponding to the RobotConfiguration enumeration
     * and an error code (Note: The interface returns combined configuration values, e.g., LUF corresponds to 0, not the individual
     * enumeration values of LEFT/UP/FLIP).
     *
     * @param q Input joint angle array, 6 elements for 6-axis robot, unit: radians (rad)
     * @return Robot configuration result and error code (type: ResultWithErrno3, i.e., std::tuple<int, int>):
     *         - First int: Integer value corresponding to the RobotConfiguration enumeration, value range and meanings:
     *           -1 (NONE)   - Invalid configuration
     *            0 (LUF)    - LEFT+UP+FLIP (Left shoulder, elbow up, wrist flipped)
     *            1 (LUN)    - LEFT+UP+NOFLIP (Left shoulder, elbow up, wrist not flipped)
     *            2 (LDF)    - LEFT+DOWN+FLIP (Left shoulder, elbow down, wrist flipped)
     *            3 (LDN)    - LEFT+DOWN+NOFLIP (Left shoulder, elbow down, wrist not flipped)
     *            4 (RUF)    - RIGHT+UP+FLIP (Right shoulder, elbow up, wrist flipped)
     *            5 (RUN)    - RIGHT+UP+NOFLIP (Right shoulder, elbow up, wrist not flipped)
     *            6 (RDF)    - RIGHT+DOWN+FLIP (Right shoulder, elbow down, wrist flipped)
     *            7 (RDN)    - RIGHT+DOWN+NOFLIP (Right shoulder, elbow down, wrist not flipped)
     *         - Second int: Error code with the following meanings:
     *           0  - Success: Configuration calculation completed, valid configuration value returned
     *          -1  - Abnormal robot state: Not initialized completely, try reinitializing before calling
     *          -5  - Invalid input parameters: Incorrect dimension of joint angle array (not 6 elements) or values out of reasonable range
     *
     * @throws arcs::common_interface::AuboException Thrown when input parameters are illegal (e.g., empty array, wrong number of elements)
     *
     * @par Python function prototype
     * getRobotConfiguration(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float]) -> Tuple[int, int]
     *
     * @par Lua function prototype
     * getRobotConfiguration(q: table) -> number, number
     *
     * @par Lua example
     * -- Input 6-axis joint angles (unit: rad) to get configuration and error code
     * local joint_angles = {3.083,1.227,1.098,0.670,-1.870,-0.397}
     * local config_val, err_code = getRobotConfiguration(joint_angles)
     * if err_code == 0 then
     *     print("Robot configuration value: ", config_val)  -- Example output: 4 (corresponding to RUF, Right shoulder, elbow up, wrist flipped)
     * else
     *     print("Failed to get configuration, error code: ", err_code)
     * end
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.getRobotConfiguration","params":[[3.083688522170976,1.2273215976885394,1.098072739631141,0.6705738810610149,-1.870715392248607,-0.39708546603119627]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[4,0]}
     * \endenglish
     */
    ResultWithErrno3 getRobotConfiguration(const std::vector<double>& q);

    /**
     * \chinese
     * 求解movej之间的轨迹点
     *
     * @param q1 movej的起点
     * @param r1 在q1处的交融半径
     * @param q2 movej的终点
     * @param r2 在q2处的交融半径
     * @param d 采样距离
     * @return q1~q2 之间笛卡尔空间离散轨迹点(x,y,z,rx,ry,rz)集合
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathMovej(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float], arg1:
     * float, arg2: List[float], arg3: float, arg4: float) -> List[List[float]]
     *
     * @par Lua函数原型
     * pathMovej(q1: table, r1: number, q2: table, r2: number, d: number) ->
     * table, number
     *
     * @par Lua示例
     * path , num = pathMovej({0.0,-0.2618,1.7453,0.4364,1.5711,0.0},0.25,{0.3234,-0.5405,1.5403,0.5881,1.2962,0.7435},0.03,0.2)
     *
     * \endchinese
     * \english
     * Solve the trajectory points between movej
     *
     * @param q1 Start point of movej
     * @param r1 Blend radius at q1
     * @param q2 End point of movej
     * @param r2 Blend radius at q2
     * @param d Sampling distance
     * @return Discrete trajectory points (x, y, z, rx, ry, rz) between q1 and q2 in Cartesian space
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathMovej(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float], arg1:
     * float, arg2: List[float], arg3: float, arg4: float) -> List[List[float]]
     *
     * @par Lua function prototype
     * pathMovej(q1: table, r1: number, q2: table, r2: number, d: number) ->
     * table, number
     *
     * @par Lua example
     * path , num = pathMovej({0.0,-0.2618,1.7453,0.4364,1.5711,0.0},0.25,{0.3234,-0.5405,1.5403,0.5881,1.2962,0.7435},0.03,0.2)
     *
     * \endenglish
     */
    std::vector<std::vector<double>> pathMovej(const std::vector<double> &q1,
                                               double r1,
                                               const std::vector<double> &q2,
                                               double r2, double d);
    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 计算机械臂末端的雅克比矩阵
     *
     * @param q 关节角
     * @param base_or_end 参考坐标系为基坐标系（或者末端坐标系）
     *        true: 在 base 下描述
     *        false: 在 末端坐标系 下描述
     * @return 雅克比矩阵是否有效
     * 返回值的第一个参数为该构型下对应的雅克比矩阵，第二个为逆解错误码
     * 此接口的错误码返回值在0.28.1-rc.21 0.29.0-alpha.25版本之后做了修改。
     * 此前逆解错误时返回 30082 ，修改后错误码返回列表如下
     * 0 - 成功
     * -23 - 逆解计算不收敛，计算出错
     * -24 - 逆解计算超出机器人最大限制
     * -25 - 逆解输入配置存在错误
     * -26 - 逆解雅可比矩阵计算失败
     * -27 - 目标点存在解析解，但均不满足选解条件
     * -28 - 逆解返回未知类型错误
     * 若错误码非0,则返回值的第一个参数为输入参考关节角qnear
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * calJacobian(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: bool) -> Tuple[List[float], int]
     *
     * @par Lua函数原型
     * calJacobian(q: table, base_or_end: boolean) -> table
     *
     * @par Lua示例
     * calJ_result = calJacobian({0.58815,0.0532,0.62391,2.46,0.479,1.619},true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.calcJacobian","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[0.20822779551242535,-0.5409416184208162,0.2019786999613013,0.061264982268770196,-0.026269884327316487,
     * 0.10131708699859962,0.26388933410019777,-0.36074292664199115,0.1346954733416397,0.04085636647597124,-0.07244204452918337,0.0708466286633346,
     * 0.0,0.10401808481666497,-0.12571344758923886,-0.07741290545882097,0.18818543519232858,0.04628646442706299,0.0,0.5548228314607867,
     * -0.5548228314607868,0.5548228314607868,-0.7901273140338193,0.37230961532208007,0.0,-0.8319685244586092,0.8319685244586091,-0.8319685244586091,
     * -0.5269197820578843,-0.8184088260676008,1.0,3.749399456654644e-33,-6.512048180336603e-18,1.0956823467534067e-16,-0.31313634553301894,
     * 0.43771285536682175],0]}
     * \endchinese
     * \english
     * Calculate the Jacobian matrix at the robot end-effector
     *
     * @param q Joint angles
     * @param base_or_end Reference frame: base (or end-effector)
     *        true: described in base frame
     *        false: described in end-effector frame
     * @return Whether the Jacobian matrix is valid
     * The first parameter of the return value is the Jacobian matrix for this configuration, the second is the error code.
     * The error code list was updated after versions 0.28.1-rc.21 and 0.29.0-alpha.25.
     * Previously, inverse kinematics errors returned 30082. The updated error codes are:
     * 0 - Success
     * -23 - Inverse kinematics calculation does not converge, calculation error
     * -24 - Inverse kinematics calculation exceeds robot limits
     * -25 - Inverse kinematics input configuration error
     * -26 - Inverse kinematics Jacobian calculation failed
     * -27 - Analytical solution exists but none satisfy the selection criteria
     * -28 - Unknown error in inverse kinematics
     * If the error code is not 0, the first parameter of the return value is the input reference joint angles qnear
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * calJacobian(self: pyaubo_sdk.RobotAlgorithm, arg0: List[float],
     * arg1: bool) -> Tuple[List[float], int]
     *
     * @par Lua function prototype
     * calJacobian(q: table, base_or_end: boolean) -> table
     *
     * @par Lua example
     * calJ_result = calJacobian({0.58815,0.0532,0.62391,2.46,0.479,1.619},true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.calcJacobian","params":[[0.58815,0.0532,0.62391,2.46,0.479,1.619],true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[0.20822779551242535,-0.5409416184208162,0.2019786999613013,0.061264982268770196,-0.026269884327316487,
     * 0.10131708699859962,0.26388933410019777,-0.36074292664199115,0.1346954733416397,0.04085636647597124,-0.07244204452918337,0.0708466286633346,
     * 0.0,0.10401808481666497,-0.12571344758923886,-0.07741290545882097,0.18818543519232858,0.04628646442706299,0.0,0.5548228314607867,
     * -0.5548228314607868,0.5548228314607868,-0.7901273140338193,0.37230961532208007,0.0,-0.8319685244586092,0.8319685244586091,-0.8319685244586091,
     * -0.5269197820578843,-0.8184088260676008,1.0,3.749399456654644e-33,-6.512048180336603e-18,1.0956823467534067e-16,-0.31313634553301894,
     * 0.43771285536682175],0]}
     * \endenglish
     */
    ResultWithErrno calcJacobian(const std::vector<double> &q,
                                 bool base_or_end);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 求解交融的轨迹点
     *
     * @param type
     * 0-movej 和 movej
     * 1-movej 和 movel
     * 2-movel 和 movej
     * 3-movel 和 movel
     * @param q_start 交融前路径的起点
     * @param q_via 交融点
     * @param q_to 交融后路径的终点
     * @param r 在q_via处的交融半径
     * @param d 采样距离
     * @return q_via处的交融段笛卡尔空间离散轨迹点(x,y,z)集合
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * pathBlend3Points(self: pyaubo_sdk.RobotAlgorithm, arg0: int, arg1:
     * List[float], arg2: List[float], arg3: List[float], arg4: float, arg5:
     * float) -> List[List[float]]
     *
     * @par Lua函数原型
     * pathBlend3Points(type: number, q_start: table, q_via: table, q_to: table,
     * r: number, d: number) -> table, number
     *
     * @par Lua示例
     * q_via , num = pathBlend3Points(1,{0.58815,0.0532,0.62391,2.46,0.479,1.619},{0.0,-0.2618,1.7453,0.4364,1.5711,0.0},
     * {0.3234,-0.5405,1.5403,0.5881,1.2962,0.7435},0.25,0.02)
     *
     * \endchinese
     * \english
     * Solve the blended trajectory points
     *
     * @param type
     * 0-movej and movej
     * 1-movej and movel
     * 2-movel and movej
     * 3-movel and movel
     * @param q_start Start point before blending
     * @param q_via Blending point
     * @param q_to End point after blending
     * @param r Blend radius at q_via
     * @param d Sampling distance
     * @return Discrete trajectory points (x, y, z) of the blend segment at q_via in Cartesian space
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * pathBlend3Points(self: pyaubo_sdk.RobotAlgorithm, arg0: int, arg1:
     * List[float], arg2: List[float], arg3: List[float], arg4: float, arg5:
     * float) -> List[List[float]]
     *
     * @par Lua function prototype
     * pathBlend3Points(type: number, q_start: table, q_via: table, q_to: table,
     * r: number, d: number) -> table, number
     *
     * @par Lua example
     * q_via , num = pathBlend3Points(1,{0.58815,0.0532,0.62391,2.46,0.479,1.619},{0.0,-0.2618,1.7453,0.4364,1.5711,0.0},
     * {0.3234,-0.5405,1.5403,0.5881,1.2962,0.7435},0.25,0.02)
     *
     * \endenglish
     */
    std::vector<std::vector<double>> pathBlend3Points(
        int type, const std::vector<double> &q_start,
        const std::vector<double> &q_via, const std::vector<double> &q_to,
        double r, double d);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 生成用于负载辨识的激励轨迹
     * 此接口内部调用pathBufferAppend
     * 将离线轨迹存入buffer中，后续可通过movePathBuffer运行离线轨迹
     * @param name 轨迹名字
     * @param traj_conf 各关节轨迹的限制条件
     * traj_conf.move_axis: 运动的轴
     * 由于实际用户现场可能不希望在负载辨识时控制机械臂多关节大幅度运动，故最好选用traj_conf.move_axis=LoadIdentifyMoveAxis::Joint_4_6;
     * traj_conf.init_joint:
     * 运动初始关节角,为了避免关节5接近零位时的奇异问题，应设置traj_conf.init_joint[4]的绝对值不小于0.3(rad)，接近1.57(rad)为宜。其余关节的关节角可任意设置
     * traj_conf.lower_joint_bound, traj_conf.upper_joint_bound:
     * 关节角上下限,维度应与config.move_axis维度保持一致,推荐设置upper_joint_bound为2，lower_joint_bound为-2
     * config.max_velocity, config.max_acceleration:
     * 关节角速度角加速度限制,维度应与config.move_axis维度保持一致,出于安全和驱动器跟随性能的考虑,推荐设置max_velocity=3,max_acceleration=5
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
     * Generate excitation trajectory for payload identification
     * This interface internally calls pathBufferAppend
     * The offline trajectory is stored in the buffer, and can be executed later via movePathBuffer
     * @param name Trajectory name
     * @param traj_conf Joint trajectory constraints
     * traj_conf.move_axis: Moving axes
     * Since users may not want large multi-joint movements during payload identification, it is recommended to use traj_conf.move_axis=LoadIdentifyMoveAxis::Joint_4_6;
     * traj_conf.init_joint:
     * Initial joint angles. To avoid singularity issues near joint 5 zero position, set abs(traj_conf.init_joint[4]) >= 0.3(rad), preferably close to 1.57(rad). Other joints can be set arbitrarily.
     * traj_conf.lower_joint_bound, traj_conf.upper_joint_bound:
     * Joint angle limits, dimensions should match config.move_axis. Recommended: upper_joint_bound=2, lower_joint_bound=-2
     * config.max_velocity, config.max_acceleration:
     * Joint velocity and acceleration limits, dimensions should match config.move_axis. For safety and driver performance, recommended: max_velocity=3, max_acceleration=5
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
    int generatePayloadIdentifyTraj(const std::string &name,
                                    const TrajConfig &traj_conf);
    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 负载辨识轨迹是否生成完成
     *
     * @return 完成返回0; 正在进行中返回1; 计算失败返回<0;
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.payloadIdentifyTrajGenFinished","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Whether payload identification trajectory generation is finished
     *
     * @return 0 if finished; 1 if in progress; <0 if failed;
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.payloadIdentifyTrajGenFinished","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int payloadIdentifyTrajGenFinished();

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 求解 moveS 的轨迹点
     *
     * @brief pathMoveS
     * @param qs 样条轨迹生成点集合
     * @param d 采样距离
     * @return
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Solve the trajectory points for moveS
     *
     * @brief pathMoveS
     * @param qs Spline trajectory generation point set
     * @param d Sampling distance
     * @return
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    std::vector<std::vector<double>> pathMoveS(
        const std::vector<std::vector<double>> &qs, double d);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 振动抑制参数辨识算法接口
     *
     * @param q 当前关节角度
     * @param qd 当前关节速度
     * @param target_q 目标关节角度
     * @param target_qd 关节速度
     * @param target_qdd 关节加速度
     * @param tool_offset 工具TCP信息
     * @param omega 振动频率
     * @param zeta 振动阻尼比
     * @return 振动抑制参数和是否辨识成功
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * calibVibrationParams(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * List[List[float]], arg1: List[List[float]], arg2: List[List[float]], arg3: List[List[float]],
     * arg4: List[List[float]], arg5: List[float]) -> list[list[float]],int
     *
     * @par Lua函数原型
     * calibVibrationParams(q: table,qd: table, target_q: table, target_qd: table,
     * target_qdd: table, tool_offset: table, omega: table, zeta: table) -> table,number
     * \endchinese
     */
    ResultWithErrno1 calibVibrationParams(const std::vector<std::vector<double>> &q,
                             const std::vector<std::vector<double>> &qd,
                             const std::vector<std::vector<double>> &target_q,
                             const std::vector<std::vector<double>> &target_qd,
                             const std::vector<std::vector<double>> &target_qdd,
                             const std::vector<double> &tool_offset);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 振动抑制参数辨识算法接口1
     *
     * @param record_cache_name 目标缓存名称
     * @param tool_offset 工具TCP信息
     * @return 振动抑制参数和是否辨识成功
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * calibVibrationParams(self: pyaubo_sdk.RobotAlgorithm, arg0:
     * string, arg1: List[float]) -> list[list[float]],int
     *
     * @par Lua函数原型
     * calibVibrationParams(record_cache_name: string, tool_offset: table) -> table,number
     * \endchinese
     */
    ResultWithErrno1 calibVibrationParams1(const std::string &record_cache_name, const std::vector<double> &tool_offset);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 判断是否需要重新辨识振动参数
     *
     * @param param1 参考参数（如上一次辨识结果）
     * @param param2 当前参数（如新测量结果）
     * @param threshold 变化阈值（0~1），超过则需重新辨识
     * @return >0 需要重新辨识，=0 不需要，<0 出错
     *
     * @par Lua函数原型
     * needVibrationRecalib(param1: table, param2: table, threshold: number) -> number
     *
     * @par JSON-RPC示例
     * {"jsonrpc":"2.0","method":"VibrationController.needVibrationRecalib",
     *  "params":[param1_obj, param2_obj, 0.1],"id":1}
     * \endchinese
     */
    int needVibrationRecalib(const VibrationRecalibrationParameter &param1,
                             const VibrationRecalibrationParameter &param2,
                             double threshold);

    /**
     * @ingroup RobotAlgorithm
     * \chinese
     * 验证机器人运动路径从起点到终点的可达性
     *
     * 该接口通过采样的方式验证指定路径是否存在超限、自碰撞、奇异等不可达情况，
     * 支持关节角<->关节角、位姿<->位姿两种路径类型验证。
     *
     * @param type 路径类型标识，用于指定起点和终点的数据类型：
     *        0 - 起点：关节角，终点：关节角
     *        1 - 起点：位姿，终点：位姿
     * @param start 路径起点数据
     * @param r1 起点交融半径，单位：m（米）
     * @param end 路径终点数据
     * @param r2 终点交融半径，单位：m（米）
     * @param d 路径采样间隔，单位：m（米），间隔越小验证精度越高，但耗时越长
     * @return 路径可达性结果码：
     *        0  - 可达：路径无异常，可正常运动
     *       -18 - 路径中存在关节超限/笛卡尔空间超限
     *       -21 - 轨迹生成失败
     *       -22 - 路径中机器人本体发生自碰撞
     *       -24 - 路径中经过机器人奇异位形
     *       -27 - 目标点有解但超出关节限位
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Lua函数原型
     * validatePath(type, start, r1, end, r2, d) -> number
     *
     * @par Lua示例
     * -- 验证6轴机器人关节角到关节角的路径可达性
     * local start_joint = {0.0, 0.0, 90.0, 0.0, 90.0, 0.0}  --
     * 关节角（单位：度） local end_joint = {30.0, 0.0, 90.0, 0.0, 90.0, 0.0}
     * local result = validatePath(0, start_joint, 0.01, end_joint, 0.01, 0.05)
     *
     * @par Python函数原型
     * validatePath(type: int, start: list[float], r1: float, end: list[float],
     * r2: float, d: float) -> int
     *
     * @par Python示例
     * # 验证6轴机器人关节角到位姿的路径可达性
     * start_joint = [0.0, 0.0, math.pi/2, 0.0, math.pi/2, 0.0]
     * end_pose = [0.5, 0.2, 0.8, 0.0, math.pi/2, 0.0]
     * result = validatePath(1, start_joint, 0.01, end_pose, 0.01, 0.05)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.validatePath","params":[0,
     * [0.0,0.0,1.57,0.0,1.57,0.0], 0.01, [0.52,0.0,1.57,0.0,1.57,0.0], 0.01,
     * 0.05],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     *
     * \english
     * Validate the reachability of the robot's motion path from start point to
     * end point
     *
     * This interface verifies whether the specified path has unreachable
     * conditions such as out-of-limit, self-collision, singularity, etc., by
     * sampling. It supports four path type validations: Joint-Joint,
     * Joint-Pose, Pose-Joint, Pose-Pose.
     *
     * @param type Path type identifier, specifying the data type of start and
     * end points:
     *    0 - Start: Joint angles, End: Joint angles
     *    1 - Start: Pose, End: Pose
     * @param start: Start point data of the path
     *    - Joint angles
     *    - Pose
     * @param r1 Start point blending radius, unit: m (meters), used to smooth
     * path sampling near the start point
     * @param end End point data of the path, format is consistent with start
     * (matching the type specified by type)
     * @param r2 End point blending radius, unit: m (meters), used to smooth
     * path sampling near the end point
     * @param d Path sampling interval, unit: m (meters). Smaller intervals
     * improve verification accuracy but increase time consumption
     *
     * @return Path reachability result code:
     *    0  - Reachable: Path is normal, movement is possible
     *    -18 - Joint/ Cartesian space limits exceeded in the path
     *    -21 - Trajectory generation failed
     *    -22 - Self-collision of the robot body in the path
     *    -24 - Path passing through robot singular configuration
     *    -27 - The target point has a solution but exceeds joint limits
     * configuration
     *
     * @throws arcs::common_interface::AuboException Thrown when parameters are
     * invalid (e.g., mismatched data length, values out of reasonable range,
     * etc.)
     *
     * @par Lua function prototype
     * validatePath(type, start, r1, end, r2, d) -> integer
     *
     * @par Lua example
     * -- Validate reachability of Joint-Joint path for 6-axis robot
     * local start_joint = {0.0, 0.0, 90.0, 0.0, 90.0, 0.0}
     * local end_joint = {30.0, 0.0, 90.0, 0.0, 90.0, 0.0}
     * result = validatePath(0, start_joint, 0.01, end_joint, 0.01, 0.05)
     *
     * @par Python function prototype
     * validatePath(type: int, start: list[float], r1: float, end: list[float],
     * r2: float, d: float) -> int
     *
     * @par Python example
     * # Validate reachability of Joint-Pose path for 6-axis robot
     * start_joint = [0.0, 0.0, math.pi/2, 0.0, math.pi/2, 0.0]
     * end_pose = [0.5, 0.2, 0.8, 0.0, math.pi/2, 0.0]
     * result = validatePath(1, start_joint, 0.01,end_pose, 0.01, 0.05)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.RobotAlgorithm.validatePath","params":[0,
     * [0.0,0.0,1.57,0.0,1.57,0.0], 0.01, [0.52,0.0,1.57,0.0,1.57,0.0], 0.01,
     * 0.005],"id":1}
     *
     * @par JSON-RPC response example {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int validatePath(int type, const std::vector<double> &start, double r1,
                     const std::vector<double> &end, double r2, double d);

protected:
    void *d_;
};
using RobotAlgorithmPtr = std::shared_ptr<RobotAlgorithm>;

} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_ROBOT_ALGORITHM_INTERFACE_H
