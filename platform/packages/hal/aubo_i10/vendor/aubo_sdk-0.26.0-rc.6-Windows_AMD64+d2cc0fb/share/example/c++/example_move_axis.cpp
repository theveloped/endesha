#include "aubo_sdk/rpc.h"
#ifdef WIN32
#include <windows.h>
#endif

using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// 实现阻塞功能: 当机械臂运动到目标路点时，程序再往下执行
int waitArrival(RobotInterfacePtr impl)
{
    const int max_retry_count = 5;
    int cnt = 0;

    // 接口调用: 获取当前的运动指令 ID
    int exec_id = impl->getMotionControl()->getExecId();

    // 等待机械臂开始运动
    while (exec_id == -1) {
        if (cnt++ > max_retry_count) {
            return -1;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        exec_id = impl->getMotionControl()->getExecId();
    }

    // 等待机械臂动作完成
    while (impl->getMotionControl()->getExecId() != -1) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    return 0;
}

void exampleMoveAxis1(RpcClientPtr cli)
{
    // 关节角，单位: 弧度
    std::vector<double> joint_angle = {
        0.0 * (M_PI / 180),  -15.0 * (M_PI / 180), 100.0 * (M_PI / 180),
        25.0 * (M_PI / 180), 90.0 * (M_PI / 180),  0.0 * (M_PI / 180)
    };
    // 位姿
    std::vector<double> pose1 = { -0.155944, -0.727344, 0.439066,
                                  3.05165,   0.0324355, 1.80417 };
    std::vector<double> pose2 = { -0.581143, -0.357548, 0.439066,
                                  3.05165,   0.0324355, 1.80417 };
    std::vector<double> pose3 = { 0.503502, -0.420646, 0.439066,
                                  3.05165,  0.0324355, 1.80417 };

    // 接口调用: 获取机器人的名字
    auto robot_name = cli->getRobotNames().front();

    auto robot_interface = cli->getRobotInterface(robot_name);

    // 接口调用: 设置机械臂的速度比率
    robot_interface->getMotionControl()->setSpeedFraction(0.3);

    // 接口调用: 设置工具中心点（TCP相对于法兰盘中心的偏移）
    std::vector<double> tcp_offset(6, 0.0);
    robot_interface->getRobotConfig()->setTcpOffset(tcp_offset);

    // 接口调用: 关节运动到起始位置
    robot_interface->getMotionControl()->moveJoint(
        joint_angle, 80 * (M_PI / 180), 60 * (M_PI / 180), 0, 0);
    // 阻塞
    int ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "关节运动到起始位置成功！" << std::endl;
    } else {
        std::cout << "关节运动到起始位置失败！" << std::endl;
    }

    std::string axis_group_name = "test";
    auto axis = cli->getAxisInterface(cli->getAxisNames().front());
    auto syn_move = cli->getSyncMove(robot_name);
    syn_move->axisGroupAdd(axis_group_name, { 0, 1, 0 }, "base");
    syn_move->axisGroupAddAxis(axis_group_name, cli->getAxisNames().front(),
                               "base", { 0, 1, 0 });
    robot_interface->getRobotConfig()->enableAxisGroup(axis_group_name);

    // 接口调用: 直线运动到位置1
    robot_interface->getMotionControl()->moveLineWithAxisGroup(
        pose1, 1.2, 0.25, 0.025, 0, axis_group_name, { -0.14 });
    // 阻塞
    ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "直线运动到位置1成功！" << std::endl;
    } else {
        std::cout << "直线运动到位置1失败！" << std::endl;
    }

    // 接口调用: 直线运动到位置2
    robot_interface->getMotionControl()->moveLineWithAxisGroup(
        pose2, 1.2, 0.25, 0.025, 0, axis_group_name, { -0.126 });
    // 阻塞
    ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "直线运动到位置2成功！" << std::endl;
    } else {
        std::cout << "直线运动到位置2失败！" << std::endl;
    }

    // 接口调用: 直线运动到位置3
    robot_interface->getMotionControl()->moveLineWithAxisGroup(
        pose3, 1.2, 0.25, 0.025, 0, axis_group_name, { -0.08 });
    // 阻塞
    ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "直线运动到位置3成功！" << std::endl;
    } else {
        std::cout << "直线运动到位置3失败！" << std::endl;
    }
}

