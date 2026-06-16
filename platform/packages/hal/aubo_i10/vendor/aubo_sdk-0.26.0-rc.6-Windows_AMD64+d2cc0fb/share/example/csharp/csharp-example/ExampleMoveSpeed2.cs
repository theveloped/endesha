using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;

namespace csharp_example
{
    class ExampleSpeedLine
    {
        const int RSERR_SUCC = 0;

        // M_PI
        const double M_PI = 3.14159265358979323846;

        // 机械臂IP地址和端口号（请根据实际情况修改）
        const string robotIP = "127.0.0.1";
        const int rpcServerPort = 30004;
        const int rtdeServerPort = 30010;

        // 坐标系类型枚举
        enum CoordinateSystem
        {
            BASE_COORDINATE_SYSTEM = 1,
            TOOL_COORDINATE_SYSTEM = 2,
            USER_COORDINATE_SYSTEM = 3
        }

        // 动作类型枚举
        enum ActionType
        {
            POSITION_MOVE,    // 位置移动
            ORIENTATION_MOVE, // 姿态旋转
            STOP_MOVE,        // 停止运动
            EXIT_PROGRAM      // 退出程序
        }

        // 用户输入结构
        struct UserInput
        {
            public ActionType actionType;  // 动作类型
            public char axis;              // 坐标轴
            public bool positiveDirection; // 坐标轴方向
        }

        // 辅助函数：打印List<double>
        static void PrintVec(List<double> param, string name)
        {
            Console.Write(name + ": ");
            for (int i = 0; i < param.Count; i++)
            {
                Console.Write(param[i]);
                if (i != param.Count - 1)
                {
                    Console.Write(", ");
                }
            }
            Console.WriteLine();
        }

        private static cSharpBinging_TypeDef.RobotModeType robot_mode_ = cSharpBinging_TypeDef.RobotModeType.NoController;
        // 用于线程同步的锁对象
        private static readonly object rtdeMtx = new object();
        private static cSharpBinding_RTDE.SubscribeCallbackDelegate subscribedCallback;

        private static void PrintMsgLog(cSharpBinging_TypeDef.RobotMsg msg)
        {
            Console.WriteLine("\n");
            Console.WriteLine($"Timestamp: {msg.timestamp}");
            Console.WriteLine($"Level: {msg.level}");
            Console.WriteLine($"Code: {msg.code}");
            Console.WriteLine($"Source: {msg.source}");

            if (msg.args != null && msg.args_count > 0)
            {
                // 解析 args
                string[] args = new string[msg.args_count];
                for (int j = 0; j < msg.args_count; j++)
                {
                    IntPtr argPtr = Marshal.ReadIntPtr(msg.args, j * IntPtr.Size);
                    args[j] = Marshal.PtrToStringAnsi(argPtr);
                }
                Console.WriteLine("Args:");
                if (args != null)
                {
                    foreach (var arg in args)
                    {
                        Console.WriteLine($"  - {arg}");
                    }
                }

            }
            else
            {
                Console.WriteLine("(None)");
            }

            Console.WriteLine(new string('-', 50));
        }

        public static cSharpBinging_TypeDef.RobotMsg[] ReadRobotMsgVector(ref cSharpBinging_TypeDef.RobotMsgVector robot_msg_vec)
        {
            if (robot_msg_vec.data == IntPtr.Zero || robot_msg_vec.size <= 0)
            {
                return Array.Empty<cSharpBinging_TypeDef.RobotMsg>();
            }

            cSharpBinging_TypeDef.RobotMsg[] result = new cSharpBinging_TypeDef.RobotMsg[robot_msg_vec.size];

            for (int i = 0; i < robot_msg_vec.size; ++i)
            {
                IntPtr msgPtr = IntPtr.Add(robot_msg_vec.data, i * Marshal.SizeOf(typeof(cSharpBinging_TypeDef.RobotMsg)));
                cSharpBinging_TypeDef.RobotMsg msg = Marshal.PtrToStructure<cSharpBinging_TypeDef.RobotMsg>(msgPtr);

                result[i] = new cSharpBinging_TypeDef.RobotMsg
                {
                    timestamp = msg.timestamp,
                    level = msg.level,
                    code = msg.code,
                    source = msg.source,
                    args = msg.args,
                    args_count = msg.args_count
                };
            }

            return result;
        }

