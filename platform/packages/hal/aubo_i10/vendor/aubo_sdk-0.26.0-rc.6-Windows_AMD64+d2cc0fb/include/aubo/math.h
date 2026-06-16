/** @file  math.h
 *  \~chinese @brief 数学方法接口，如欧拉角与四元数转换、位姿的加减运算
 *  \~english @brief Mathematic operation interface, such as euler to quaternion conversion, addition/subtraction of poses
 */
#ifndef AUBO_SDK_MATH_INTERFACE_H
#define AUBO_SDK_MATH_INTERFACE_H

#include <vector>
#include <memory>

#include <aubo/type_def.h>
#include <aubo/global_config.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup Math Math (数学工具)
 * \~chinese 数学工具API接口
 */
class ARCS_ABI_EXPORT Math
{
public:
    Math();
    virtual ~Math();

    /**
     * @ingroup Math
     * \english
     * Pose addition
     *
     * Both arguments contain three position parameters (x, y, z) jointly called
     * P, and three rotation parameters (R_x, R_y, R_z) jointly called R. This
     * function calculates the result x_3 as the addition of the given poses as
     * follows:
     *
     * p_3.P = p_1.P + p_2.P
     *
     * p_3.R = p_1.R * p_2.R
     *
     * @param p1 Tool pose 1
     * @param p2 Tool pose 2
     * @return sum of position parts and product of rotation parts (pose)
     *
     * @par Python interface prototype
     * poseAdd(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float]) ->
     * List[float]
     *
     * @par Lua interface prototype
     * poseAdd(p1: table, p2: table) -> table
     *
     * @par Lua example
     * pose_add = poseAdd({0.2, 0.5, 0.1, 1.57, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.poseAdd","params":[[0.2, 0.5, 0.1, 1.57,
     * 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.4,1.0,0.7,3.14,-0.0,0.0]}
     * \endengish
     *
     * \chinese
     * 位姿相加。
     * 两个参数都包含三个位置参数（x、y、z），统称为P，
     * 以及三个旋转参数（R_x、R_y、R_z），统称为R。
     * 此函数根据以下方式计算结果 p_3，即给定位姿的相加：
     * p_3.P = p_1.P + p_2.P,
     * p_3.R = p_1.R * p_2.R
     *
     * @param p1 工具位姿1（pose）
     * @param p2 工具位姿2（pose）
     * @return 位置部分之和和旋转部分之积（pose）
     *
     * @par Python函数原型
     * poseAdd(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float]) ->
     * List[float]
     *
     * @par Lua函数原型
     * poseAdd(p1: table, p2: table) -> table
     *
     * @par Lua示例
     * pose_add = poseAdd({0.2, 0.5, 0.1, 1.57, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.poseAdd","params":[[0.2, 0.5, 0.1, 1.57,
     * 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.4,1.0,0.7,3.14,-0.0,0.0]}
     * \endchinese
     */
    std::vector<double> poseAdd(const std::vector<double> &p1,
                                const std::vector<double> &p2);

    /**
     * @ingroup Math
     * \chinese
     * 位姿相减
     *
     * 两个参数都包含三个位置参数（x、y、z），统称为P，
     * 以及三个旋转参数（R_x、R_y、R_z），统称为R。
     * 此函数根据以下方式计算结果 p_3，即给定位姿的相加：
     * p_3.P = p_1.P - p_2.P,
     * p_3.R = p_1.R * p_2.R.inverse
     *
     * @param p1 工具位姿1
     * @param p2 工具位姿2
     * @return 位姿相减计算结果
     *
     * @par Python函数原型
     * poseSub(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float]) ->
     * List[float]
     *
     * @par Lua函数原型
     * poseSub(p1: table, p2: table) -> table
     *
     * @par Lua示例
     * pose_sub = poseSub({0.2, 0.5, 0.1, 1.57, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.poseSub","params":[[0.2, 0.5, 0.1, 1.57,
     * 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,-0.5,0.0,-0.0,0.0]}
     * \endchinese
     * 
     * \english
     * Pose subtraction
     *
     * Both arguments contain three position parameters (x, y, z) jointly called
     * P, and three rotation parameters (R_x, R_y, R_z) jointly called R. This
     * function calculates the result x_3 as the addition of the given poses as
     * follows:
     *
     * p_3.P = p_1.P - p_2.P,
     *
     * p_3.R = p_1.R * p_2.R.inverse
     *
     * @param p1 tool pose 1
     * @param p2 tool pose 2
     * @return difference between two poses
     *
     * @par Python interface prototype
     * poseSub(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float]) ->
     * List[float]
     *
     * @par Lua interface prototype
     * poseSub(p1: table, p2: table) -> table
     *
     * @par Lua example
     * pose_sub = poseSub({0.2, 0.5, 0.1, 1.57, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.poseSub","params":[[0.2, 0.5, 0.1, 1.57,
     * 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.0,-0.5,0.0,-0.0,0.0]}
     * \endenglish
     */
    std::vector<double> poseSub(const std::vector<double> &p1,
                                const std::vector<double> &p2);

