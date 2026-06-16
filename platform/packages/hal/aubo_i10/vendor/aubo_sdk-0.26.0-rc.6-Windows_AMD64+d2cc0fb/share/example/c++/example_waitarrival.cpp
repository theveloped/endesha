#include <mutex>
#include "aubo_sdk/rpc.h"
#include "aubo_sdk/rtde.h"
#ifdef WIN32
#include <windows.h>

#include <thread>
#include <chrono>
#include <atomic>
#endif
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;

bool marks = true;
int line_number_ = -1;
void getIineNumberThread(RpcClientPtr cli) {
    auto robot_name = cli->getRobotNames().front();
    auto robot_interface = cli->getRobotInterface(robot_name);
    auto robot = robot_interface->getMotionControl();
    while (marks) {
        int now_id = robot->getExecId();
        std::cout << "[Info] getExecId() = " << now_id << ", line_number = " << line_number_ << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(400));
    }
}
void exampleSubscribe(RtdeClientPtr cli) {
    // 接口调用: 设置话题
    int topic6 = cli->setTopic(
        false,
        { "line_number" },
        20, 1);
    // 接口调用: 订阅
    cli->subscribe(topic6, [](InputParser& parser) {
        line_number_ = parser.popInt32();
        });
}

int waitArrival(MotionControlPtr robot, int line_number) {
    int pre = -1;
    while (line_number_ <= line_number ) {
        //判断执行到最后一个动作是否结束
        if (line_number == line_number_ && robot->getExecId() == -1) break;
        if (pre != line_number_) {
            std::cout << "当前运行的行号:" << line_number_ << std::endl;
        }
        pre = line_number_;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    return 0;
}
void exampleLineNumber(RpcClientPtr cli) {
    auto robot_name = cli->getRobotNames().front();

    auto robot_interface = cli->getRobotInterface(robot_name);


    auto robot = robot_interface->getMotionControl();

    auto runtime_machine = cli->getRuntimeMachine();

    robot->setSpeedFraction(0.75);

    std::thread t(getIineNumberThread, cli);

    std::vector<double> p1 = { 0.19428619034678518,-0.5477608722089901,0.05945241593428857,3.0868983663567846,0.535193210204831,-0.6486764986738255 };
    std::vector<double> p2 = { 0.26628055485158936,-0.4452622728139073,0.05943906412892791,3.086882116513631,0.5352135514900898,-1.4571389628082894 };
    std::vector<double> p3 = { 0.476184624335076,-0.3371768923013714,0.059568293687588536,3.088011074607731,0.5343896398560942,-0.7063579432095806 };
    std::vector<double> p4 = { 0.4425770780036432,-0.13597592887177673,0.05922236680382481,3.0911455124422482,0.535789927543353,0.06408754959673374 };
    std::vector<double> p5 = { 0.4839375031260943,0.009252793806966662,0.05899314514545728,3.0916751089973316,0.5363234034471815,-0.741794514981592 };

    int tid, ret, line_number = 0;
    tid = runtime_machine->newTask(); //创建task
    runtime_machine->start(); // 开始运行
    
    runtime_machine->setPlanContext(tid,++line_number, "line 1");
    robot->moveLine(p1, 2, 0.25, 0, 0);
    
    runtime_machine->setPlanContext(tid, ++line_number, "line 2");
    robot->moveLine(p2, 2, 0.25, 0, 0);

    robot->setCirclePathMode(0);
    runtime_machine->setPlanContext(tid, ++line_number, "circle 3");
    robot->moveCircle(p3, p4, 2, 0.25, 0, 0);

    runtime_machine->setPlanContext(tid, ++line_number, "line 4");
    robot->moveLine(p5, 2, 0.25, 0, 0);

    waitArrival(robot, line_number);

    runtime_machine->stop();
    runtime_machine->deleteTask(tid); //删除task
    marks = false;
    t.join();
}

/**
 * 功能: 机器臂运行行号输出
 * 步骤:
 * 第一步: 连接 RTDE 服务、机械臂登录
 * 第二步: 设置 RPC 超时、连接到 RPC 服务、登录
 * 第三步: 设置RTDE输入
 * 第四步: 信息输出
 * 第五步: RTDE 退出登录、断开连接
 * 第六步: RPC 退出登录、断开连接
 */

#define LOCAL_IP "192.168.1.103"

int main(int argc, char** argv)
{
#ifdef WIN32
    // 将Windows控制台输出代码页设置为 UTF-8
    SetConsoleOutputCP(CP_UTF8);
#endif

    auto rtde_cli = std::make_shared<RtdeClient>();
    // 接口调用: 连接到 RTDE 服务
    rtde_cli->connect(LOCAL_IP, 30010);
    // 接口调用: 登录
    rtde_cli->login("aubo", "123456");

    //订阅行号信息
    exampleSubscribe(rtde_cli);

    auto rpc_cli = std::make_shared<RpcClient>();
    // 接口调用: 设置 RPC 超时
    rpc_cli->setRequestTimeout(1000);
    // 接口调用: 连接到 RPC 服务
    rpc_cli->connect(LOCAL_IP, 30004);
    // 接口调用: 登录
    rpc_cli->login("aubo", "123456");


    exampleLineNumber(rpc_cli);

    // 接口调用: 退出登录
    rtde_cli->logout();
    // 接口调用: 断开连接
    rtde_cli->disconnect();

    // 接口调用: 退出登录
    rpc_cli->logout();
    // 接口调用: 断开连接
    rpc_cli->disconnect();

    return 0;
}
