/** @file gripper_interface.h
 *  @brief 通用夹爪接口
 */
#ifndef AUBO_SDK_GRIPPER_INTERFACE_H
#define AUBO_SDK_GRIPPER_INTERFACE_H

#include <aubo/sync_move.h>
#include <aubo/trace.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup GripperInterface GripperInterface (夹爪)
 * \~chinese 通用夹爪API接口
 */
class ARCS_ABI_EXPORT GripperInterface
{
public:
    GripperInterface();
    virtual ~GripperInterface();

    /**
     * @ingroup GripperInterface
     * \chinese
     * 获取支持的所有夹爪
     *
     * @return
     * \endchinese
     */
    std::vector<std::string> gripperGetSupportedModels();

    /**
     * @ingroup GripperInterface
     * \chinese
     * 扫描该型号下的所有设备
     *
     * @param model 夹爪品牌型号
     * @param device_name 设备名
     * @return 成功返回设备列表和0，失败返回错误码
     * \endchinese
     */
    ResultWithErrno2 gripperScanDevices(const std::string &model,
                                        const std::string &device_name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 获取已添加的夹爪
     * @return
     */
    std::vector<std::string> gripperGetNames();

    /**
     * @ingroup GripperInterface
     * \chinese
     * 添加夹爪
     *
     * @param name 用户自定义名字，唯一
     * @param model 夹爪品牌及型号
     * @return 成功返回0，失败返回错误码
     * \endchinese
     */
    int gripperAdd(const std::string &name, const std::string &model);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 删除夹爪
     *
     * @param name 用户自定义名字
     * @return 成功返回0，失败返回错误码
     * \endchinese
     */
    int gripperDelete(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 修改夹爪名
     *
     * @param name
     * @param new_name 新名字
     * @return 成功返回0，失败返回错误码
     * \endchinese
     */
    int gripperRename(const std::string &name, const std::string &new_name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 夹爪连接
     *
     * @param name
     * @param device_name 设备名
     * @return 成功返回0，失败返回错误码
     * \endchinese
     */
    int gripperConnect(const std::string &name, const std::string &device_name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 夹爪断开连接
     *
     * @param name
     * @return 成功返回0，失败返回错误码
     * \endchinese
     */
    int gripperDisconnect(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 夹爪是否连接
     *
     * @param name
     * @return 已连接返回true，未连接返回false
     * \endchinese
     */
    bool gripperIsConnected(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 设置工作模式
     *
     * @param name
     * @param work_mode 工作模式
     * @return 成功返回0，失败返回错误码
     * \endchinese
     */
    int gripperSetWorkMode(const std::string &name, int work_mode);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 获取工作模式
     *
     * @param name
     * @return 返回工作模式
     * \endchinese
     */
    int gripperGetWorkMode(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 设置夹爪安装偏移
     *
     * @param name
     * @param isVisibled 是否显示
     * @param pose 末端（不包括手指）相对法兰的位姿
     * @return 成功返回true，失败返回false
     * \endchinese
     */
    int gripperSetMountPose(const std::string &name,
                            const std::vector<double> &pose,
                            bool enable_collision);

    /**
     * @brief 获取夹爪安装偏移
     * @param name
     * @return 返回夹爪安装偏移
     */
    std::vector<double> gripperGetMountPose(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 使能夹爪
     *
     * @param name
     * @return
     * \endchinese
     */
    int gripperEnable(const std::string &name, bool enable);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 夹爪是否使能
     *
     * @param name
     * @return
     * \endchinese
     */
    bool gripperIsEnabled(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 设置运动参数
     *
     * @param name
     * @param position 位置，单位：m/Pa
     * @param velocity_percent 速度，单位：%，范围：[0, 1]
     * @param force 夹持力，单位：N
     * @param angle 旋转角度，单位：rad
     * @param r_velocity_percent 旋转速度，单位：%，范围：[0, 1]
     * @param torque_percent 旋转扭矩，单位：%，范围：[0, 1]
     *
     * @return
     * \endchinese
     */
    int gripperSetPosition(const std::string &name, const double position);
    int gripperSetVelocity(const std::string &name,
                           const double velocity_percent);
    int gripperSetForce(const std::string &name, const double force);
    int gripperSetAngle(const std::string &name, const double angle);
    int gripperSetRVelocity(const std::string &name,
                            const double r_velocity_percent);
    int gripperSetTorque(const std::string &name, const double torque_percent);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 开始运动
     *
     * @param name
     * @return
     * \endchinese
     */
    int gripperMove(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 停止运动
     *
     * @param name
     * @return
     * \endchinese
     */
    int gripperStop(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 获取夹爪状态
     *
     * @param name
     * @return
     *
     * @note 位置，速度，夹持力，旋转角度，旋转速度，旋转扭矩的单位与Set接口一致
     *
     * \endchinese
     */
    std::string gripperGetHardwareVersion(const std::string &name);
    std::string gripperGetSoftwareVersion(const std::string &name);
    double gripperGetPosition(const std::string &name);
    double gripperGetVelocity(const std::string &name);
    double gripperGetForce(const std::string &name);
    double gripperGetAngle(const std::string &name);
    double gripperGetRVelocity(const std::string &name);
    double gripperGetTorque(const std::string &name);
    bool gripperGetObjectDetection(const std::string &name);
    bool gripperGetMotionState(const std::string &name);
    double gripperGetVoltage(const std::string &name);
    double gripperGetTemperature(const std::string &name);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 重置modbus从站ID
     *
     * @param name
     * @param slave_id 从站Id
     * @return
     * \endchinese
     */
    int gripperResetSlaveId(const std::string &name, const int slave_id);

    /**
     * @ingroup GripperInterface
     * \chinese
     * 获取夹爪状态
     * @param name
     * @return 状态
     * \endchinese
     */
    int gripperGetStatusCode(const std::string &name);

protected:
    void *d_;
};
using GripperInterfacePtr = std::shared_ptr<GripperInterface>;

} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_GRIPPER_INTERFACE_H