    /**
     * @ingroup Math
     * \chinese
     * 计算线性插值
     *
     * @param p1 起点的TCP位姿
     * @param p2 终点的TCP位姿
     * @param alpha 系数，
     * 当0<alpha<1，返回p1和p2两点直线的之间靠近p1端且占总路径比例为alpha的点；
     * 例如当alpha=0.3,返回的是靠近p1那端，总路径的百分之30的点；
     * 当alpha>1,返回p2；
     * 当alpha<0,返回p1；
     * @return 插值计算结果
     *
     * @par Python函数原型
     * interpolatePose(self: pyaubo_sdk.Math, arg0: List[float], arg1:
     * List[float], arg2: float) -> List[float]
     *
     * @par Lua函数原型
     * interpolatePose(p1: table, p2: table, alpha: number) -> table
     *
     * @par Lua示例
     * pose_interpolate = interpolatePose({0.2, 0.2, 0.4, 0, 0, 0},{0.2, 0.2, 0.6, 0, 0, 0},0.5)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.interpolatePose","params":[[0.2, 0.2,
     * 0.4, 0, 0, 0],[0.2, 0.2, 0.6, 0, 0, 0],0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.2,0.2,0.5,0.0,-0.0,0.0]}
     * \endchinese
     *
     * \english
     * Calculate linear interpolation
     *
     * @param p1 starting TCP pose
     * @param p2 ending TCP pose
     * @param alpha coefficient;
     * When 0<alpha<1，return a point between p1 & p2 that is closer to p1, at alpha percentage of the path；
     * For example when alpha=0.3,point returned is closer to p1，at 30% of the total distance;
     * When alpha>1, return p2；
     * When alpha<0,return p1；
     * @return interpolation result
     *
     * @par Python interface prototype
     * interpolatePose(self: pyaubo_sdk.Math, arg0: List[float], arg1:
     * List[float], arg2: float) -> List[float]
     *
     * @par Lua interface prototype
     * interpolatePose(p1: table, p2: table, alpha: number) -> table
     *
     * @par Lua example
     * pose_interpolate = interpolatePose({0.2, 0.2, 0.4, 0, 0, 0},{0.2, 0.2, 0.6, 0, 0, 0},0.5)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.interpolatePose","params":[[0.2, 0.2,
     * 0.4, 0, 0, 0],[0.2, 0.2, 0.6, 0, 0, 0],0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.2,0.2,0.5,0.0,-0.0,0.0]}
     * \endenglish
     *
     */
    std::vector<double> interpolatePose(const std::vector<double> &p1,
                                        const std::vector<double> &p2,
                                        double alpha);
    /**
     * @ingroup Math
     * \chinese
     * 位姿变换
     *
     * 第一个参数 p_from 用于转换第二个参数 p_from_to，并返回结果。
     * 这意味着结果是从 p_from 的坐标系开始，
     * 然后在该坐标系中移动 p_from_to后的位姿。
     *
     * 这个函数可以从两个不同的角度来看。
     * 一种是函数将 p_from_to 根据 p_from 的参数进行转换，即平移和旋转。
     * 另一种是函数被用于获取结果姿态，先对 p_from 进行移动，然后再对 p_from_to
     * 进行移动。 如果将姿态视为转换矩阵，它看起来像是：
     *
     * T_world->to = T_world->from * T_from->to，
     * T_x->to = T_x->from * T_from->to
     *
     * 这两个方程描述了姿态变换的基本原理，根据给定的起始姿态和相对于起始姿态的姿态变化，可以计算出目标姿态。
     *
     * 举个例子，已知B相对于A的位姿、C相对于B的位姿，求C相对于A的位姿。
     * 第一个参数是B相对于A的位姿，第二个参数是C相对于B的位姿，
     * 返回值是C相对于A的位姿。
     *
     * @param pose_from 起始位姿（空间向量）
     * @param pose_from_to 相对于起始位姿的姿态变化（空间向量）
     * @return 结果位姿 (空间向量)
     *
     * @par Python函数原型
     * poseTrans(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float]) ->
     * List[float]
     *
     * @par Lua函数原型
     * poseTrans(pose_from: table, pose_from_to: table) -> table
     *
     * @par Lua示例
     * pose_trans = poseTrans({0.2, 0.5, 0.1, 1.57, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.poseTrans","params":[[0.2, 0.5,
     * 0.1, 1.57, 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.4,-0.09960164640373415,0.6004776374923573,3.14,-0.0,0.0]}
     * \endchinese
     * 
     * \english
     * Pose transformation
     *
     * The first argument, p_from, is used to transform the second argument,
     * p_from_to, and the result is then returned. This means that the result is
     * the resulting pose, when starting at the coordinate system of p_from, and
     * then in that coordinate system moving p_from_to.
     *
     * This function can be seen in two different views. Either the function
     * transforms, that is translates and rotates, p_from_to by the parameters
     * of p_from. Or the function is used to get the resulting pose, when first
     * making a move of p_from and then from there, a move of p_from_to. If the
     * poses were regarded as transformation matrices, it would look like:
     *
     * T_world->to = T_world->from * T_from->to，
     * T_x->to = T_x->from * T_from->to
     *
     *
     * These two equations describes the foundations for pose transformation.
     * Based on a starting pose and the pose transformation relative to the starting pose, we can get the target pose.
     *
     * For example, we know pose of B relative to A, pose of C relative to B, find pose of C relative to A.
     * param 1 is pose of B relative to A，param 2 is pose of C relative to B，
     * the return value is the pose of C relative to A
     *
     * @param pose_from starting pose（vector in 3D space）
     * @param pose_from_to pose transformation relative to starting pose（vector in 3D space）
     * @return final pose (vector in 3D space)
     *
     * @par Python interface prototype
     * poseTrans(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float]) ->
     * List[float]
     *
     * @par Lua interface prototype
     * poseTrans(pose_from: table, pose_from_to: table) -> table
     *
     * @par Lua example
     * pose_trans = poseTrans({0.2, 0.5, 0.1, 1.57, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.poseTrans","params":[[0.2, 0.5,
     * 0.1, 1.57, 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.4,-0.09960164640373415,0.6004776374923573,3.14,-0.0,0.0]}
     * \endenglish
     */
    std::vector<double> poseTrans(const std::vector<double> &pose_from,
                                  const std::vector<double> &pose_from_to);

