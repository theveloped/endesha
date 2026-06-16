#include <math.h>
#include "aubo_sdk/rpc.h"
#include "aubo_sdk/rtde.h"
#include <fstream>
#include <atomic>
#include <mutex>
#ifdef _WIN32
#include <Windows.h>
#endif

using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;

std::mutex rtde_mtx_;
GripperStatusVector gripper_status;

void exampleGripper(RpcClientPtr cli)
{
    auto robot_name = cli->getRobotNames().front();
    auto models = cli->getGripperInterface()->gripperGetSupportedModels();
    std::cout << "supported models: " << std::endl << "   ";
    for (auto model : models) {
        std::cout << model << ",";
    }
    std::cout << std::endl;

    if (0 != cli->getGripperInterface()->gripperAdd("gripper_1",
                                                    "gripper.DH_PGE-50-26")) {
        std::cout << "添加夹爪错误" << std::endl;
        return;
    }

    cli->getGripperInterface()->gripperConnect("gripper_1", "/dev/ttyUSB0,1");
    int connect_count_ = 0;
    while (!cli->getGripperInterface()->gripperIsConnected("gripper_1") &&
           connect_count_++ < 5) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    if (!cli->getGripperInterface()->gripperIsConnected("gripper_1")) {
        std::cout << "夹爪gripper_1连接失败" << std::endl;
        return;
    }

    if (0 != cli->getGripperInterface()->gripperEnable("gripper_1", true)) {
        std::cout << "夹爪gripper_1激活失败" << std::endl;
        return;
    }
    int enable_count_ = 0;
    while (cli->getGripperInterface()->gripperIsConnected("gripper_1") &&
           !cli->getGripperInterface()->gripperIsEnabled("gripper_1") &&
           enable_count_++ < 5) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    if (!cli->getGripperInterface()->gripperIsEnabled("gripper_1")) {
        std::cout << "夹爪gripper_1激活失败" << std::endl;
        return;
    }

    std::cout << "运动到26的位置" << std::endl;
    cli->getGripperInterface()->gripperSetPosition("gripper_1", 26);
    cli->getGripperInterface()->gripperSetForce("gripper_1", 20);
    cli->getGripperInterface()->gripperSetVelocity("gripper_1", 50);
    if (0 != cli->getGripperInterface()->gripperMove("gripper_1")) {
        std::cout << "夹爪gripper_1运动失败" << std::endl;
        return;
    }
    std::this_thread::sleep_for(std::chrono::seconds(1));
    while (cli->getGripperInterface()->gripperIsConnected("gripper_1") &&
           cli->getGripperInterface()->gripperGetMotionState("gripper_1")) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    std::cout << "运动到0的位置" << std::endl;
    cli->getGripperInterface()->gripperSetPosition("gripper_1", 0);
    cli->getGripperInterface()->gripperSetForce("gripper_1", 20);
    cli->getGripperInterface()->gripperSetVelocity("gripper_1", 50);
    if (0 != cli->getGripperInterface()->gripperMove("gripper_1")) {
        std::cout << "夹爪gripper_1运动失败" << std::endl;
        return;
    }
    std::this_thread::sleep_for(std::chrono::seconds(1));
    while (cli->getGripperInterface()->gripperIsConnected("gripper_1") &&
           cli->getGripperInterface()->gripperGetMotionState("gripper_1")) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    std::this_thread::sleep_for(std::chrono::seconds(10));

    if (0 != cli->getGripperInterface()->gripperEnable("gripper_1", false)) {
        std::cout << "夹爪gripper_1激活失败" << std::endl;
        return;
    }

    std::this_thread::sleep_for(std::chrono::seconds(5));

    cli->getGripperInterface()->gripperDelete("gripper_1");
}

void rtdeGripperStatus(RtdeClientPtr rtde_cli)
{
    // 接口调用: 设置话题
    int topic5 = rtde_cli->setTopic(false, { "gripper_status" }, 1, 5);
    // 接口调用: 订阅
    rtde_cli->subscribe(topic5, [](InputParser &parser) {
        std::unique_lock<std::mutex> lck(rtde_mtx_);
        gripper_status = parser.popGripperStatusVector();
        for (auto status : gripper_status) {
            std::cout << "name: " << status.name << std::endl;
            std::cout << "  is_connected: " << status.is_connected << std::endl;
            std::cout << "  is_enabled: " << status.is_enabled << std::endl;
            std::cout << "  position: " << status.position << std::endl;
            std::cout << "  velocity: " << status.velocity << std::endl;
            std::cout << "  force: " << status.force << std::endl;
            std::cout << "  angle: " << status.angle << std::endl;
            std::cout << "  r_velocity: " << status.r_velocity << std::endl;
            std::cout << "  torque: " << status.torque << std::endl;
            std::cout << "  object_detection: " << status.object_detection
                      << std::endl;
            std::cout << "  motion_state: " << status.motion_state << std::endl;
            std::cout << "  voltage: " << status.voltage << std::endl;
            std::cout << "  temperature: " << status.temperature << std::endl;
        }
    });
}

#define LOCAL_IP "127.0.0.1"
int main(int argc, char **argv)
{
#ifdef _WIN32
    // 将Windows控制台输出代码页设置为 UTF-8
    SetConsoleOutputCP(CP_UTF8);
#endif
    auto rpc_cli = std::make_shared<RpcClient>();
    rpc_cli->setRequestTimeout(1000);
    // 接口调用: 连接到 RPC 服务
    rpc_cli->connect(LOCAL_IP, 30004);
    // 接口调用: 登录
    rpc_cli->login("aubo", "123456");

    auto rtde_cli = std::make_shared<RtdeClient>();
    // 接口调用: 连接到 RTDE 服务
    rtde_cli->connect(LOCAL_IP, 30010);
    // 接口调用: 登录
    rtde_cli->login("aubo", "123456");

    rtdeGripperStatus(rtde_cli);

    exampleGripper(rpc_cli);
}