void exampleMoveAxis2(RpcClientPtr cli)
{
    // 接口调用: 开启运行时。
    // 注意: 摆弧运动需要将运行时打开,否则摆弧不生效。
    cli->getRuntimeMachine()->start();

    // 关节角，单位: 弧度
    std::vector<double> joint_angle = {
        0.0 * (M_PI / 180),  -15.0 * (M_PI / 180), 100.0 * (M_PI / 180),
        25.0 * (M_PI / 180), 90.0 * (M_PI / 180),  0.0 * (M_PI / 180)
    };
    std::vector<double> joint_angle1 = {
        -30.93 * (M_PI / 180), -18.57 * (M_PI / 180), 95.20 * (M_PI / 180),
        23.79 * (M_PI / 180),  89.95 * (M_PI / 180),  -30.93 * (M_PI / 180)
    };
    // 位姿
    std::vector<double> pose1 = { 0.1112, -0.4403, 0.36491, -3.14, 0, 1.576 };
    std::vector<double> pose2 = {
        0.065, -0.41235, 0.43762, 3.044, 0.005, 0.045
    };
    std::vector<double> pose3 = { -0.34103, -0.35413, 0.53763,
                                  3.044,    0.005,    0.045 };

    // 接口调用: 获取机器人的名字
    auto robot_name = cli->getRobotNames().front();

    auto robot_interface = cli->getRobotInterface(robot_name);

    // 接口调用: 设置机械臂的速度比率
    robot_interface->getMotionControl()->setSpeedFraction(0.7);

    // 接口调用: 设置工具中心点（TCP相对于法兰盘中心的偏移）
    std::vector<double> tcp_offset(6, 0.0);
    robot_interface->getRobotConfig()->setTcpOffset(tcp_offset);

    // 接口调用: 关节运动到起始位置
    robot_interface->getMotionControl()->moveJoint(
        joint_angle, 80 * (M_PI / 180), 60 * (M_PI / 180), 0, 0);

    // 阻塞
    int ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "关节运动到起始位置成功！" << std::endl;
    } else {
        std::cout << "关节运动到起始位置失败！" << std::endl;
    }

    // 接口调用: 关节运动到起始位置
    robot_interface->getMotionControl()->moveJoint(
        joint_angle1, 80 * (M_PI / 180), 60 * (M_PI / 180), 0, 0);

    // 阻塞
    ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "关节运动到起始位置成功！" << std::endl;
    } else {
        std::cout << "关节运动到起始位置失败！" << std::endl;
    }

    // 接口调用: 直线运动到位置1
    robot_interface->getMotionControl()->moveLine(pose1, 1.2, 0.25, 0.0, 0);

    // 阻塞
    ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "直线运动到位置1成功！" << std::endl;
    } else {
        std::cout << "直线运动到位置1失败！" << std::endl;
    }

    std::string axis_group_name = "test";
    auto axis = cli->getAxisInterface(cli->getAxisNames().front());
    auto syn_move = cli->getSyncMove(robot_name);
    syn_move->axisGroupAdd(axis_group_name, { 0, 1, 0 }, "base");
    syn_move->axisGroupAddAxis(axis_group_name, cli->getAxisNames().front(),
                               "base", { 0, 1, 0 });
    robot_interface->getRobotConfig()->enableAxisGroup(axis_group_name);

    std::string params = "{\"type\":\"SINE\",\"frequency\":3,\"amplitude\": "
                         "[0.01,0.01],\"hold_distance\": "
                         "[0,0],\"hold_time\":[0,0], "
                         "\"angle\":[0,0], \"direction\":0}";

    // 接口调用: 开始摆动
    robot_interface->getMotionControl()->weaveStart(params);

    // 接口调用: 直线运动到位置3
    robot_interface->getMotionControl()->moveLineWithAxisGroup(
        pose2, 0.05, 0.01, 0.0, 0.0, axis_group_name, { 0.1 });

    // 接口调用: 直线运动到位置3
    robot_interface->getMotionControl()->moveLineWithAxisGroup(
        pose3, 0.05, 0.01, 0.0, 0.0, axis_group_name, { 0.2 });

    // 接口调用: 结束摆动
    robot_interface->getMotionControl()->weaveEnd();

    // 阻塞
    ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "直线运动到位置3成功！" << std::endl;
    } else {
        std::cout << "直线运动到位置3失败！" << std::endl;
    }

    // 摆弧运动结束后将运行时关闭
    cli->getRuntimeMachine()->stop();
}

/**
 * 功能: 机械臂直线运动
 * 步骤:
 * 第一步: 设置 RPC 超时、连接 RPC 服务、机械臂登录
 * 第二步: 设置运动速度比率和工具中心点
 * 第三步: 先关节运动到起始位置，然后再以直线运动的方式依次经过3个路点
 * 第四步: RPC 退出登录、断开连接
 */

#define LOCAL_IP "192.168.10.11"

int main(int argc, char **argv)
{
#ifdef WIN32
    // 将Windows控制台输出代码页设置为 UTF-8
    SetConsoleOutputCP(CP_UTF8);
#endif

    auto rpc_cli = std::make_shared<RpcClient>();
    // 接口调用: 设置 RPC 超时
    rpc_cli->setRequestTimeout(1000);
    // 接口调用: 连接到 RPC 服务
    rpc_cli->connect(LOCAL_IP, 30004);
    // 接口调用: 登录
    rpc_cli->login("aubo", "123456");

    // exampleMoveAxis1(rpc_cli);
    exampleMoveAxis2(rpc_cli); // 摆动

    // 接口调用: 退出登录
    rpc_cli->logout();
    // 接口调用: 断开连接
    rpc_cli->disconnect();

    return 0;
}