    /**
     * \english
     * Pose inverse transformation
     *
     * Given pose of C relative to A, pose of C relative to B, find pose of B relative to A.
     * param 1 is pose of C relative to A，param 2 is pose of C relative to B，
     * the return value is the pose of B relative to A
     *
     * @param pose_from starting pose
     * @param pose_to_from pose transformation relative to final pose
     * @return resulting pose
     *
     * @par Python interface prototype
     * poseTransInv(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float])
     * -> List[float]
     *
     * @par Lua interface prototype
     * poseTransInv(pose_from: table, pose_to_from: table) -> table
     *
     * @par Lua example
     * pose_trans_inv = poseTransInv({0.4, -0.0996016, 0.600478, 3.14, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.poseTransInv","params":[[0.4, -0.0996016,
     * 0.600478, 3.14, 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.2,0.5000000464037341,0.10000036250764266,1.57,-0.0,0.0]}
     * \endenglish
     *
     * @ingroup Math
     * \chinese
     * 姿态逆变换
     *
     * 已知C相对于A的位姿、C相对于B的位姿，求B相对于A的位姿。
     * 第一个参数是C相对于A的位姿，第二个参数是C相对于B的位姿，
     * 返回值是B相对于A的位姿。
     *
     * @param pose_from 起始位姿
     * @param pose_to_from 相对于结果位姿的姿态变化
     * @return 结果位姿
     *
     * @par Python函数原型
     * poseTransInv(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float])
     * -> List[float]
     *
     * @par Lua函数原型
     * poseTransInv(pose_from: table, pose_to_from: table) -> table
     *
     * @par Lua示例
     * pose_trans_inv = poseTransInv({0.4, -0.0996016, 0.600478, 3.14, 0, 0},{0.2, 0.5, 0.6, 1.57, 0, 0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.poseTransInv","params":[[0.4, -0.0996016,
     * 0.600478, 3.14, 0, 0],[0.2, 0.5, 0.6, 1.57, 0, 0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.2,0.5000000464037341,0.10000036250764266,1.57,-0.0,0.0]}
     * \endchinese
     */
    std::vector<double> poseTransInv(const std::vector<double> &pose_from,
                                     const std::vector<double> &pose_to_from);

    /**
     * @ingroup Math
     * \chinese
     * 获取位姿的逆
     *
     * @param pose 工具位姿（空间向量）
     * @return 工具位姿的逆转换（空间向量）
     *
     * @par Python函数原型
     * poseInverse(self: pyaubo_sdk.Math, arg0: List[float]) -> List[float]
     *
     * @par Lua函数原型
     * poseInverse(pose: table) -> table
     *
     * @par Lua示例
     * pose_inverse = poseInverse({0.2, 0.5, 0.1, 1.57, 0, 3.14})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.poseInverse","params":[[0.2, 0.5,
     * 0.1, 1.57, 0, 3.14]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.19920341988726448,-0.09960155178838484,-0.5003973704832628,
     * 1.5699999989900404,-0.0015926530848129354,-3.1415913853161266]}
     * 
     * \endchinese
     *
     * \english
     * Get the inverse of a pose
     *
     * @param pose tool pose (spatial vector)
     * @return inverse tool pose transformation (spatial vector)
     *
     * @par Python interface prototype
     * poseInverse(self: pyaubo_sdk.Math, arg0: List[float]) -> List[float]
     *
     * @par Lua interface prototype
     * poseInverse(pose: table) -> table
     *
     * @par Lua example
     * pose_inverse = poseInverse({0.2, 0.5, 0.1, 1.57, 0, 3.14})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.poseInverse","params":[[0.2, 0.5,
     * 0.1, 1.57, 0, 3.14]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.19920341988726448,-0.09960155178838484,-0.5003973704832628,
     * 1.5699999989900404,-0.0015926530848129354,-3.1415913853161266]}
     * \endenglish
     *
     */
    std::vector<double> poseInverse(const std::vector<double> &pose);

