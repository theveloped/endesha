/**
 * @file example_joint_trajectory.cpp
 * @brief Aubo 机械臂多点位关节轨迹运动示例
 *
 * 本示例演示了如何使用 Aubo SDK 控制机械臂进行多点位关节轨迹运动
 * 主要功能包括：
 *    - 建立 RPC 连接并登录
 *    - 检查安全状态、设置负载、上电和松刹车
 *    - 启动运行时(start)环境
 *    - 使用 moveJoint 进行多点位往复运动
 *    - 使用 setLabel 和 getPlanContext 跟踪当前执行点位
 *
 * \warning: 运行前请根据实际情况修改代码中的关节角度和负载参数！
 *
 * 使用方法:
 *   ./example_joint_trajectory [roobot_ip]
 *   默认连接 kDefaultRobotIP
 */

#include <aubo_sdk/rpc.h>
#include <iostream>
#include <thread>
#include <chrono>
#include <vector>
#include <cmath>

#ifdef _WIN32
#include <windows.h>
#endif

using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;

//==============================================================================
// 常量定义
//==============================================================================

/** @brief 默认机器人 IP 地址 */
constexpr char kDefaultRobotIp[] = "127.0.0.1";

/** @brief RPC 服务端口号 */
constexpr int kRpcPort = 30004;

/** @brief RPC 请求超时时间（毫秒） */
constexpr int kRpcTimeoutMs = 1000;

/** @brief 运行时启动超时时间（毫秒） */
constexpr int kRuntimeStartTimeoutMs = 3000;

/** @brief 运行时状态轮询间隔（毫秒） */
constexpr int kRuntimePollIntervalMs = 20;

/** @brief 上电超时时间（毫秒） */
constexpr int kPowerOnTimeoutMs = 20000;

/** @brief 松刹车超时时间（毫秒） */
constexpr int kStartupTimeoutMs = 10000;

/** @brief 机械臂模式轮询间隔（毫秒） */
constexpr int kRobotModePollIntervalMs = 1000;

//==============================================================================
// 工具函数
//==============================================================================

/**
 * @brief 将角度值转换为弧度值
 * @param degree 角度值（度）
 * @return 对应的弧度值
 */
constexpr double degreeToRadian(double degree)
{
    return degree * M_PI / 180.0;
}

//==============================================================================
// 等待辅助函数
//==============================================================================

/**
 * @brief 等待机械臂进入指定的工作模式
 *
 * 该函数会轮询机械臂的当前模式，直到达到目标模式或超时。
 * 机械臂的模式转换是异步的，例如上电后需要等待进入 Idle 模式，
 * 松刹车后需要等待进入 Running 模式。
 *
 * @param robot 机器人接口指针
 * @param target_mode 目标工作模式（如 Idle、Running 等）
 * @param timeout_ms 超时时间（毫秒）
 * @return true 成功进入目标模式
 * @return false 超时未能进入目标模式
 */
bool waitForRobotMode(RobotInterfacePtr robot, RobotModeType target_mode,
                      int timeout_ms)
{
    int elapsed_ms = 0;
    while (elapsed_ms < timeout_ms) {
        auto current_mode = robot->getRobotState()->getRobotModeType();
        if (current_mode == target_mode) {
            return true;
        }
        std::cout << "当前模式: " << current_mode << std::endl;
        std::this_thread::sleep_for(
            std::chrono::milliseconds(kRobotModePollIntervalMs));
        elapsed_ms += kRobotModePollIntervalMs;
    }
    return false;
}

/**
 * @brief 等待运行时环境进入 Running 状态
 *
 * 运行时（RuntimeMachine）启动后需要一定时间完成初始化，
 * 该函数会轮询运行时状态，直到进入 Running 状态或超时。
 * 只有在 Running 状态下才能下发运动指令。
 *
 * @param runtime 运行时接口指针
 * @param timeout_ms 超时时间（毫秒），默认为 kRuntimeStartTimeoutMs
 * @return true 运行时已进入 Running 状态
 * @return false 超时未能进入 Running 状态
 */
