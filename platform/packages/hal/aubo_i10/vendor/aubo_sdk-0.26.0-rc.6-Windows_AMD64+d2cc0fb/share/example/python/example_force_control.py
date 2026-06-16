#! /usr/bin/env python
# coding=utf-8

"""
力控示例

步骤:
第一步: 连接RPC服务器、登录
第二步: 开启力传感器标定并开启力控模式
第三步: 退出登陆并断开RPC连接
"""
import pyaubo_sdk
import time
import csv
import math
from typing import List, Sequence, Tuple, Any, Optional

robot_ip = "127.0.0.1"  # 服务器 IP 地址
robot_port = 30004  # 端口号
M_PI = 3.14159265358979323846
robot_rpc_client = pyaubo_sdk.RpcClient()
EMBEDDED: bool = True # 是否使用机械臂内置力传感器
SENSOR_VENDOR: str = "kw_ftsensor"  # 外置力传感器厂商名称

# 阻塞
def wait_arrival(robot_interface):
    max_retry_count = 5
    cnt = 0

    # 接口调用: 获取当前的运动指令 ID
    exec_id = robot_interface.getMotionControl().getExecId()

    # 等待机械臂开始运动
    while exec_id == -1:
        if cnt > max_retry_count:
            return -1
        time.sleep(0.05)
        cnt += 1
        exec_id = robot_interface.getMotionControl().getExecId()

    # 等待机械臂运动完成
    while robot_interface.getMotionControl().getExecId() != -1:
        time.sleep(0.05)

    return 0

def calculate_distance(p1: Sequence[float], p2: Optional[Sequence[float]] = None) -> float:
    """
    计算两点之间的欧氏距离，默认第二点为原点
    """
    if p2 is None:
        p2 = (0.0,) * 6
    if len(p1) != 6 or len(p2) != 6:
        return 0.0
    return math.sqrt(sum((p1[i] - p2[i]) ** 2 for i in range(3)))

def fc_enable(cli: Any)->int:
    # 接口调用：获取机器人的名字
    robot_name = cli.getRobotNames()[0]
    robot = cli.getRobotInterface(robot_name)
    # 开启力控
    ret = robot.getForceControl().fcEnable()
    if ret != 0:
        print("力控开启失败, 错误码: ", ret)
        return -1

def fc_disable(cli: Any)->int:
    # 接口调用：获取机器人的名字
    robot_name = cli.getRobotNames()[0]
    robot = cli.getRobotInterface(robot_name)
    # 关闭力控
    ret = robot.getForceControl().fcDisable()
    if ret != 0:
        print("力控关闭失败, 错误码: ", ret)
        return -1

def tcp_sensor_test(cli: Any, csv_path: str = "force.csv"):
    # 接口调用：获取机器人的名字
    robot_name = cli.getRobotNames()[0]

    # 选择力传感器类型
    if EMBEDDED:
        sensor_pose = [0, 0, 0, 0, 0, 0]
        cli.getRobotInterface(robot_name) \
            .getRobotConfig() \
            .selectTcpForceSensor("embedded")
    else:
        sensor_pose = [0, 0, 0.047, 0, 0, 0]
        cli.getRobotInterface(robot_name) \
            .getRobotConfig() \
            .selectTcpForceSensor(SENSOR_VENDOR)

    # 写入 CSV
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)

        # 表头
        writer.writerow(["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"])
        f.flush()

        while True:
            sensor_data = cli.getRobotInterface(robot_name) \
                             .getRobotState() \
                             .getTcpForceSensors()

            print("--------------------------------------")
            for i, v in enumerate(sensor_data):
                print(f"获取TCP力传感器读数: {i + 1}: {v}")
            print("--------------------------------------")

            writer.writerow(list(sensor_data))
            f.flush()

            time.sleep(0.005)

# --------- 力传感器标定 ----------
def tcp_sensor_calibration(cli: Any, joints: List[List[float]]) -> Tuple[List[float], List[float], float]:
    robot_name = cli.getRobotNames()[0]
    robot_interface = cli.getRobotInterface(robot_name)

    print("goto p0")
    robot_interface.getMotionControl().moveJoint(
        joints[0],
        10.0 * (math.pi / 180.0),
        5.0 * (math.pi / 180.0),
        0, 0
    )
    wait_arrival(robot_interface)
    time.sleep(1.0)

    q1 = robot_interface.getRobotState().getJointPositions()
    tcp_force1 = robot_interface.getRobotState().getTcpForceSensors()

    print("goto p1")
    robot_interface.getMotionControl().moveJoint(
        joints[1],
        20.0 * (math.pi / 180.0),
        10.0 * (math.pi / 180.0),
        0, 0
    )
    wait_arrival(robot_interface)
    time.sleep(1.0)

    q2 = robot_interface.getRobotState().getJointPositions()
    tcp_force2 = robot_interface.getRobotState().getTcpForceSensors()

    print("goto p2")
    robot_interface.getMotionControl().moveJoint(
        joints[2],
        20.0 * (math.pi / 180.0),
        10.0 * (math.pi / 180.0),
        0, 0
    )
    wait_arrival(robot_interface)
    time.sleep(1.0)

    q3 = robot_interface.getRobotState().getJointPositions()
    tcp_force3 = robot_interface.getRobotState().getTcpForceSensors()

    pose1 = robot_interface.getRobotAlgorithm().forwardKinematics(q1)
    pose2 = robot_interface.getRobotAlgorithm().forwardKinematics(q2)
    pose3 = robot_interface.getRobotAlgorithm().forwardKinematics(q3)

    calib_forces = [list(tcp_force1), list(tcp_force2), list(tcp_force3)]
    calib_poses = [list(pose1[0]), list(pose2[0]), list(pose3[0])]

    # 三点标定接口
    result = robot_interface.getRobotAlgorithm().calibrateTcpForceSensor(calib_forces, calib_poses)

    return result