    /**
     * @ingroup Math
     * \chinese
     * 计算两个位姿的位置距离
     *
     * @param p1 位姿1
     * @param p2 位姿2
     * @return 两个位姿的位置距离
     *
     * @par Lua函数原型
     * poseDistance(p1: table, p2: table) -> number
     *
     * @par Lua示例
     * pose_distance = poseDistance({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},{0.2, 0.5, 0.6, 0, -0.172, 0.0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.poseDistance","params":[[0.1, 0.3, 0.1,
     * 0.3142, 0.0, 1.571],[0.2, 0.5, 0.6, 0, -0.172, 0.0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.5477225575051661}
     * \endchinese
     * 
     * \english
     * Calculate distance between two poses
     *
     * @param p1 pose 1
     * @param p2 pose 2
     * @return distance between the poses
     *
     * @par Lua function prototype
     * poseDistance(p1: table, p2: table) -> number
     *
     * @par Lua example
     * pose_distance = poseDistance({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},{0.2, 0.5, 0.6, 0, -0.172, 0.0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.poseDistance","params":[[0.1, 0.3, 0.1,
     * 0.3142, 0.0, 1.571],[0.2, 0.5, 0.6, 0, -0.172, 0.0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.5477225575051661}
     * \endenglish
     *
     */
    double poseDistance(const std::vector<double> &p1,
                        const std::vector<double> &p2);

    /**
     * @ingroup Math
     * \chinese
     * 计算两个位姿的轴角距离
     *
     * @param p1 位姿1
     * @param p2 位姿2
     * @return 轴角距离
     *
     * @par Lua函数原型
     * poseAngleDistance(p1: table, p2: table) -> number
     *
     * @par Lua示例
     * pose_angle_distance = poseAngleDistance({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},{0.2, 0.5, 0.6, 0, -0.172, 0.0})
     *
     * \endchinese
     *
     * \english
     * Calculate axis-angle difference between two poses
     *
     * @param p1 pose 1
     * @param p2 pose 2
     * @return axis angle difference
     *
     * @par Lua函数原型
     * poseAngleDistance(p1: table, p2: table) -> number
     *
     * @par Lua示例
     * pose_angle_distance = poseAngleDistance({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},{0.2, 0.5, 0.6, 0, -0.172, 0.0})
     *
     * \endenglish
     */
    double poseAngleDistance(const std::vector<double> &p1,

                             const std::vector<double> &p2);

    /**
     * @ingroup Math
     * \chinese
     * 判断两个位姿是否相等
     *
     * @param p1 位姿1
     * @param p2 位姿2
     * @param eps 误差
     * @return 相等返回true，反之返回false
     *
     * @par Lua函数原型
     * poseEqual(p1: table, p2: table, eps: number) -> boolean
     *
     * @par Lua示例
     * pose_equal = poseEqual({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},{0.1, 0.3, 0.1, 0.3142, 0.0, 1.5711},0.01)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.poseEqual","params":[[0.1, 0.3, 0.1,
     * 0.3142, 0.0, 1.571],[0.1, 0.3, 0.1, 0.3142, 0.0, 1.5711],0.01]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endchinese
     *
     * \english
     * Determine if two poses are equivalent
     *
     * @param p1 pose 1
     * @param p2 pose 2
     * @param eps error margin
     * @return true or false
     *
     * @par Lua函数原型
     * poseEqual(p1: table, p2: table, eps: number) -> boolean
     *
     * @par Lua示例
     * pose_equal = poseEqual({0.1, 0.3, 0.1, 0.3142, 0.0, 1.571},{0.1, 0.3, 0.1, 0.3142, 0.0, 1.5711},0.01)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.poseEqual","params":[[0.1, 0.3, 0.1,
     * 0.3142, 0.0, 1.571],[0.1, 0.3, 0.1, 0.3142, 0.0, 1.5711],0.01],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     * \endenglish
     */
    bool poseEqual(const std::vector<double> &p1, const std::vector<double> &p2,
                   double eps = 5e-5);

    /**
     * @ingroup Math
     * \chinese
     * @param F_b_a_old
     * @param V_in_a
     * @param type
     * @return
     *
     * @par Python函数原型
     * transferRefFrame(self: pyaubo_sdk.Math, arg0: List[float], arg1:
     * List[float[3]], arg2: int) -> List[float]
     *
     * @par Lua函数原型
     * transferRefFrame(F_b_a_old: table, V_in_a: table, type: number) -> table
     * \endchinese
     *
     * \english
     * @param F_b_a_old
     * @param V_in_a
     * @param type
     * @return
     *
     * @par Python interface prototype
     * transferRefFrame(self: pyaubo_sdk.Math, arg0: List[float], arg1:
     * List[float[3]], arg2: int) -> List[float]
     *
     * @par Lua interface prototype
     * transferRefFrame(F_b_a_old: table, V_in_a: table, type: number) -> table
     * \endenglish
     */
    std::vector<double> transferRefFrame(const std::vector<double> &F_b_a_old,
                                         const Vector3d &V_in_a, int type);

