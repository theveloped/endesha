#ifndef ARCS_RESEARCH_INTERFACE_ROBOT_H
#define ARCS_RESEARCH_INTERFACE_ROBOT_H

#include <functional>
#include <atomic>
#include <aubo/global_config.h>
#include <research_interface/rci_types.h>
#include <stdexcept>
#include "aubo_sdk/rpc.h"

namespace arcs {
namespace research_interface {

struct JointPositions
{
    JointPositions() {}
    JointPositions(const std::array<double, 7> &joint_positions)
        : q(joint_positions)
    {
    }
    JointPositions(std::initializer_list<double> joint_positions)
    {
        if (joint_positions.size() != q.size()) {
            throw std::invalid_argument(
                "Invalid number of elements in joint_positions.");
        }
        std::copy(joint_positions.begin(), joint_positions.end(), q.begin());
    }

    std::array<double, 7> q{};
    bool finished{ false };
};

class ARCS_ABI Robot
{
public:
    Robot(const std::string &ip, int port = 30030);
    ~Robot();

    // 启动机器人
    int startup();

    int setControlPeriod(int period = 5000);

    int movej(const JointPositions &jnt_pos);

    // 位置控制
    void control(
        std::function<JointPositions(const RobotState &, double duration)>
            control_callback,
        bool limit_rate = false, double cutoff_frequency = 100,
        bool loop = false);

    // 实时读取机器人的状态
    void read(std::function<bool(const RobotState &)> read_callback);

protected:
    void *d_{ nullptr };
    bool init_{ false };
};

} // namespace research_interface
} // namespace arcs

#endif