# --------- 力控模式开启示例 ----------
def example_force_control(cli: Any) -> None:
    robot_name = cli.getRobotNames()[0]
    robot_interface = cli.getRobotInterface(robot_name)

    # 选择传感器类型 + 传感器安装位姿
    if EMBEDDED:
        sensor_pose = [0.0, 0.0, 0.0,   0.0, 0.0, 0.0]
        robot_interface.getRobotConfig().selectTcpForceSensor("embedded")
    else:
        sensor_pose = [0.0, 0.0, 0.047, 0.0, 0.0, 0.0]
        robot_interface.getRobotConfig().selectTcpForceSensor(SENSOR_VENDOR)

    robot_interface.getRobotConfig().setTcpForceSensorPose(sensor_pose)

    # 设置TCP偏移（这里与C++一致：tcp_pose = sensor_pose）
    tcp_pose = list(sensor_pose)
    robot_interface.getRobotConfig().setTcpOffset(tcp_pose)

    # 负载辨识参考点（关节角度单位：rad）
    joint1 = [-0.261799, 0.261799, 1.309,    1.0472,   1.39626, 0.0]
    joint2 = [-0.628319, 0.471239, 1.65806, -0.471239, 0.0,     0.0]
    joint3 = [-0.628319, 0.366519, 1.74533, -0.10472,  1.5708,  0.0]

    # 标定
    calib_result = tcp_sensor_calibration(cli, [joint1, joint2, joint3])
    force_offset = calib_result[0]
    com = calib_result[1]
    mass = calib_result[2]

    print("force_offset:", force_offset)
    print("com:", com)
    print("mass:", mass)

    if calculate_distance(force_offset) < 1e-4:
        print("标定错误，请检查传感器数据!")
        raise RuntimeError("TCP force sensor calibration failed")

    time.sleep(1.0)

    print("go to start_joint")
    start_joint = [
        0.0 / 180.0 * math.pi,
        16.41 / 180.0 * math.pi,
        76.36 / 180.0 * math.pi,
        7.87 / 180.0 * math.pi,
        90.21 / 180.0 * math.pi,
        0.0 / 180.0 * math.pi,
    ]
    robot_interface.getMotionControl().moveJoint(
        start_joint,
        10.0 * (math.pi / 180.0),
        5.0 * (math.pi / 180.0),
        0, 0
    )
    wait_arrival(robot_interface)
    time.sleep(1.0)

    # 根据标定结果设置负载 + 力传感器偏移
    robot_interface.getRobotConfig().setPayload(
        mass, com,
        [0.0], [0.0]
    )
    robot_interface.getRobotConfig().setTcpForceOffset(force_offset)

    # 力控动力学模型（导纳）
    admittance_m = [10.0, 10.0, 10.0, 2.0, 2.0, 2.0]
    admittance_d = [200.0, 200.0, 200.0, 20.0, 20.0, 20.0]
    admittance_k = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    robot_interface.getForceControl().setDynamicModel(admittance_m, admittance_d, admittance_k)

    # 目标力控参数
    compliance = [True, True, True, True, True, True]
    target_wrench = [0.0] * 6
    speed_limits = [2.0] * 6

    # TaskFrameType::NONE
    task_frame = pyaubo_sdk.TaskFrameType.NONE

    robot_interface.getForceControl().setTargetForce(
        [0.0] * 6, compliance, target_wrench, speed_limits, task_frame
    )

    print("Press 's'/'q' to enable/disable force control mode.")
    while True:
        key = input("Please input your choose: ").strip()
        if not key:
            continue
        key = key[0]

        if key == "s":
            if robot_interface.getForceControl().isFcEnabled():
                print("The robot has already been force control mode. Can't enable.")
            else:
                fc_enable(cli)
                print("Enter force control mode")

        elif key == "q":
            if not robot_interface.getForceControl().isFcEnabled():
                print("The robot has already quit force control mode. Can't disable.")
            else:
                fc_disable(cli)
                print("Quit force control mode")

        else:
            print("Please input 's' or 'q'.")

if __name__ == '__main__':
    robot_rpc_client.setRequestTimeout(1000)
    robot_rpc_client.connect(robot_ip, robot_port)  # 接口调用: 连接到 RPC 服务
    if robot_rpc_client.hasConnected():
        print("Robot rcp_client connected successfully!")
        robot_rpc_client.login("aubo", "123456")  # 接口调用: 机械臂登录
        if robot_rpc_client.hasLogined():
            print("Robot rcp_client logined successfully!")
            # 使能和退出力控
            example_force_control(robot_rpc_client)
            # 读取力传感器数据并保存到force.csv文件中
            # tcp_sensor_test(robot_rpc_client, "force.csv")