    /**
     * @ingroup Math
     * \chinese
     * 姿态旋转
     *
     * @param pose
     * @param rotv
     * @return
     *
     * @par Python函数原型
     * poseRotation(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float])
     * -> List[float]
     *
     * @par Lua函数原型
     * poseRotation(pose: table, rotv: table) -> table
     * \endchinese
     * 
     * \english
     * Pose rotation
     *
     * @param pose
     * @param rotv
     * @return
     *
     * @par Python interface prototype
     * poseRotation(self: pyaubo_sdk.Math, arg0: List[float], arg1: List[float])
     * -> List[float]
     *
     * @par Lua interface prototype
     * poseRotation(pose: table, rotv: table) -> table
     * \endenglish
     */
    std::vector<double> poseRotation(const std::vector<double> &pose,
                                     const std::vector<double> &rotv);

    /**
     * @ingroup Math
     * \chinese 
     * 欧拉角转四元数
     *
     * @param rpy 欧拉角
     * @return 四元数
     *
     * @par Python函数原型
     * rpyToQuaternion(self: pyaubo_sdk.Math, arg0: List[float]) -> List[float]
     *
     * @par Lua函数原型
     * rpyToQuaternion(rpy: table) -> table
     *
     * @par Lua示例
     * quaternion = rpyToQuaternion({0.611, 0.785, 0.960})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.rpyToQuaternion","params":[[0.611, 0.785,
     * 0.960]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.834721517970497,0.07804256900772265,0.4518931575790371,0.3048637712043723]}
     * \endchinese
     *
     * \english 
     * Euler angles to quaternions
     *
     * @param rpy euler angles
     * @return quaternions
     *
     * @par Python interface prototype
     * rpyToQuaternion(self: pyaubo_sdk.Math, arg0: List[float]) -> List[float]
     *
     * @par Lua interface prototype
     * rpyToQuaternion(rpy: table) -> table
     *
     * @par Lua example
     * quaternion = rpyToQuaternion({0.611, 0.785, 0.960})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.rpyToQuaternion","params":[[0.611, 0.785,
     * 0.960]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.834721517970497,0.07804256900772265,0.4518931575790371,0.3048637712043723]}
     * \endenglish
     */
    std::vector<double> rpyToQuaternion(const std::vector<double> &rpy);

    /**
     * @ingroup Math
     * \chinese
     * 四元数转欧拉角
     *
     * @param quat 四元数
     * @return 欧拉角
     *
     * @par Python函数原型
     * quaternionToRpy(self: pyaubo_sdk.Math, arg0: List[float]) -> List[float]
     *
     * @par Lua函数原型
     * quaternionToRpy(quat: table) -> table
     *
     * @par Lua示例
     * rpy = quaternionToRpy({0.834722,0.0780426, 0.451893, 0.304864})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.quaternionToRpy","params":[[0.834722,
     * 0.0780426, 0.451893, 0.304864]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.6110000520523781,0.7849996877683915,0.960000543982093]}
     * \endchinese
     *
     * \english
     * Quaternions to euler angles
     *
     * @param quat quaternions
     * @return euler angles
     *
     * @par Python interface prototype
     * quaternionToRpy(self: pyaubo_sdk.Math, arg0: List[float]) -> List[float]
     *
     * @par Lua interface prototype
     * quaternionToRpy(quat: table) -> table
     *
     * @par Lua example
     * rpy = quaternionToRpy({0.834722,0.0780426, 0.451893, 0.304864})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.quaternionToRpy","params":[[0.834722,
     * 0.0780426, 0.451893, 0.304864]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.6110000520523781,0.7849996877683915,0.960000543982093]}
     * \endenglish
     */
    std::vector<double> quaternionToRpy(const std::vector<double> &quat);

