#include "aubo_sdk/rpc.h"
#ifdef WIN32
#include <Windows.h>
#endif

#include <math.h>

using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;

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

void exampleCalibrateForceOffset(RpcClientPtr impl)
{
    std::vector<double> joint1 = {
        161.01, -18.80, -88.00, -67.45, -91.85, 90.02
    };
    std::vector<double> joint2 = {
        161.01, -18.80, -88.00, -67.45, -91.85, 0.01
    };
    std::vector<double> joint3 = {
        161.01, -18.80, -88.00, 20.00, -91.85, 0.00
    };

    for (int i = 0; i < 6; i++) {
        joint1[i] = joint1[i] / 180.0 * M_PI;
    }

    if (impl.get() == nullptr || !impl->hasConnected() || !impl->hasLogined()) {
        std::cout << "not login" << std::endl;
        return;
    }

    auto robot_name = impl->getRobotNames().front();
    int ret = 0;

    // 运动到第一个标定位姿
    std::cout << "[ForceControl] goto p0 {" << joint1[0] << "," << joint1[1]
              << "," << joint1[2] << "," << joint1[3] << "," << joint1[4] << ","
              << joint1[5] << "}" << std::endl;
    if (!(ret = impl->getRobotInterface(robot_name)
                    ->getMotionControl()
                    ->moveJoint(joint1, 10 * (M_PI / 180), 5 * (M_PI / 180), 0,
                                0))) {
        waitArrival(impl->getRobotInterface(robot_name));
    } else {
        std::cout << "[ForceControl] 运动到第1个标定位姿错误" << std::endl;
        return;
    }
    //等待机器人停稳
    std::this_thread::sleep_for(std::chrono::seconds(1));
    //记录关节位置和tcp force
    auto q1 = impl->getRobotInterface(robot_name)
                  ->getRobotState()
                  ->getJointPositions();
    auto tcp_force1 = impl->getRobotInterface(robot_name)
                          ->getRobotState()
                          ->getTcpForceSensors();
    std::cout << "[ForceControl] q1 {" << q1[0] << "," << q1[1] << "," << q1[2]
              << "," << q1[3] << "," << q1[4] << "," << q1[5] << "}"
              << std::endl;
    std::cout << "[ForceControl] tcp_force1 {" << tcp_force1[0] << ","
              << tcp_force1[1] << "," << tcp_force1[2] << "," << tcp_force1[3]
              << "," << tcp_force1[4] << "," << tcp_force1[5] << "}"
              << std::endl;

    // 运动到第二个标定位姿
    std::cout << "[ForceControl] goto p1 {" << joint2[0] << "," << joint2[1]
              << "," << joint2[2] << "," << joint2[3] << "," << joint2[4] << ","
              << joint2[5] << "}" << std::endl;
    if (!(ret = impl->getRobotInterface(robot_name)
                    ->getMotionControl()
                    ->moveJoint(joint2, 10 * (M_PI / 180), 5 * (M_PI / 180), 0,
                                0))) {
        waitArrival(impl->getRobotInterface(robot_name));
    } else {
        std::cout << "[ForceControl] 运动到第二个标定位姿错误" << std::endl;
        return;
    }
    //等待机器人停稳
    std::this_thread::sleep_for(std::chrono::seconds(1));
    //记录关节位置和tcp force
    auto q2 = impl->getRobotInterface(robot_name)
                  ->getRobotState()
                  ->getJointPositions();
    auto tcp_force2 = impl->getRobotInterface(robot_name)
                          ->getRobotState()
                          ->getTcpForceSensors();
    std::cout << "[ForceControl] q2 {" << q2[0] << "," << q2[1] << "," << q2[2]
              << "," << q2[3] << "," << q2[4] << "," << q2[5] << "}"
              << std::endl;
    std::cout << "[ForceControl] tcp_force2 {" << tcp_force2[0] << ","
              << tcp_force2[1] << "," << tcp_force2[2] << "," << tcp_force2[3]
              << "," << tcp_force2[4] << "," << tcp_force2[5] << "}"
              << std::endl;

    // 运动到第三个标定位姿
    std::cout << "[ForceControl] goto p2 {" << joint3[0] << "," << joint3[1]
              << "," << joint3[2] << "," << joint3[3] << "," << joint3[4] << ","
              << joint3[5] << "}" << std::endl;
    if (!(ret = impl->getRobotInterface(robot_name)
                    ->getMotionControl()
                    ->moveJoint(joint3, 20 * (M_PI / 180), 10 * (M_PI / 180), 0,
                                0))) {
        waitArrival(impl->getRobotInterface(robot_name));
    } else {
        std::cout << "[ForceControl] 运动到第三个标定位姿错误" << std::endl;
        return;
    }
    //等待机器人停稳
    std::this_thread::sleep_for(std::chrono::seconds(1));
    //记录关节位置和tcp force
    auto q3 = impl->getRobotInterface(robot_name)
                  ->getRobotState()
                  ->getJointPositions();
    auto tcp_force3 = impl->getRobotInterface(robot_name)
                          ->getRobotState()
                          ->getTcpForceSensors();
    std::cout << "[ForceControl] q3 {" << q3[0] << "," << q3[1] << "," << q3[2]
              << "," << q3[3] << "," << q3[4] << "," << q3[5] << "}"
              << std::endl;
    std::cout << "[ForceControl] tcp_force3 {" << tcp_force3[0] << ","
              << tcp_force3[1] << "," << tcp_force3[2] << "," << tcp_force3[3]
              << "," << tcp_force3[4] << "," << tcp_force3[5] << "}"
              << std::endl;

    std::vector<std::vector<double>> calib_forces{ tcp_force1, tcp_force2,
                                                   tcp_force3 };

    std::vector<std::vector<double>> calib_q{ q1, q2, q3 };

    auto offset = impl->getRobotInterface(robot_name)
                      ->getRobotAlgorithm()
                      ->calibrateTcpForceSensorOffset(calib_forces, calib_q);

    printf(" force_offset: %.6f, %.6f, %.6f, %.6f, %.6f, "
           "%.6f.\n",
           offset[0], offset[1], offset[2], offset[3], offset[4], offset[5]);

    impl->getRobotInterface(robot_name)
        ->getRobotConfig()
        ->setTcpForceOffset(offset);
}

#define LOCAL_IP "192.168.1.102"

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

    exampleCalibrateForceOffset(rpc_cli);

    // 接口调用: 退出登录
    rpc_cli->logout();
    // 接口调用: 断开连接
    rpc_cli->disconnect();

    return 0;
}
