// 力控相关的工艺封装接口
#ifndef AUBO_SDK_SKILL_INTERFACE_H
#define AUBO_SDK_SKILL_INTERFACE_H

#include <chrono>
#include <atomic>
#include <shared_mutex>
#include <condition_variable>
#include <aubo/aubo_api.h>

using namespace arcs::common_interface;

namespace arcs {
namespace aubo_sdk {

class RtdeClient;
class RpcClient;
using RtdeClientPtr = std::shared_ptr<RtdeClient>;
using RpcClientPtr = std::shared_ptr<RpcClient>;

class GuideTrajMove;
using GuideTrajMovePtr = std::shared_ptr<GuideTrajMove>;

class ARCS_ABI ForceControl
{
public:
    enum ForceStage
    {
        TOUCH = 1,    // 接近
        SEARCH = 2,   // 搜孔
        INSERT = 3,   // 插孔
        CONSTANT = 4, // 恒力

    }; // enum ForceStage

    enum StateCode
    {
        // 失败状态码
        TimeOut = -100,         // 超时
        Search_MaxForce = -4,   // 搜孔达到最大力
        Insert_MaxForce = -3,   // 插入达到最大力
        Constant_NotTouch = -2, // 恒力过程中未接触
        Touch_Distance = -1,    // 超出探寻距离

        Running = 0, // 力控执行中

        // 成功状态码
        Touch_Succeed = 1,    // 接触成功
        Insert_Succeed = 2,   // 插孔成功
        Search_Succeed = 3,   // 搜孔成功
        Constant_Succeed = 4, // 接触成功

    }; // StateCode

    // 轨迹类型
    enum GuideTrajType
    {
        NONE = 0,   // 无参考轨迹
        LINE1 = 1,  // 直线 speedLine
        LINE2 = 2,  // 直线 moveLine
        SPIRAL = 3, // 螺旋线
        WEAVE = 4,  // 摆线
    };

    // 螺旋线平面
    enum class SpiralPlane
    {
        xy = 0,
        yz = 1,
        zx = 2
    };

    // 螺旋线轨迹参数
    struct SpiralTrajParams
    {
        double step = 0.0;     // 圈数
        double direction = -1; // 旋转方向 -1顺时针旋转，1逆时针旋转
        SpiralPlane plane = SpiralPlane::xy; // 参考平面选择
        double spiral = 0.0;                 // 螺旋线外扩
        double helix = 0.0;                  // 螺旋上升 m
        double radius = 0.0;                 // 第一圈半径 m
    };

    // 摆线方向
    enum class WeaveSelect
    {
        x = 1,
        y = 2,
        z = 3,
        rx = 4,
        ry = 5,
        rz = 6
    };

    // 摆线轨迹参数
    struct WeaveTrajParams
    {
        double step = 0.0;                      // 周期
        double amplitude = 0.0;                 // 幅度
        WeaveSelect direction = WeaveSelect::x; // 方向
        double hold_distance = 0.0;             // 保持距离 m
        double angle = 0.0;                     // 角度
        double type;                            // 类型
    };

    // 插孔方向
    enum class InsertSelect
    {
        x = 1,
        y = 2,
        z = 3,
    };

    // 插孔参数
    struct InsertParams
    {
        InsertSelect insert_select = InsertSelect::z; // 插入方向,可选x\y\z
        double hole_diameter = 0.0;                   // 轴孔直径  m
        double insert_max_speed = 0.01;               // 插入速度限制 m/s
        double insert_time = 1000;                    // 插入时间限制 ms
        GuideTrajType guide_traj_type = NONE;         // 主动轨迹类型
        std::vector<double> insert_max_force = {
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        };                              // 最大力限制
        double insert_max_depth = 0.01; // 插入距离限制 m
        double insert_guide_force = 10; // 插入引导力
        // 力控调节参数
        std::vector<double> insert_damp_scale = {
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5
        };
        std::vector<double> insert_stiff_scale = {
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5
        };

        SpiralTrajParams spiral_param; // 螺旋轨迹参数
        WeaveTrajParams weave_param;   // 摆动轨迹参数
    };

    // 搜孔平面
    enum class SearchPlane
    {
        yz = 1,
        xz = 2,
        xy = 3
    };

    // 搜孔参数
    struct SearchParams
    {
        SearchPlane search_plane = SearchPlane::xy; // 搜孔平面
        double hole_diameter = 0.0;                 // 轴孔直径 m
        double search_range = 0.1;                  // 搜孔范围
        double search_time = 1000;                  // 搜孔时间限制 ms
        GuideTrajType guide_traj_type = NONE; // 搜孔过程主动轨迹类型
        double search_max_force = 10;         // 最大力限制
        double search_guide_force = 1;        // 搜孔引导力
        // 力控调节参数
        std::vector<double> search_damp_scale = {
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5
        };
        std::vector<double> search_stiff_scale = {
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5
        };