    /**
     * @ingroup Math
     * \chinese
     * 四点法标定TCP偏移
     *
     * 找一个尖点，将机械臂工具末端点绕着尖点示教四个位置，姿态差别要大。
     * 设置完毕后即可计算出来结果。
     *
     * @param poses 四个点的位姿集合
     * @return TCP标定结果和标定结果是否有效
     *
     * @par Python函数原型
     * tcpOffsetIdentify(self: pyaubo_sdk.Math, arg0: List[List[float]]) ->
     * Tuple[List[float], int]
     *
     * @par Lua函数原型
     * tcpOffsetIdentify(poses: table) -> table
     *
     * @par Lua示例
     * p1 = {0.48659,0.10456,0.24824,-3.135,0.004,1.569} \n
     * p2 = {0.38610,0.09096,0.22432,2.552,-0.437,1.008} \n
     * p3 = {0.38610,0.05349,0.16791,-3.021,-0.981,0.517} \n
     * p4 = {0.49675,0.06417,0.21408,-2.438,0.458,0.651} \n
     * p = {p1,p2,p3,p4} \n
     * tcp_result = tcpOffsetIdentify(p)
     *
     * \endchinese
     *
     * \english
     * Four point method calibration for TCP offset
     *
     * About a sharp point, move the robot's tcp in four different poses. Difference between each pose should be drastic.
     * Result can be obtained based on these four poses
     *
     * @param poses combination of four different poses
     * @return TCP calibration result and whether successfull
     *
     * @par Python interface prototype
     * tcpOffsetIdentify(self: pyaubo_sdk.Math, arg0: List[List[float]]) ->
     * Tuple[List[float], int]
     *
     * @par Lua interface prototype
     * tcpOffsetIdentify(poses: table) -> table
     *
     * @par Lua example
     * p1 = {0.48659,0.10456,0.24824,-3.135,0.004,1.569} \n
     * p2 = {0.38610,0.09096,0.22432,2.552,-0.437,1.008} \n
     * p3 = {0.38610,0.05349,0.16791,-3.021,-0.981,0.517} \n
     * p4 = {0.49675,0.06417,0.21408,-2.438,0.458,0.651} \n
     * p = {p1,p2,p3,p4} \n
     * tcp_result = tcpOffsetIdentify(p)
     *
     * \endenglish
     */
    ResultWithErrno tcpOffsetIdentify(
        const std::vector<std::vector<double>> &poses);

    /**
     * @ingroup Math
     * \chinese
     * 三点法标定坐标系
     *
     * @param poses 三个点的位姿集合
     * @param type 类型:\n
     *      0 - oxy 原点 x轴正方向 xy平面（y轴正方向）\n
     *      1 - oxz 原点 x轴正方向 xz平面（z轴正方向）\n
     *      2 - oyz 原点 y轴正方向 yz平面（z轴正方向）\n
     *      3 - oyx 原点 y轴正方向 yx平面（x轴正方向）\n
     *      4 - ozx 原点 z轴正方向 zx平面（x轴正方向）\n
     *      5 - ozy 原点 z轴正方向 zy平面（y轴正方向）\n
     * @return 坐标系标定结果和标定结果是否有效
     *
     * @par Lua函数原型
     * calibrateCoordinate(poses: table, type: int) -> table, number
     *
     * @par Lua示例
     * p1 = {0.55462,0.06219,0.37175,-3.142,0.0,1.580} \n
     * p2 = {0.63746,0.11805,0.37175,-3.142,0.0,1.580} \n
     * p3 = {0.40441,0.28489,0.37174,-3.142,0.0,1.580} \n
     * p = {p1,p2,p3} \n
     * coord_pose, cal_result = calibrateCoordinate(p,0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.calibrateCoordinate","params":[[[0.55462,0.06219,0.37175,-3.142,0.0,1.580],
     * [0.63746,0.11805,0.37175,-3.142,0.0,1.580],[0.40441,0.28489,0.37174,-3.142,0.0,1.580]],0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[0.55462,0.06219,0.37175,-3.722688983883945e-05,-1.6940658945086007e-21,0.5932768162455785],0]}
     * \endchinese
     *
     * \english
     * Calibrate coordinate system with 3 points
     *
     * @param poses set of 3 poses
     * @param type type:\n
     *      0 - oxy origin, +x axis, xy plane (+y direction) \n
     *      1 - oxz origin, +x axis, xz plane (+z direction) \n
     *      2 - oyz origin, +y axis, yz plane (+z direction) \n
     *      3 - oyx origin, +y axis, yx plane (+x direction) \n
     *      4 - ozx origin, +z axis, zx plane (+x direction) \n
     *      5 - ozy origin, +z axis, zy plane (+y direction) \n
     * @return Coordinate system calibration result and whether the calibration result is valid
     *
     * @par Lua function prototype
     * calibrateCoordinate(poses: table, type: int) -> table, number
     *
     * @par Lua example
     * p1 = {0.55462,0.06219,0.37175,-3.142,0.0,1.580} \n
     * p2 = {0.63746,0.11805,0.37175,-3.142,0.0,1.580} \n
     * p3 = {0.40441,0.28489,0.37174,-3.142,0.0,1.580} \n
     * p = {p1,p2,p3} \n
     * coord_pose, cal_result = calibrateCoordinate(p,0)
     *
     * @par JSON-RPC request example    
     * {"jsonrpc":"2.0","method":"Math.calibrateCoordinate","params":[[[0.55462,0.06219,0.37175,-3.142,0.0,1.580],
     * [0.63746,0.11805,0.37175,-3.142,0.0,1.580],[0.40441,0.28489,0.37174,-3.142,0.0,1.580]],0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[0.55462,0.06219,0.37175,-3.722688983883945e-05,-1.6940658945086007e-21,0.5932768162455785],0]}
     * \endenglish
     */
    ResultWithErrno calibrateCoordinate(
        const std::vector<std::vector<double>> &poses, int type);