        private static void OnDataReceived(IntPtr parser)
        {
            lock (rtdeMtx)
            {
                robot_mode_ = cSharpBinding_RTDE.rtde_popRobotModeType(parser);
                OnRobotMsgReceived(parser);
            }
        }

        private static void OnRobotMsgReceived(IntPtr parser)
        {
            cSharpBinging_TypeDef.RobotMsgVector robotMsgVec = new cSharpBinging_TypeDef.RobotMsgVector();

            int result = cSharpBinding_RTDE.rtde_popRobotMsgVector(parser, ref robotMsgVec);
            if (result <= 0)
            {
                Console.WriteLine("No messages received or error occurred.");
                return;
            }

            // 解析消息
            cSharpBinging_TypeDef.RobotMsg[] msgs = ReadRobotMsgVector(ref robotMsgVec);
            foreach (var msg in msgs)
            {
                PrintMsgLog(msg);
            }

        }

        // 选择坐标系对应的参考帧
        static List<double> SelectedCoordinate(CoordinateSystem coordinate, IntPtr cli)
        {
            // 接口调用: 获取机器人的名字
            IntPtr[] robot_names = new IntPtr[10];
            for (int i = 0; i < 10; i++)
            {
                robot_names[i] = Marshal.AllocHGlobal(100);
            }

            int num = cSharpBinding_RPC.rpc_getRobotNames(cli, robot_names);
            if (num <= 0)
            {
                for (int i = 0; i < 10; i++)
                {
                    Marshal.FreeHGlobal(robot_names[i]);
                }
                return new List<double>(new double[6]);
            }
            string robot_name = Marshal.PtrToStringAnsi(robot_names[0]);
            for (int i = 0; i < 10; i++)
            {
                Marshal.FreeHGlobal(robot_names[i]);
            }
            if (string.IsNullOrEmpty(robot_name))
            {
                return new List<double>(new double[6]);
            }

            IntPtr robot_interface = cSharpBinding_RPC.rpc_getRobotInterface(cli, robot_name);
            List<double> frame = new List<double>(new double[6]);

            switch (coordinate)
            {
                case CoordinateSystem.BASE_COORDINATE_SYSTEM:
                    frame = new List<double>(new double[6]);
                    break;
                case CoordinateSystem.TOOL_COORDINATE_SYSTEM:
                    double[] tcpPose = new double[6];
                    IntPtr robot_state = cSharpBinging_RobotInterface.robot_getRobotState(robot_interface);
                    cSharpBinging_RobotState.getTcpPose(robot_state, tcpPose);
                    frame = tcpPose.ToList();
                    frame[0] = 0;
                    frame[1] = 0;
                    frame[2] = 0;
                    break;
                case CoordinateSystem.USER_COORDINATE_SYSTEM:
                    // TCP 在基坐标系下的位姿
                    List<double> coord_p0 = new List<double>(new double[6]);
                    List<double> coord_p1 = new List<double>(new double[6]);
                    List<double> coord_p2 = new List<double>(new double[6]);
                    coord_p0[0] = 0.49946;
                    coord_p0[1] = 0.32869;
                    coord_p0[2] = 0.35522;
                    coord_p0[3] = 2.414;
                    coord_p0[4] = 0.0;
                    coord_p0[5] = 2.357;

                    coord_p1[0] = 0.58381;
                    coord_p1[1] = 0.41325;
                    coord_p1[2] = 0.22122;
                    coord_p1[3] = 2.414;
                    coord_p1[4] = 0.0;
                    coord_p1[5] = 2.357;

                    coord_p2[0] = 0.58826;
                    coord_p2[1] = 0.41772;
                    coord_p2[2] = 0.46730;
                    coord_p2[3] = 2.414;
                    coord_p2[4] = 0.0;
                    coord_p2[5] = 2.357;

                    // 展平二维数组为一维数组（行优先）
                    double[] flat_coords = new double[3 * 6];
                    for (int i = 0; i < 3; i++)
                    {
                        List<double> coord = (i == 0) ? coord_p0 : (i == 1) ? coord_p1 : coord_p2;
                        for (int j = 0; j < 6; j++)
                        {
                            flat_coords[i * 6 + j] = coord[j];
                        }
                    }

                    double[] user_on_base = new double[6];
                    IntPtr mathPtr = cSharpBinding_RPC.rpc_getMath(cli);
                    int ret = cSharpBinding_Math.calibrateCoordinate(mathPtr, flat_coords, 3, 0, user_on_base);
                    if (ret != RSERR_SUCC)
                    {
                        Console.WriteLine("calibrateCoordinate failed, ret = " + ret);
                    }
                    frame = user_on_base.ToList();
                    frame[0] = 0;
                    frame[1] = 0;
                    frame[2] = 0;
                    break;
            }
            return frame;
        }