bool waitForRuntimeRunning(RuntimeMachinePtr runtime,
                           int timeout_ms = kRuntimeStartTimeoutMs)
{
    int elapsed_ms = 0;
    while (elapsed_ms < timeout_ms) {
        if (runtime->getRuntimeState() == RuntimeState::Running) {
            return true;
        }
        std::this_thread::sleep_for(
            std::chrono::milliseconds(kRuntimePollIntervalMs));
        elapsed_ms += kRuntimePollIntervalMs;
    }
    return false;
}

//==============================================================================
// 主函数
//==============================================================================

/**
 * @brief 程序入口函数
 *
 * 执行流程：
 *   1. 建立 RPC 连接并登录
 *   2. 检查安全状态、设置负载、上电和松刹车
 *   3. 启动运行时环境
 *   4. 执行往复运动并等待完成
 *   5. 清理并退出
 *
 * @param argc 命令行参数个数
 * @param argv 命令行参数数组，argv[1] 可指定机器人 IP
 * @return 0 成功，-1 失败
 */
int main(int argc, char *argv[])
{
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif

    std::string robot_ip = kDefaultRobotIp;
    if (argc > 1) {
        robot_ip = argv[1];
    }

    // 创建 RPC 客户端，用于与机器人控制器通信
    auto rpc_client = std::make_shared<RpcClient>();
    RuntimeMachinePtr runtime = nullptr;

    try {
        //----------------------------------------------------------------------
        // 第一步：建立 RPC 连接并登录
        //----------------------------------------------------------------------

        rpc_client->setRequestTimeout(kRpcTimeoutMs);

        if (rpc_client->connect(robot_ip, kRpcPort) != AUBO_OK) {
            std::cerr << "连接失败: " << robot_ip << ":" << kRpcPort
                      << std::endl;
            return -1;
        }
        std::cout << "已连接到 " << robot_ip << std::endl;

        // 使用默认账户登录
        if (rpc_client->login("aubo", "123456") != AUBO_OK) {
            std::cerr << "登录失败" << std::endl;
            rpc_client->disconnect();
            return -1;
        }
        std::cout << "登录成功" << std::endl;

        // 获取机器人接口
        auto robot_names = rpc_client->getRobotNames();
        if (robot_names.empty()) {
            std::cerr << "未找到机器人" << std::endl;
            rpc_client->logout();
            rpc_client->disconnect();
            return -1;
        }
        auto robot = rpc_client->getRobotInterface(robot_names.front());

        //----------------------------------------------------------------------
        // 第二步：检查安全状态、设置负载、上电和松刹车
        //----------------------------------------------------------------------

        // 检查安全状态，只有 Normal 和 ReducedMode 可以正常操作
        auto safety_mode = robot->getRobotState()->getSafetyModeType();
        std::cout << "当前安全模式: " << safety_mode << std::endl;

        // 尝试恢复异常安全状态
        if (safety_mode == SafetyModeType::ProtectiveStop ||
            safety_mode == SafetyModeType::Violation) {
            std::cout << "检测到保护性停机，正在解锁..." << std::endl;
            robot->getRobotManage()->setUnlockProtectiveStop();
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            safety_mode = robot->getRobotState()->getSafetyModeType();
        }

        if (safety_mode == SafetyModeType::SystemEmergencyStop ||
            safety_mode == SafetyModeType::RobotEmergencyStop ||
            safety_mode == SafetyModeType::Fault) {
            // 急停或故障，尝试重置安全接口板
            std::cout << "检测到急停/故障，正在重置..." << std::endl;
            robot->getRobotManage()->restartInterfaceBoard();
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
            safety_mode = robot->getRobotState()->getSafetyModeType();
        }

        // 再次检查安全状态
        if (safety_mode != SafetyModeType::Undefined &&
            safety_mode != SafetyModeType::Normal &&
            safety_mode != SafetyModeType::ReducedMode) {
            std::cerr << "安全状态异常: " << safety_mode << std::endl;
            if (safety_mode == SafetyModeType::SafeguardStop) {
                std::cerr << "防护停机，请检查安全IO信号是否正常" << std::endl;
            } else if (safety_mode == SafetyModeType::Recovery) {
                std::cerr << "机械臂超出安全限制，请手动移动到安全位置"
                          << std::endl;
            } else if (safety_mode == SafetyModeType::SystemEmergencyStop ||
                       safety_mode == SafetyModeType::RobotEmergencyStop) {
                std::cerr << "请释放急停按钮" << std::endl;
            } else if (safety_mode == SafetyModeType::Fault) {
                std::cerr << "机械臂存在硬件故障，请联系技术支持" << std::endl;
            }
            rpc_client->logout();
            rpc_client->disconnect();
            return -1;
        }

        // 设置负载参数（质量kg, 重心m, 惯量kg·m²）
        // 警告：请根据实际末端负载修改参数！
        robot->getRobotConfig()->setPayload(0, { 0, 0, 0 }, {},
                                            { 0, 0, 0, 0, 0, 0 });

        // 机械臂模式转换流程：Disconnected -> PowerOff -> Idle -> Running
        auto robot_mode = robot->getRobotState()->getRobotModeType();
        std::cout << "当前机械臂模式: " << robot_mode << std::endl;

        // 如果未上电（PowerOff 或更早状态），需要先上电
        if (robot_mode != RobotModeType::Idle &&
            robot_mode != RobotModeType::Running) {
            std::cout << "正在上电..." << std::endl;
            if (robot->getRobotManage()->poweron() != AUBO_OK) {
                std::cerr << "上电请求失败" << std::endl;
                rpc_client->logout();
                rpc_client->disconnect();
                return -1;
            }

            if (!waitForRobotMode(robot, RobotModeType::Idle,
                                  kPowerOnTimeoutMs)) {
                std::cerr << "等待上电超时" << std::endl;
                rpc_client->logout();
                rpc_client->disconnect();
                return -1;
            }
            robot_mode = RobotModeType::Idle;
        }

        // 如果已上电但未松刹车（Idle 状态），需要松刹车
        if (robot_mode == RobotModeType::Idle) {
            std::cout << "正在松刹车..." << std::endl;
            if (robot->getRobotManage()->startup() != AUBO_OK) {
                std::cerr << "松刹车请求失败" << std::endl;
                rpc_client->logout();
                rpc_client->disconnect();
                return -1;
            }

            if (!waitForRobotMode(robot, RobotModeType::Running,
                                  kStartupTimeoutMs)) {
                std::cerr << "等待松刹车超时" << std::endl;
                rpc_client->logout();
                rpc_client->disconnect();
                return -1;
            }
        }

        std::cout << "机械臂已就绪" << std::endl;

        //----------------------------------------------------------------------
        // 第三步：启动运行时环境
        //----------------------------------------------------------------------

        // 获取运行时环境接口，运行时是执行运动指令的核心组件
        runtime = rpc_client->getRuntimeMachine();
        std::cout << "正在启动运行时..." << std::endl;
        bool runtime_started = false;
        int elapsed_ms = 0;
        while (elapsed_ms < kRuntimeStartTimeoutMs) {
            if (runtime->start() == AUBO_OK) {
                runtime_started = true;
                break;
            }
            std::this_thread::sleep_for(
                std::chrono::milliseconds(kRuntimePollIntervalMs));
            elapsed_ms += kRuntimePollIntervalMs;
        }

        if (!runtime_started) {
            std::cerr << "运行时启动超时" << std::endl;
            rpc_client->logout();
            rpc_client->disconnect();
            return -1;
        }

        if (!waitForRuntimeRunning(runtime)) {
            std::cerr << "等待运行时就绪超时" << std::endl;
            rpc_client->logout();
            rpc_client->disconnect();
            return -1;
        }
        std::cout << "运行时已启动" << std::endl;

        //----------------------------------------------------------------------
        // 第四步：执行往复运动并等待完成
        //----------------------------------------------------------------------

        // 定义 3 组关节目标位置（6 轴机器人，每组 6 个关节角度，单位：弧度）
        // 警告：运行前请根据实际机型修改关节角度，避免碰撞或超限！
        std::vector<std::vector<double>> joint_positions = {
            // 位置 1：初始位置
            { degreeToRadian(0.0), degreeToRadian(-15.0), degreeToRadian(100.0),
              degreeToRadian(25.0), degreeToRadian(90.0), degreeToRadian(0.0) },

            // 位置 2：中间位置
            { degreeToRadian(35.92), degreeToRadian(-11.28),
              degreeToRadian(59.96), degreeToRadian(-18.76),
              degreeToRadian(90.0), degreeToRadian(35.92) },

            // 位置 3：目标位置
            { degreeToRadian(41.04), degreeToRadian(-7.65),
              degreeToRadian(98.80), degreeToRadian(16.44),
              degreeToRadian(90.0), degreeToRadian(11.64) }
        };
        // 设置全局速度比率（0.0~1.0），影响所有运动指令的实际速度
        // 提示：示例默认使用较低速度，可根据实际需求调整
        robot->getMotionControl()->setSpeedFraction(0.3);

        // 构建完整的运动序列
        // 单次往复：位置1 -> 位置2 -> 位置3 -> 位置2
        std::vector<size_t> single_round = { 0, 1, 2, 1 };
        int repeat_count = 10; // 往复运动重复次数

        std::vector<size_t> move_sequence;
        for (int i = 0; i < repeat_count; ++i) {
            move_sequence.insert(move_sequence.end(), single_round.begin(),
                                 single_round.end());
        }

        // 执行运动序列
        int instruction_label = 0;
        bool motion_failed = false;

        // 设置初始标签，用于标记运动序列起点
        runtime->setLabel(instruction_label, "开始");

        for (size_t position_index : move_sequence) {
            // 下发关节运动指令，队列满时重试
            while (true) {
                int result = robot->getMotionControl()->moveJoint(
                    joint_positions[position_index], 0.5, 0.5, 0, 0);

                if (result == AUBO_OK) {
                    // 设置标签用于追踪执行进度
                    runtime->setLabel(
                        ++instruction_label,
                        "位置" + std::to_string(position_index + 1));
                    std::cout << "下发移动到位置" << (position_index + 1)
                              << ", label=" << instruction_label << std::endl;
                    break;
                } else if (result == AUBO_QUEUE_FULL) {
                    // 队列已满，等待后重试
                    std::this_thread::sleep_for(std::chrono::milliseconds(20));
                } else {
                    std::cerr << "moveJoint 失败, 错误码: " << result
                              << std::endl;
                    motion_failed = true;
                    break;
                }
            }
            if (motion_failed) {
                break;
            }
        }

        if (motion_failed) {
            std::cerr << "运动指令下发失败，已下发 " << instruction_label
                      << " 条" << std::endl;
        } else {
            std::cout << "指令下发完成, 共 " << instruction_label << " 条"
                      << std::endl;
        }

        // 等待已下发的运动指令执行完成
        if (instruction_label > 0) {
            // getPlanContext 返回当前执行到的标签号
            // 当 line_number >= 最后一条指令的标签时表示完成
            while (true) {
                // 检查运行时状态，如果已停止则退出等待
                if (runtime->getRuntimeState() != RuntimeState::Running) {
                    std::cerr << "运行时已停止，退出等待" << std::endl;
                    break;
                }
                auto [_, line_number, comment] = runtime->getPlanContext();
                if (line_number >= instruction_label) {
                    std::cout << "运动完成" << std::endl;
                    break;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
        }

        //----------------------------------------------------------------------
        // 第五步：清理并退出
        //----------------------------------------------------------------------

        runtime->abort();
        rpc_client->logout();
        rpc_client->disconnect();
        std::cout << "已退出" << std::endl;

        return 0;

    } catch (const AuboException &e) {
        std::cerr << "SDK 异常: " << e.what() << ", 错误码: " << e.code()
                  << std::endl;
        if (runtime)
            runtime->stop();
        rpc_client->logout();
        rpc_client->disconnect();
        return -1;
    }
}