    /**
     * @ingroup Math
     * \chinese 
     * 根据圆弧的三个点,计算出拟合成的圆的另一半圆弧的中间点位置
     *
     *  @param p1 圆弧的起始点
     *  @param p2 圆弧的中间点
     *  @param p3 圆弧的结束点
     *  @param mode 当mode等于1的时候，表示需要对姿态进行圆弧规划；
     *  当mode等于0的时候，表示不需要对姿态进行圆弧规划
     *  
     *  @return 拟合成的圆的另一半圆弧的中间点位置和计算结果是否有效
     *
     * @par Lua函数原型
     * calculateCircleFourthPoint(p1: table, p2: table, p3: table, mode: int)
     *
     * @par Lua示例
     * center_pose, cal_result = calculateCircleFourthPoint({0.5488696249770836,-0.1214996547187204,0.2631931199112321,-3.14159198038469,-3.673205103150083e-06,1.570796326792424},
     * {0.5488696249770835,-0.1214996547187207,0.3599720701808493,-3.14159198038469,-3.6732051029273e-06,1.570796326792423},
     * {0.5488696249770836,-0.0389996547187214,0.3599720701808496,-3.141591980384691,-3.673205102557476e-06,1.570796326792422},1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Math.calculateCircleFourthPoint","params":[[0.5488696249770836,-0.1214996547187204,0.2631931199112321,-3.14159198038469,-3.673205103150083e-06,1.570796326792424],
     * [0.5488696249770835,-0.1214996547187207,0.3599720701808493,-3.14159198038469,-3.6732051029273e-06,1.570796326792423],
     * [0.5488696249770836,-0.0389996547187214,0.3599720701808496,-3.141591980384691,-3.673205102557476e-06,
     * 1.570796326792422],1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[[0.5488696249770837,-0.031860179583911546,0.27033259504604207,-3.1415919803846903,-3.67320510285378e-06,1.570796326792423],1]}
     *
     * \endchinese
     *
     * \english
     * Based on three points on an arc, calculate the position of the midpoint of the other half of the fitted circle's arc
     *
     * @param p1 start point of the arc
     * @param p2 middle point of the arc
     * @param p3 end point of the arc
     * @param mode when mode = 1, need to plan for orientation around arc;
     * when mode = 0, do not need to plan for orientation around arc.
     * @return position of the midpoint of the other half of the fitted circle's arc and whether the result is valid.
     *
     *
     * @par Lua函数原型
     * calculateCircleFourthPoint(p1: table, p2: table, p3: table, mode: int)
     *
     * @par Lua示例
     * center_pose, cal_result = calculateCircleFourthPoint({0.5488696249770836,-0.1214996547187204,0.2631931199112321,-3.14159198038469,-3.673205103150083e-06,1.570796326792424},
     * {0.5488696249770835,-0.1214996547187207,0.3599720701808493,-3.14159198038469,-3.6732051029273e-06,1.570796326792423},
     * {0.5488696249770836,-0.0389996547187214,0.3599720701808496,-3.141591980384691,-3.673205102557476e-06,1.570796326792422},1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Math.calculateCircleFourthPoint","params":[[0.5488696249770836,-0.1214996547187204,0.2631931199112321,-3.14159198038469,-3.673205103150083e-06,1.570796326792424],
     * [0.5488696249770835,-0.1214996547187207,0.3599720701808493,-3.14159198038469,-3.6732051029273e-06,1.570796326792423],
     * [0.5488696249770836,-0.0389996547187214,0.3599720701808496,-3.141591980384691,-3.673205102557476e-06,
     * 1.570796326792422],1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[[0.5488696249770837,-0.031860179583911546,0.27033259504604207,-3.1415919803846903,-3.67320510285378e-06,1.570796326792423],1]}
     *
     * \endenglish
     */
    ResultWithErrno calculateCircleFourthPoint(const std::vector<double> &p1,
                                               const std::vector<double> &p2,
                                               const std::vector<double> &p3,
                                               int mode);
    /**
     * @ingroup Math
     * \chinese
     * @brief forceTrans:
     * 变换力和力矩的参考坐标系 force_in_b = pose_a_in_b * force_in_a
     * @param pose_a_in_b: a 坐标系在 b 坐标系的位姿
     * @param force_in_a: 力和力矩在 a 坐标系的描述
     * @return force_in_b，力和力矩在 b 坐标系的描述
     * \endchinese
     *
     * \english
     * @brief forceTrans:
     * Transform the reference frame of force and torque: force_in_b = pose_a_in_b * force_in_a
     * @param pose_a_in_b: pose of frame a in frame b
     * @param force_in_a: force and torque described in frame a
     * @return Force_in_b, force and torque described in frame b
     * \endenglish
     */
    std::vector<double> forceTrans(const std::vector<double> &pose_a_in_b,
                                   const std::vector<double> &force_in_a);

