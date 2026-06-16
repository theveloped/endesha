#ifndef AUBO_SCOPE_ROBOT_PROXY_H
#define AUBO_SCOPE_ROBOT_PROXY_H

#include <memory>
#include <vector>
#include <string>
#include <shared_mutex>

#include <QObject>
#include <QMutex>
#include <QMap>

#include <aubo/aubo_api.h>

#include <robot_proxy/realtime_robot_state.h>

namespace arcs {
namespace aubo_sdk {
class RtdeClient;
class ScriptClient;
class RpcClient;
using RtdeClientPtr = std::shared_ptr<RtdeClient>;
using ScriptClientPtr = std::shared_ptr<ScriptClient>;
using RpcClientPtr = std::shared_ptr<RpcClient>;

using arcs::common_interface::ForceControlPtr;
using arcs::common_interface::IoControlPtr;
using arcs::common_interface::MotionControlPtr;
using arcs::common_interface::RegisterControlPtr;
using arcs::common_interface::RobotAlgorithmPtr;
using arcs::common_interface::RobotConfigPtr;
using arcs::common_interface::RobotInterfacePtr;
using arcs::common_interface::RobotManagePtr;
using arcs::common_interface::RobotStatePtr;
using arcs::common_interface::RuntimeMachinePtr;
using arcs::common_interface::SyncMovePtr;
using arcs::common_interface::SystemInfoPtr;
using arcs::common_interface::TracePtr;

using RobotInterface = common_interface::RobotInterface;

/**
 * 单个机器人代理接口类
 */
class ARCS_ABI RobotProxy : public QObject
{
    Q_OBJECT

public:
    RobotProxy(QObject *parent = NULL);
    ~RobotProxy();

    /// 获取当前机器人的名称
    QString getRobotName() const;

    /// 获取当前机器人在所有机器人中的索引
    int getRobotIndex() const;

    /// 获取所有机器人的名字
    std::vector<std::string> getRobotNames();

    /// 连接到当前机器人
    int connect(const QString &ip, int port);

    /// 连接到当前机器人
    int nonblock_connect(const QString &ip, int port,
                         std::function<void(bool)> cb);
    int nonblock_connect2(const QString &ip, int port,
                          std::function<void(int)> cb);

    /// 登录到当前机器人
    int login(const QString &usrname, const QString &passwd);

    /// 断开与机器人的连接，如果不指定名称，则断开当前选中的机器人
    int disconnectFromServer();

    /// 机器人是否已经连接，如果不指定名称，则断开当前选中的机器人
    bool hasConnected();

    /// 机器人是否已经登录，如果不指定名称，则断开当前选中的机器人
    bool hasLogined();

    /// 发送脚本程序到当前机器人
    int sendScript(const std::string &script);

    /// 获取当前机器人的脚本程序
    std::string getScript() const;

    /// 使用 RealtimeRobotState 中的 getRealDHParam getTheoryDHParam 替代
    ARCS_DEPRECATED std::unordered_map<std::string, std::vector<double>> getDH(
        bool real = true);

    SystemInfoPtr getSystemInfo();
    RuntimeMachinePtr getRuntimeMachine();
    RegisterControlPtr getRegisterControl();
    GripperInterfacePtr getGripperInterface();

    /// 获取RobotConfig接口
    RobotConfigPtr getRobotConfig();

    /// 获取运动规划接口
    MotionControlPtr getMotionControl();

    /// 获取力控接口
    ForceControlPtr getForceControl();

    /// 获取IO控制的接口
    IoControlPtr getIoControl();

    /// 获取同步运动接口
    SyncMovePtr getSyncMove();

    /// 获取机器人实用算法接口
    RobotAlgorithmPtr getRobotAlgorithm();

    /// 获取机器人管理接口(上电、启动、停止等)
    RobotManagePtr getRobotManage();

    /// 获取机器人状态接口
    RobotStatePtr getRobotState();

    RealtimeRobotStatePtr getRealTimeState();

    /// 获取告警信息接口
    TracePtr getTrace();

    /// 根据机器人名字获取机器人接口
    RobotInterfacePtr getRobotInterface(const std::string &name);

    /// 切换机器人
    int selectRobot(int index);

    aubo_sdk::RpcClientPtr getRpcClient();
    aubo_sdk::RtdeClientPtr getRtdeClient();
    aubo_sdk::ScriptClientPtr getScriptClient();

    /// 通过错误码获取消息文本
    QString getErrorCodeMsg(int code);

    /// 获取 ICM 连接状态
    bool icmIsConnected();

    /// 获取 Profinet 地址表数据
    std::vector<std::vector<uint8_t>> getPnAddressData();

    // EIP
    /// 获取 EIP 连接状态
    int getEipConnected();
    /// 获取 EtherNet/IP 地址表数据
    std::vector<std::vector<uint8_t>> getEipAddressData();

signals:
    // FIXME: 断开连接和登出的信号需要从 RobotProxy 类主动发出