        // 在不同坐标系下的位置姿态示教
        static void exampleSpeedLine(IntPtr cli)
        {
            int input_coord;
            Console.WriteLine("请选择坐标系：");
            Console.WriteLine("1. 基坐标系");
            Console.WriteLine("2. 工具坐标系");
            Console.WriteLine("3. 用户坐标系");
            Console.Write("请输入选项编号：");
            string input = Console.ReadLine();
            if (!int.TryParse(input, out input_coord))
            {
                Console.WriteLine("输入值无效");
                Console.WriteLine("以下为有效输入值: 1、2、3");
                return;
            }

            if (input_coord != 1 && input_coord != 2 && input_coord != 3)
            {
                Console.WriteLine("输入值无效");
                Console.WriteLine("以下为有效输入值: 1、2、3");
                return;
            }

            CoordinateSystem selected_coord;
            switch (input_coord)
            {
                case 1:
                    selected_coord = CoordinateSystem.BASE_COORDINATE_SYSTEM;
                    break;
                case 2:
                    selected_coord = CoordinateSystem.TOOL_COORDINATE_SYSTEM;
                    break;
                case 3:
                    selected_coord = CoordinateSystem.USER_COORDINATE_SYSTEM;
                    break;
                default:
                    selected_coord = CoordinateSystem.BASE_COORDINATE_SYSTEM; 
                    break;
            }

            // 定义输入字符串和键值映射
            Dictionary<string, UserInput> keymap = new Dictionary<string, UserInput>
            {
                { "x+", new UserInput { actionType = ActionType.POSITION_MOVE, axis = 'x', positiveDirection = true } },
                { "x-", new UserInput { actionType = ActionType.POSITION_MOVE, axis = 'x', positiveDirection = false } },
                { "y+", new UserInput { actionType = ActionType.POSITION_MOVE, axis = 'y', positiveDirection = true } },
                { "y-", new UserInput { actionType = ActionType.POSITION_MOVE, axis = 'y', positiveDirection = false } },
                { "z+", new UserInput { actionType = ActionType.POSITION_MOVE, axis = 'z', positiveDirection = true } },
                { "z-", new UserInput { actionType = ActionType.POSITION_MOVE, axis = 'z', positiveDirection = false } },
                { "rx+", new UserInput { actionType = ActionType.ORIENTATION_MOVE, axis = 'x', positiveDirection = true } },
                { "rx-", new UserInput { actionType = ActionType.ORIENTATION_MOVE, axis = 'x', positiveDirection = false } },
                { "ry+", new UserInput { actionType = ActionType.ORIENTATION_MOVE, axis = 'y', positiveDirection = true } },
                { "ry-", new UserInput { actionType = ActionType.ORIENTATION_MOVE, axis = 'y', positiveDirection = false } },
                { "rz+", new UserInput { actionType = ActionType.ORIENTATION_MOVE, axis = 'z', positiveDirection = true } },
                { "rz-", new UserInput { actionType = ActionType.ORIENTATION_MOVE, axis = 'z', positiveDirection = false } },
                { "s", new UserInput { actionType = ActionType.STOP_MOVE, axis = 'x', positiveDirection = true } },
                { "exit", new UserInput { actionType = ActionType.EXIT_PROGRAM, axis = 'x', positiveDirection = true } }
            };

            // 初始化循环控制变量
            bool continue_loop = true;
            int cnt = 0;
            while (continue_loop)
            {
                Console.WriteLine("请输入机械臂要运动的轴: ");
                // 显示有效输入提示
                if (cnt++ == 0)
                {
                    Console.WriteLine("有效输入值如下: x+、x-、y+、y-、z+、z-、rx+、rx-、ry+、ry-、rz+、rz-、s、exit");
                    Console.WriteLine("x+表示x轴正方向做直线运动，x-表示x轴负方向做直线运动，y+表示y轴正方向做直线运动，y-表示y轴负方向做直线运动，z+表示z轴正方向做直线运动，z-表示z轴负方向做直线运动，rx+表示x轴正方向做旋转运动，rx-表示x轴负方向做旋转运动，ry+表示y轴正方向做旋转运动，ry-表示y轴负方向做旋转运动，rz+表示z轴正方向做旋转运动，rz-表示z轴负方向做旋转运动，s表示停止运动，exit表示退出循环");
                }
                string input_axis = Console.ReadLine();

                // 定义有效的输入值集合
                HashSet<string> validInputs = new HashSet<string>
                {
                    "x+", "x-", "y+", "y-", "z+", "z-", "rx+", "rx-", "ry+", "ry-", "rz+", "rz-", "s", "exit"
                };

                if (!validInputs.Contains(input_axis))
                {
                    Console.WriteLine("输入值无效");
                    Console.WriteLine("以下为有效输入值: x+、x-、y+、y-、z+、z-、rx+、rx-、ry+、ry-、rz+、rz-、s、exit");
                    continue;
                }

                // 接口调用: 获取机器人的名字
                IntPtr[] robot_names = new IntPtr[10];
                for (int i = 0; i < 10; i++)
                {
                    robot_names[i] = Marshal.AllocHGlobal(100);
                }
                int num = cSharpBinding_RPC.rpc_getRobotNames(cli, robot_names);
                if (num <= 0)
                {
                    for (int i = 0; i < 10; i++)
                    {
                        Marshal.FreeHGlobal(robot_names[i]);
                    }
                    Console.WriteLine("获取机器人名字失败");
                    continue;
                }
                string robot_name = Marshal.PtrToStringAnsi(robot_names[0]);
                for (int i = 0; i < 10; i++)
                {
                    Marshal.FreeHGlobal(robot_names[i]);
                }
                if (string.IsNullOrEmpty(robot_name))
                {
                    Console.WriteLine("机器人名字为空");
                    continue;
                }

                IntPtr robot_interface = cSharpBinding_RPC.rpc_getRobotInterface(cli, robot_name);
                IntPtr motion_control = cSharpBinging_RobotInterface.robot_getMotionControl(robot_interface);

                // 接口调用: 设置机械臂的速度比率
                cSharpBinging_MotionControl.setSpeedFraction(motion_control, 0.75);

                UserInput userInput = keymap[input_axis];

                double[] speed = new double[6];
                double tcp_speed = 0.25;
                double a = 1.2;
                tcp_speed = userInput.positiveDirection ? tcp_speed : -tcp_speed;

                List<double> frame = new List<double>();
                if (userInput.actionType == ActionType.EXIT_PROGRAM)
                {
                    continue_loop = false;
                }
                else if (userInput.actionType == ActionType.STOP_MOVE)
                {
                    // 接口调用: 停止位置姿态示教
                    cSharpBinging_MotionControl.stopLine(motion_control, 10, 10);
                }
                else if (userInput.actionType == ActionType.POSITION_MOVE)
                {
                    frame = SelectedCoordinate(selected_coord, cli);

                    // 位置移动
                    switch (userInput.axis)
                    {
                        case 'x':
                            speed[0] = tcp_speed;
                            break;
                        case 'y':
                            speed[1] = tcp_speed;
                            break;
                        case 'z':
                            speed[2] = tcp_speed;
                            break;
                    }

                    double[] frameArray = frame.ToArray();
                    double[] result = new double[6];
                    IntPtr mathPtr = cSharpBinding_RPC.rpc_getMath(cli);
                    cSharpBinding_Math.poseTrans(mathPtr, frameArray, speed, result);
                    result[3] = 0;
                    result[4] = 0;
                    result[5] = 0;

                    cSharpBinging_MotionControl.speedLine(motion_control, result, a, 100);
                }
                else if (userInput.actionType == ActionType.ORIENTATION_MOVE)
                {
                    frame = SelectedCoordinate(selected_coord, cli);
                    // 姿态旋转
                    switch (userInput.axis)
                    {
                        case 'x':
                            speed[0] = tcp_speed;
                            break;
                        case 'y':
                            speed[1] = tcp_speed;
                            break;
                        case 'z':
                            speed[2] = tcp_speed;
                            break;
                    }

                    double[] frameArray = frame.ToArray();
                    double[] result = new double[6];
                    IntPtr mathPtr = cSharpBinding_RPC.rpc_getMath(cli);
                    cSharpBinding_Math.poseTrans(mathPtr, frameArray, speed, result);

                    result[3] = result[0];
                    result[4] = result[1];
                    result[5] = result[2];
                    result[0] = 0;
                    result[1] = 0;
                    result[2] = 0;

                    cSharpBinging_MotionControl.speedLine(motion_control, result, a, 100);
                }
            }
        }

