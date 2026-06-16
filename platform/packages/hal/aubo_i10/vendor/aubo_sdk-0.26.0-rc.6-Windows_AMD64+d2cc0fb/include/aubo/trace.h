/** @file  trace.h
 *  \~chinese @brief 向控制器日志系统注入日志方面的接口 \~english @brief Interface for injecting logs into the controller's logging system
 */
#ifndef AUBO_SDK_TRACE_INTERFACE_H
#define AUBO_SDK_TRACE_INTERFACE_H

#include <string>
#include <vector>
#include <memory>
#include <sstream>

#include <aubo/global_config.h>
#include <aubo/type_def.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup Trace Trace (日志与弹窗)
 * \~chinese 提供给控制器扩展程序的日志记录系统  \~english provides a logging system for controller extension programs
 */
class ARCS_ABI_EXPORT Trace
{
public:
    Trace();
    virtual ~Trace();

    /**
     * @ingroup Trace
     * \~chinese 向 aubo_control 日志注入告警信息 \~english Injects alarm information into the aubo_control log
     *
     * TraceLevel: \n
     *  0 - FATAL \n
     *  1 - ERROR \n
     *  2 - WARNING \n
     *  3 - INFO \n
     *  4 - DEBUG \n
     *
     * \~chinese code定义参考 error_stack \~english Code definitions refer to error_stack
     *
     * @param level
     * @param code
     * @param args
     * @return
     *
     * \~chinese @par Python函数原型 \~english @par Python function prototype
     * alarm(self: pyaubo_sdk.Trace, arg0: arcs::common_interface::TraceLevel,
     * arg1: int, arg2: List[str]) -> int
     *
     * \~chinese @par Lua函数原型 \~english @par Lua function prototype
     * alarm(level: number, code: number, args: table) -> nil
     *
     * \~chinese @par JSON-RPC请求示例 \~english @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.Trace.alarm","params":["",1,["Error","Trajectory
     * planning failed!","1"]],"id":1}
     *
     * \~chinese @par JSON-RPC响应示例 \~engish @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     */
    int alarm(TraceLevel level, int code,
              const std::vector<std::string> &args = {});

    /**
     * @ingroup Trace
     * \chinese
     * 打印文本信息到日志中
     *
     * @param msg 文本信息
     * @return
     *
     * @par Python函数原型
     * textmsg(self: pyaubo_sdk.Trace, arg0: str) -> int
     *
     * @par Lua函数原型
     * textmsg(msg: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.Trace.textmsg","params":["test"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * print message into log
     *
     * @param msg message information
     * @return
     *
     * @par Python function prototype
     * textmsg(self: pyaubo_sdk.Trace, arg0: str) -> int
     *
     * @par Lua function prototype
     * textmsg(msg: string) -> nil
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.Trace.textmsg","params":["test"],"id":1}
     *
     * @par JSON-RPC responose example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish 
     */
    int textmsg(const std::string &msg);

    /**
     * \~chinese 通知上位机 \~english Notify the system
     *
     * @param msg
     * @return
     */
    int notify(const std::string &msg);

    /**
     * @ingroup Trace
     * \chinese
     * 向连接的 RTDE 客户端发送弹窗请求
     *
     * @param level
     * @param title
     * @param msg
     * @param mode 模式 \n
     *   0: 普通模式 \n
     *   1: 阻塞模式 \n
     *   2: 输入模式 bool \n
     *   3: 输入模式 int \n
     *   4: 输入模式 double \n
     *   5: 输入模式 string \n
     * @return
     *
     * @par Python函数原型
     * popup(self: pyaubo_sdk.Trace, arg0: arcs::common_interface::TraceLevel,
     * arg1: str, arg2: str, arg3: int) -> int
     *
     * @par Lua函数原型
     * popup(level: number, title: string, msg: string, mode: number) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.Trace.popup","params":["","Error","Trajectory
     * planning failed!",1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Send a popup request to the connected RTDE client
     *
     * @param level
     * @param title
     * @param msg
     * @param mode mode \n
     *   0: normal mode \n
     *   1: blocking mode \n
     *   2: input mode bool \n
     *   3: input mode int \n
     *   4: input mode double \n
     *   5: input mode string \n
     * @return
     *
     * @par Python function prototype
     * popup(self: pyaubo_sdk.Trace, arg0: arcs::common_interface::TraceLevel,
     * arg1: str, arg2: str, arg3: int) -> int
     *
     * @par Lua function prototype
     * popup(level: number, title: string, msg: string, mode: number) -> nil
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.Trace.popup","params":["","Error","Trajectory
     * planning failed!",1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int popup(TraceLevel level, const std::string &title,
              const std::string &msg, int mode);

    /**
     * @ingroup Trace
     * \chinese
     * peek最新的 AlarmInfo(上次一获取之后)
     *
     * last_time设置为0时，可以获取到所有的AlarmInfo
     *
     * @param num
     * @param last_time
     * @return
     *
     * @par Python函数原型
     * peek(self: pyaubo_sdk.Trace, arg0: int, arg1: int) ->
     * List[arcs::common_interface::RobotMsg]
     *
     * @par Lua函数原型
     * peek(num: number, last_time: number) -> table
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.Trace.peek","params":[1,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {{"id":1,"jsonrpc":"2.0","result":[{"args":["RobotModeType.Running"],
     * "code":30045,"level":"INFO","source":"rob1","timestamp":5102883064300}]}
     * \endchinese
     * \english
     * peek the latest AlarmInfo (after the last retrieval)
     *
     * When last_time is set as 0, retrieve all AlarmInfo
     *
     * @param num
     * @param last_time
     * @return
     *
     * @par Python function prototype
     * peek(self: pyaubo_sdk.Trace, arg0: int, arg1: int) ->
     * List[arcs::common_interface::RobotMsg]
     *
     * @par Lua function prototype
     * peek(num: number, last_time: number) -> table
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.Trace.peek","params":[1,0],"id":1}
     *
     * @par JSON-RPC response example
     * {{"id":1,"jsonrpc":"2.0","result":[{"args":["RobotModeType.Running"],
     * "code":30045,"level":"INFO","source":"rob1","timestamp":5102883064300}]}
     * \endenglish
     */
    RobotMsgVector peek(size_t num, uint64_t last_time = 0);

protected:
    void *d_;
};

using TracePtr = std::shared_ptr<Trace>;

} // namespace common_interface
} // namespace arcs
#endif
