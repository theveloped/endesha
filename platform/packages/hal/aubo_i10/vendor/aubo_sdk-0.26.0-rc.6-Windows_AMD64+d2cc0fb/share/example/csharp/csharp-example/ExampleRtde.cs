using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Runtime.InteropServices;

namespace csharp_example
{
    class ExampleRtde
    {
        const int RSERR_SUCC = 0;

        static UInt16 rshd = 0xffff;
        //机械臂IP地址
        const string robotIP = "192.168.124.154";
        //机械臂端口号
        const int rpcServerPort = 30004;
        const int rtdeServerPort = 30010;
        //M_PI
        const double M_PI = 3.14159265358979323846;

        private static cSharpBinging_TypeDef.RobotModeType robot_mode_ = cSharpBinging_TypeDef.RobotModeType.NoController;
        private static cSharpBinging_TypeDef.SafetyModeType safety_mode_ = cSharpBinging_TypeDef.SafetyModeType.Normal;
        private static cSharpBinging_TypeDef.RuntimeState runtime_state_ = cSharpBinging_TypeDef.RuntimeState.Stopped;
        private static double actual_main_voltage_ = 0;
        private static double actual_robot_voltage_ = 0;
        private static double[] actual_TCP_pose_ = new double[6];

        // 用于线程同步的锁对象
        private static readonly object rtdeMtx = new object();
        private static cSharpBinding_RTDE.SubscribeCallbackDelegate subscribedCallback;

        private static void PrintMsgLog(cSharpBinging_TypeDef.RobotMsg msg)
        {
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
                safety_mode_ = cSharpBinding_RTDE.rtde_popSafetyModeType(parser);
                runtime_state_ = cSharpBinding_RTDE.rtde_popRuntimeState(parser);
                actual_main_voltage_ = cSharpBinding_RTDE.rtde_popDouble(parser);
                actual_robot_voltage_ = cSharpBinding_RTDE.rtde_popDouble(parser);
                cSharpBinding_RTDE.rtde_popVectorDouble(parser, actual_TCP_pose_ ,6);
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
        static int exampleSubscribe(IntPtr cli)
        {

            // 设置话题
            string topicNames = "R1_robot_mode,R1_safety_mode,runtime_state,R1_actual_main_voltage,R1_actual_robot_voltage,R1_actual_TCP_pose,R1_message";
            int topic7 = cSharpBinding_RTDE.rtde_setTopic(cli, false, topicNames, 3, 7);
            subscribedCallback = new cSharpBinding_RTDE.SubscribeCallbackDelegate(OnDataReceived);
            cSharpBinding_RTDE.rtde_subscribe(cli, topic7, subscribedCallback);

            return 0;
        }

        static void Main_Rtde(string[] args)
        {

            cSharpBinding_RPC csharpbingding_rpc = new cSharpBinding_RPC();
            //初始化机械臂控制库
            IntPtr rpc_client = cSharpBinding_RPC.rpc_create_client(0);
            Console.Out.WriteLine("rpc_create_client ret={0}   ", rpc_client);
            if (rpc_client == IntPtr.Zero)
            {
                Console.Error.WriteLine("rpc_create_client failed!");
            }

            cSharpBinding_RPC.rpc_connect(rpc_client, robotIP, rpcServerPort);
            cSharpBinding_RPC.rpc_setRequestTimeout(rpc_client, 1000);
            cSharpBinding_RPC.rpc_login(rpc_client, "aubo", "123456");

            IntPtr rtde_client = cSharpBinding_RTDE.rtde_create_client(0);
            Console.Out.WriteLine("rtde_create_client ret={0}   ", rtde_client);
            if (rtde_client == IntPtr.Zero)
            {
                Console.Error.WriteLine("rtde_create_client failed!");
            }

            cSharpBinding_RTDE.rtde_connect(rtde_client, robotIP, rtdeServerPort);
            cSharpBinding_RTDE.rtde_login(rtde_client, "aubo", "123456");

            // RTDE订阅
            exampleSubscribe(rtde_client);

            // 主循环
            while (true)
            {
                Console.WriteLine($"当前模式: {robot_mode_}");
                Console.WriteLine($"安全状态: {safety_mode_}");
                Console.WriteLine($"运行状态: {runtime_state_}");
                Console.WriteLine($"主电压: {actual_main_voltage_:F2} V");
                Console.WriteLine($"机器人电压: {actual_robot_voltage_:F2} V");
                Console.WriteLine("机器人当前位姿: " + string.Join(", ", actual_TCP_pose_.Select(v => v.ToString("F6"))));
                Console.WriteLine(new string('-', 30));

                Thread.Sleep(1000);
            }


            cSharpBinding_RPC.rpc_logout(rpc_client);
            cSharpBinding_RPC.rpc_disconnect(rpc_client);

        }

    }
}