    /// 建立连接的信号
    void connected(const QString &ip, int port);

    /// 断开连接的信号
    void disconnected();

    /// 登录或者登出
    void logined(bool has_login);

    /// 弹窗信号
    void popup(int robot_index, int level, const QString &title,
               const QString &msg, int mode);

    /// 解除弹窗信号
    void popupDismiss(const QString &src);

    /// 从控制器层上传的系统关机信号
    void systemHalt(const QString &src);

    /// 已弃用，推荐使用下面的重载函数
    ARCS_DEPRECATED void scriptError(const QString &);
    /// aubo_control 报错
    void scriptError(int lineno, const QString &error);
    /// 脚本运行报错
    void scriptError2(const QString &, const QString &);

    /// 脚本运行时里面的变量发生变化
    void variableUpdate(const QString &, const QString &);

    /// 运行时状态发生变化
    void runtimeStateChanged(arcs::common_interface::RuntimeState state);

    /// 拖动示教器使能状态切换
    void freedriveEnabled(int robot_index, bool enabled);

    /// 接收到机器人控制端消息
    void robotMessageRecieved(int robot_index, QString src, int level, int code,
                              const QString &msg);
    void robotMessageRecieved(int robot_index, const QString &src, int level,
                              const RobotMsg &msg);

    /// 操作模式切换
    void operationalModeChanged(
        int robot_index, arcs::common_interface::OperationalModeType mode);

    /// 联动模式切换
    void linkModeChanged(int robot_index, bool enable);

    /// 安全模式切换
    void safetyModeChanged(int robot_index,
                           arcs::common_interface::SafetyModeType mode);

    /// 机器人状态切换
    void robotModeChanged(int robot_index,
                          arcs::common_interface::RobotModeType mode);

    /// 机器人型号切换
    void robotTypeChanged(const QString &type, const QString &subtype);

    /// 缓速切换
    void slowDownChanged(int robot_index, int level);

    /// 运行时上下文更新
    void runtimeContextUpdated(int tid, int lineno, int index,
                               const QString &comment);
    void interpContextUpdated(int tid, int lineno, int index,
                              const QString &comment);
    void taskDeleted(int tid);

    /// ICM 插件状态变化
    void icmStatusChanged(bool status);

    /// PNIO 从站数据变化
    void pnioDeviceChanged(const QString &name);
    void pnioNetworkChanged(const QString &ip, const QString &subnet_mask,
                            const QString &gateway);

    // EIP 连接状态变化
    void sigEipConnectionStatusChanged(int);

    /// 示教器启用状态变化
    void teachPendantEnabledChanged(bool status);

    /// Modbus master
    void modbusSignalCreated(const QString &name);
    void modbusSignalRemoved(const QString &name);

    void jointMovedDuringPoweroff(int robot_index);
    void robotCollisionOccurred(int robot_index, const QString &msg);

    void robotToolSensorChanged(int robot_index, const QString &sensor_id);
    void robotToolSensorRemoved(int robot_index);
    void robotToolSensorStatusChanged(int robot_index, bool status);
    void programLoaded(int robot_index, const QString &program);

private:
    RobotInterfacePtr currentRobotRpcInterface();
    void robotMessageCallback(InputParser &parser);
    void sendDisconnectedSignal();

    // Profinet 地址表数据
    void initPNCacheData();
    void pnValueChanged(const std::vector<std::string> &data);

    // EtherNet/IP 地址表数据
    void initEIPCacheData();
    void eipValueChanged(const std::vector<std::string> &data);

private:
    QString name_;
    int robot_index_{ -1 };
    std::vector<std::string> robot_names_;

    std::string ip_;
    int port_;

    aubo_sdk::RpcClientPtr rpc_client_{ nullptr };
    aubo_sdk::RtdeClientPtr rtde_client_{ nullptr };
    aubo_sdk::ScriptClientPtr script_client_{ nullptr };

    RealtimeRobotStatePtr rt_state_{ nullptr };

    bool initiallized_{ false };

    QMap<int, QString> script_;

    bool icm_connected_{ false };
    bool pn_connected_{ false };
    std::atomic_int eip_connected_{ 0 };

    // Profinet 地址表数据
    std::shared_mutex mtx_pn_address_;
    std::vector<std::vector<uint8_t>> cache_pn_address_;

    // EtherNet/IP 地址表数据
    std::shared_mutex mtx_eip_address_;
    std::vector<std::vector<uint8_t>> cache_eip_address_;
};
using RobotProxyPtr = std::shared_ptr<RobotProxy>;

} // namespace aubo_sdk
} // namespace arcs
Q_DECLARE_METATYPE(arcs::aubo_sdk::RobotProxyPtr)
#endif
