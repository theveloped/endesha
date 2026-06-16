#include <cstring>
#include <fstream>
#include <math.h>
#ifdef WIN32
#include <windows.h>
#endif

#include "aubo_sdk/rpc.h"
#include "trajectory_io.h"

using namespace arcs::aubo_sdk;
using namespace arcs::common_interface;

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#define EMBEDDED

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

template <typename T>
inline std::ostream &operator<<(std::ostream &os, const std::vector<T> &list)
{
    for (size_t i = 0; i < list.size(); i++) {
        os << list.at(i);
        if (i != (list.size() - 1)) {
            os << ",";
        }
    }
    return os;
}

int waitServoJointComplete(RobotInterfacePtr impl, int timeout_ms = 10000)
{
    auto start_time = std::chrono::steady_clock::now();

    while (impl->getMotionControl()->getMotionLeftTime(0) != 0) {
        auto current_time = std::chrono::steady_clock::now();
        auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                              current_time - start_time)
                              .count();

        if (elapsed_ms >= timeout_ms) {
            std::cout << "Warning: WaitServoJointComplete timeout after "
                      << elapsed_ms << " ms" << std::endl;
            return 1;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    while (!impl->getRobotState()->isSteady()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    return 0;
}

/**
 * 测试1:
 * 开启力控 采用servoj跟踪一个轨迹,目标点下发时间间隔5ms
 */
int exampleServoj1(RpcClientPtr cli)
{
    auto robot_name = cli->getRobotNames().front();
#ifdef EMBEDDED
    // 内置传感器
    std::vector<double> sensor_pose = { 0, 0, 0, 0, 0, 0 };
    cli->getRobotInterface(robot_name)
        ->getRobotConfig()
        ->selectTcpForceSensor("embedded");
#else
    // 外置坤维传感器
    std::vector<double> sensor_pose = { 0, 0, 0.047, 0, 0, 0 };
    cli->getRobotInterface(robot_name)
        ->getRobotConfig()
        ->selectTcpForceSensor("kw_ftsensor");
#endif

    // 设置传感器安装位姿
    cli->getRobotInterface(robot_name)
        ->getRobotConfig()
        ->setTcpForceSensorPose(sensor_pose);
    // 设置TCP偏移
    std::vector<double> tcp_pose = { 0, 0, 0.0, 0, 0, 0 };
    cli->getRobotInterface(robot_name)
        ->getRobotConfig()
        ->setTcpOffset(tcp_pose);

    double mass = 0.0;
    std::vector<double> com = { 0.0, 0.0, 0.0 };
    // 设置负载
    cli->getRobotInterface(robot_name)
        ->getRobotConfig()
        ->setPayload(mass, com, { 0. }, { 0. });
    // 力传感器偏移需要根据实际情况设置
    std::vector<double> force_offset = cli->getRobotInterface(robot_name)
                                           ->getRobotState()
                                           ->getTcpForceSensors();

    // 设置力传感器偏移
    cli->getRobotInterface(robot_name)
        ->getRobotConfig()
        ->setTcpForceOffset(force_offset);

    std::vector<double> admittance_m = { 25.0, 25.0, 25.0, 2.0, 2.0, 2.0 };
    std::vector<double> admittance_d = {
        300.0, 300.0, 300.0, 12.0, 12.0, 12.0
    };
    std::vector<double> admittance_k = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };

    cli->getRobotInterface("rob1")->getForceControl()->setDynamicModel(
        admittance_m, admittance_d, admittance_k);

    // 力控开启方向
    std::vector<bool> compliance = { false, false, true, false, false, false };
    // 目标力
    std::vector<double> target_wrench{ 0.0, 0.0, 5.0, 0.0, 0.0, 0.0 };
    std::vector<double> speed_limits(6, 2.0);

    std::vector<double> feature = { 0, 0, 0, 0, 0, 0 };
    TaskFrameType frame_type = TaskFrameType::TOOL_FORCE;
    cli->getRobotInterface(robot_name)
        ->getForceControl()
        ->setTargetForce(feature, compliance, target_wrench, speed_limits,
                         frame_type);

    // 读取轨迹文件
    auto filename = "../trajs/record6.offt";
    TrajectoryIo input(filename);

    // 尝试打开轨迹文件，如果无法打开，直接返回
    if (!input.open()) {
        return 0;
    }

    // 解析轨迹数据
    auto traj = input.parse();

    // 检查轨迹文件中是否有路点，
    // 如果数量为 0，输出错误消息并返回
    auto traj_sz = traj.size();
    if (traj_sz == 0) {
        std::cerr << "轨迹文件中的路点数量为0." << std::endl;
        return 0;
    }

    // 接口调用: 获取机器人的名字
    auto robot_interface = cli->getRobotInterface(robot_name);

    // 接口调用: 设置机械臂的速度比率
    robot_interface->getMotionControl()->setSpeedFraction(1);

    // 接口调用: 关节运动到轨迹中的第一个点，否则容易引起较大超调
    robot_interface->getMotionControl()->moveJoint(traj[99], 80 * (M_PI / 180),
                                                   60 * (M_PI / 180), 0, 0);

    // 阻塞
    int ret = waitArrival(robot_interface);
    if (ret == 0) {
        std::cout << "关节运动到轨迹文件中的第一个路点成功" << std::endl;
    } else {
        std::cout << "关节运动到轨迹文件中的第一个路点失败" << std::endl;
    }
    robot_interface->getForceControl()->fcEnable();

    // 接口调用: 开启 servo 模式 7
    cli->getRobotInterface(robot_name)
        ->getMotionControl()
        ->setServoModeSelect(7);
    // 等待进入 servo 模式
    int i = 0;
    while (cli->getRobotInterface(robot_name)
               ->getMotionControl()
               ->getServoModeSelect() != 7) {
        if (i++ > 20) {
            std::cout << "Servo 模式使能失败! 当前的 Servo 模式是 "
                      << cli->getRobotInterface(robot_name)
                             ->getMotionControl()
                             ->getServoModeSelect()
                      << std::endl;
            return -1;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(7));
    }

    for (size_t i = 100; i < traj.size(); i++) {
        // 接口调用: 关节伺服运动

        while (cli->getRobotInterface(robot_name)
                   ->getMotionControl()
                   ->servoJoint(traj[i], 0.1, 0.2, 0.05, 0.1, 200) == 2) {
            // 缓存满了，需要重新下发
            // std::this_thread::sleep_for(std::chrono::milliseconds(5));
            std::cout << "Buffer is full，i: " << i << std::endl;
        }

        // std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    // 等待运动结束
    int wait_servo = waitServoJointComplete(robot_interface);

    if (wait_servo == 0) {
        std::cout << "Servoj 运动结束" << std::endl;
    }

    // 接口调用: 关闭 servo 模式  7
    cli->getRobotInterface(robot_name)
        ->getMotionControl()
        ->setServoModeSelect(0);

    // 等待结束 servo 模式7
    while (cli->getRobotInterface(robot_name)
               ->getMotionControl()
               ->getServoModeSelect() != 0) {
        if (i++ > 20) {
            std::cout << "Servo 模式失能失败! 当前的 Servo 模式是 "
                      << cli->getRobotInterface(robot_name)
                             ->getMotionControl()
                             ->getServoModeSelect()
                      << std::endl;
            return -1;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    cli->getRobotInterface("rob1")->getForceControl()->fcDisable();

    return 0;
}

#define LOCAL_IP "192.168.3.10"
/**
 * servoj功能使用步骤:
 * 1、采用实时系统测试servoj功能
 * 2、孤立一个CPU，保证该CPU没有其他任务
 * 3、将该进程设置为实时进程，优先级设置为最大
 * 4、绑定CPU，将该实时进程绑定到第二步孤立的CPU上
 */
int main(void)
{
#ifdef WIN32
    // 将Windows控制台输出代码页设置为 UTF-8
    SetConsoleOutputCP(CP_UTF8);
#endif
#ifndef _WIN32
    // 实时优先级最大值、最小值
    int sched_max = sched_get_priority_max(SCHED_FIFO);

    // 设置实时调度策略及优先级
    struct sched_param sParam;
    sParam.sched_priority = sched_max;
    sched_setscheduler(0, SCHED_FIFO, &sParam);
    auto i_schedFlag = sched_getscheduler(0);
    printf("设置调度策略 = [%d]\n", i_schedFlag);

    // 绑定CPU
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(1, &cpuset);

    // bind process to processor 0
    if (sched_setaffinity(0, sizeof(cpuset), &cpuset) < 0) {
        perror("Sched_setaffinity fail!");
    }
#endif

    auto rpc_cli = std::make_shared<RpcClient>();
    // 接口调用: 设置 RPC 超时
    rpc_cli->setRequestTimeout(1000);
    // 接口调用: 连接到 RPC 服务
    rpc_cli->connect(LOCAL_IP, 30004);
    // 接口调用: 登录
    rpc_cli->login("aubo", "123456");

    exampleServoj1(rpc_cli);

    // 接口调用: RPC 退出登录
    rpc_cli->logout();
    // 接口调用: RPC 断开连接
    rpc_cli->disconnect();

    return 0;
}