        SpiralTrajParams spiral_param;
        WeaveTrajParams weave_param;
    };

    struct ConstantParams
    {
        TaskFrameType frame_type = MOTION_FORCE;
        std::vector<double> feature = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
        std::vector<bool> compliance = { true, true, true, true, true, true };
        std::vector<double> wrench = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };

        // 力控调节参数
        std::vector<double> env_stiff = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
        std::vector<double> damp_scale = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };
        std::vector<double> stiff_scale = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };

        std::vector<double> contact_threshold = {
            1.0, 1.0, 1.0, 0.2, 0.2, 0.2
        };                           // 接触判断阈值
        double constant_time = 5000; // 默认5s
    };

    struct TouchParams
    {
        TaskFrameType frame_type = TOOL_FORCE;
        std::vector<double> feature = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
        std::vector<bool> compliance = { true, true, true, true, true, true };
        std::vector<double> wrench = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
        std::vector<double> env_stiff = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
        //        std::vector<double> damp_scale = { 0.5, 0.5, 0.5, 0.5, 0.5,
        //        0.5 };
        std::vector<double> stiff_scale = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };
        std::vector<double> speed = { 0.1, 0.1, 0.1, 0.1, 0.1, 0.1 };
        double distance = 0.0;
        double touch_time = 1000; // 默认5s
    };

    ForceControl(const RpcClientPtr rpc, const RtdeClientPtr rtde);
    ~ForceControl();

    /**
     * @brief 获取实时力控参考系下的力描述
     *
     * @return 未开启力控时返回全0
     */
    std::vector<double> getTaskForce(const TaskFrameType &type,
                                     const std::vector<double> &feature);

    // 接近
    int fcTouch(const TouchParams &param);

    // 恒力
    int fcConstant(const ConstantParams &param);

    // 插入
    int fcInsert(const InsertParams &param);

    // 搜孔
    int fcSearch(const SearchParams &param);

    // 等待力控结束
    int fcWaitCondition();

    int fcExit();

    // 注册状态回调函数
    void registerStateCallBack(std::function<void(int state)> func);

private:
    // 注册实时状态订阅
    void subscribeRealtimeState();

    // 力控过程监控线程
    void monitor();

    // 超时监控
    void timeoutMonitor();

    // 距离监控
    void distanceMonitor();

    // 单方向距离监控
    void signalDistanceMonitor();

    // 力监控
    void forceMonitor();

    // 接触监控
    void contactMonitor();

private:
    RpcClientPtr rpc_;
    RtdeClientPtr rtde_;

    std::atomic_bool is_exit_;
    std::atomic_bool is_stop_;
    std::mutex monitor_thread_mutex_;
    std::condition_variable monitor_cond_;
    std::thread *monitor_thread_ptr_;

    // 用于恒力和接近之间的切换
    std::atomic_bool last_is_contact_;

    // 记录当前参数
    std::shared_mutex mutex_;
    TaskFrameType frame_type_;
    std::vector<double> feature_;
    ForceStage cur_process_type_;
    std::vector<bool> compliance_;
    std::vector<double> env_stiff_;
    std::vector<double> damp_scale_;
    std::vector<double> stiff_scale_;
    std::vector<double> wrench_;
    std::vector<double> start_tcp_pose_;               // 开始力控位姿
    double distance_;                                  // 力控执行距离
    double direction_;                                 // 搜孔/插孔方向
    std::chrono::steady_clock::time_point start_time_; // 开启力控时间点
    double interval_;                                  // 超时间隔

    // 参考轨迹运行
    GuideTrajMovePtr guide_traj_move_;

    // 状态回调函数
    std::atomic<StateCode> state_code_ = Running;
    std::function<void(int state)> func_;

    // RTDE相关
    std::shared_mutex rtde_mutex_;
    std::vector<double> actual_tcp_pose_;
    std::vector<double> actual_tcp_speed_;
    std::vector<double> actual_tcp_force_;
    std::vector<double> actual_tcp_force_sensor_;
}; // namespace aubo_sdk

class GuideTrajMove
{
public:
    GuideTrajMove(const RpcClientPtr rpc);
    ~GuideTrajMove();

    void speedLine(const std::vector<double> &speed, const double &time);
    void moveLine(const std::vector<double> &target_pose, const double &speed);
    void moveSpiral(const ForceControl::SpiralTrajParams &spiral_param);
    void moveWeave(const ForceControl::WeaveTrajParams &weave_param,
                   const int &move_direction);

    void stop();

private:
    int waitArrival();

    RpcClientPtr rpc_;

    std::atomic_bool is_exit_;
    std::atomic_bool is_stop_;
    std::mutex thread_mutex_;
    std::condition_variable cond_;
    std::thread thread_;

    ForceControl::GuideTrajType traj_type_ = ForceControl::NONE;
};

} // namespace aubo_sdk
} // namespace arcs

#endif // AUBO_SDK_SKILL_INTERFACE_H
