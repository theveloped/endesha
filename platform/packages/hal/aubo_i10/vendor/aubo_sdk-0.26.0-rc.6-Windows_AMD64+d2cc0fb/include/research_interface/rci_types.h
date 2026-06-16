#include <array>

namespace arcs {
namespace research_interface {

#pragma pack(push, 1)

/// 机器人状态
struct RobotState
{
    uint64_t message_id;
    int dof;

    /// 机器人状态
    int robot_mode;

    /// 安全状态
    int safety_mode;

    /// 错误代码(针对这个科研接口)
    int error_code;

    uint32_t tool_io;
    uint32_t standard_di;
    uint32_t standard_do;
    uint32_t config_di;
    uint32_t config_do;
    std::array<double, 4> analog_in;
    std::array<double, 4> analog_out;
    std::array<double, 4> tool_analog_in;

    /// 关节的实际状态
    std::array<double, 7> q, qd, qdd, current, friction, voltage;

    /// 关节的目标状态
    std::array<double, 7> target_q, target_qd, target_qdd, target_current;

    std::array<double, 6> pose, target_pose;
    std::array<double, 6> tcp_offset;
    std::array<double, 7> temperature;

    /// 基于法兰坐标系的力
    std::array<double, 6> tcp_force;

    /// 负载参数
    struct
    {
        double mass;
        std::array<double, 3> cog;
    } payload;
};

/// 机器人指令
struct RobotCommand
{
    uint64_t message_id;

    /// 目标模式
    int target_mode;

    /// 指令关节角度
    std::array<double, 7> cmd_q, cmd_qd, cmd_current;

    /// 指令位姿
    std::array<double, 6> cmd_pose;

    bool finished;
};

#pragma pack(pop)
} // namespace research_interface
} // namespace arcs