        static void PrintLog(int level, string source, int code, string content)
        {
            string[] level_names = { "Critical", "Error", "Warning", "Info", "Debug", "BackTrace" };
            Console.WriteLine($"[{level_names[level]}] {source} - {code} {content}");
        }


        static void Main(string[] args)
        {
            // 初始化RPC客户端
            IntPtr rpc_client = cSharpBinding_RPC.rpc_create_client(0);
            Console.WriteLine("rpc_create_client ret={0}", rpc_client);
            if (rpc_client == IntPtr.Zero)
            {
                Console.WriteLine("rpc_create_client failed!");
                return;
            }

            cSharpBinding_RPC.rpc_connect(rpc_client, robotIP, rpcServerPort);
            cSharpBinding_RPC.rpc_setRequestTimeout(rpc_client, 1000);
            cSharpBinding_RPC.rpc_login(rpc_client, "aubo", "123456");

            // 初始化RTDE客户端
            IntPtr rtde_client = cSharpBinding_RTDE.rtde_create_client(0);
            Console.WriteLine("rtde_create_client ret={0}", rtde_client);
            if (rtde_client == IntPtr.Zero)
            {
                Console.WriteLine("rtde_create_client failed!");
                cSharpBinding_RPC.rpc_logout(rpc_client);
                cSharpBinding_RPC.rpc_disconnect(rpc_client);
                return;
            }

            cSharpBinding_RTDE.rtde_connect(rtde_client, robotIP, rtdeServerPort);
            cSharpBinding_RTDE.rtde_login(rtde_client, "aubo", "123456");

            // 设置RTDE话题
            string topicNames = "R1_robot_mode,R1_message";
            int topic = cSharpBinding_RTDE.rtde_setTopic(rtde_client, false, topicNames, 1, 0);
            if (topic < 0)
            {
                Console.WriteLine("设置话题失败!");
                cSharpBinding_RTDE.rtde_logout(rtde_client);
                cSharpBinding_RTDE.rtde_disconnect(rtde_client);
                cSharpBinding_RPC.rpc_logout(rpc_client);
                cSharpBinding_RPC.rpc_disconnect(rpc_client);
                return;
            }

            // 订阅话题
            subscribedCallback = new cSharpBinding_RTDE.SubscribeCallbackDelegate(OnDataReceived);
            cSharpBinding_RTDE.rtde_subscribe(rtde_client, topic, subscribedCallback);

            // 执行速度直线示教示例
            exampleSpeedLine(rpc_client);

            cSharpBinding_RTDE.rtde_removeTopic(rtde_client, false, topic);
            cSharpBinding_RTDE.rtde_logout(rtde_client);
            cSharpBinding_RTDE.rtde_disconnect(rtde_client);

            cSharpBinding_RPC.rpc_logout(rpc_client);
            cSharpBinding_RPC.rpc_disconnect(rpc_client);
        }
    }
}