    /**
     * @ingroup Math
     * \chinese
     * @brief 通过距离计算工具坐标系下的位姿增量
     * @param distances: N 个距离, N >=3
     * @param position: 距离参考轨迹的保持高度
     * @param radius: 传感器中心距离末端tcp的等效半径
     * @param track_scale: 跟踪比例, 设置范围(0, 1], 1表示跟踪更快
     * @return 基于工具坐标系的位姿增量
     * \endchinese
     *
     * \english
     * @brief Calculate pose increment in tool coordinate system based on sensor data
     * @param distances: N distances, N >= 3
     * @param position: reference height to maintain from the trajectory
     * @param radius: effective radius from sensor center to tool TCP
     * @param track_scale: tracking ratio, range (0, 1], 1 means faster tracking
     * @return Pose increment in tool coordinate system
     * \endenglish
     */
    std::vector<double> getDeltaPoseBySensorDistance(
        const std::vector<double> &distances, double position, double radius,
        double track_scale);

    /**
     * @ingroup Math
     * \chinese
     * @brief changeFTFrame: 变换力和力矩的参考坐标系
     * @param pose_a_in_b: a 坐标系在 b 坐标系的位姿
     * @param ft_in_a: 作用在 a 点的力和力矩在 a 坐标系的描述
     * @return ft_in_b，作用在 b 点的力和力矩在 b 坐标系的描述
     * \endchinese
     *
     * \english
     * @brief changeFTFrame: Transform the reference frame of force and torque
     * @param pose_a_in_b: pose of frame a in frame b
     * @param ft_in_a: force and torque applied at point a, described in frame a
     * @return ft_in_b, force and torque applied at point b, described in frame b
     * \endenglish
     */
    std::vector<double> deltaPoseTrans(const std::vector<double> &pose_a_in_b,
                                       const std::vector<double> &ft_in_a);

    /**
     * @ingroup Math
     * \chinese
     * @brief addDeltaPose: 计算以给定速度变换单位时间后的位姿
     * @param pose_a_in_b: 当前时刻 a 相对于 b 的位姿
     * @param v_in_b: 当前时刻 a 坐标系的速度在 b 的描述
     * @return pose_in_b, 单位时间后的位姿在 b 的描述
     * \endchinese
     *
     * \english
     * @brief addDeltaPose: Calculate the pose after unit time given a velocity
     * @param pose_a_in_b: current pose of a relative to b
     * @param v_in_b: velocity of frame a described in frame b at current time
     * @return pose_in_b, pose after unit time described in frame b
     * \endenglish
     */
    std::vector<double> deltaPoseAdd(const std::vector<double> &pose_a_in_b,
                                     const std::vector<double> &v_in_b);

    /**
     * @ingroup Math
     * \chinese
     * @brief changePoseWithXYRef: 修改 pose_tar 的ｘｙ轴方向,尽量与 pose_ref 一致，
     * @param pose_tar: 需要修改的目标位姿
     * @param pose_ref: 参考位姿
     * @return 修改后的位姿，采用pose_tar的 xyz 坐标和 z 轴方向
     * \endchinese
     *
     * \english
     * @brief changePoseWithXYRef: Modify the XY axis direction of pose_tar to be as consistent as possible with pose_ref
     * @param pose_tar: target pose to be modified
     * @param pose_ref: reference pose
     * @return Modified pose, using the xyz coordinates and z axis direction of pose_tar
     * \endenglish
     */
    std::vector<double> changePoseWithXYRef(
        const std::vector<double> &pose_tar,
        const std::vector<double> &pose_ref);

    /**
     * @ingroup Math
     * \chinese
     * @brief homMatrixToPose: 由齐次变换矩阵得到位姿
     * @param homMatrix: 4*4 齐次变换矩阵, 输入元素采用横向排列
     * @return 对应的位姿
     * \endchinese
     *
     * \english
     * @brief homMatrixToPose: Get pose from homogeneous transformation matrix
     * @param homMatrix: 4x4 homogeneous transformation matrix, input elements are arranged row-wise
     * @return corresponding pose
     * \endenglish
     */
    std::vector<double> homMatrixToPose(const std::vector<double> &homMatrix);

    /**
     * @ingroup Math
     * \chinese
     * @brief poseToHomMatrix: 位姿变换得到齐次变换矩阵
     * @param pose: 输入的位姿
     * @return 输出的齐次变换矩阵,元素横向排列
     * \endchinese
     *
     * \english
     * @brief poseToHomMatrix: Get homogeneous transformation matrix from pose
     * @param pose: input pose
     * @return output homogeneous transformation matrix, elements arranged row-wise
     * \endenglish
     */
    std::vector<double> poseToHomMatrix(const std::vector<double> &pose);

protected:
    void *d_;
};
using MathPtr = std::shared_ptr<Math>;

} // namespace common_interface
} // namespace arcs
#endif
