/** @file  runtime_machine.h
 *  @brief Script interpreter runtime interface,
 *  allows pausing the script interpreter and setting/removing breakpoints.
 */
#ifndef AUBO_SDK_RUNTIME_MACHINE_INTERFACE_H
#define AUBO_SDK_RUNTIME_MACHINE_INTERFACE_H

#include <memory>
#include <aubo/global_config.h>
#include <aubo/type_def.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup RuntimeMachine RuntimeMachine (运行时管理)
 * The RuntimeMachine class
 */
class ARCS_ABI_EXPORT RuntimeMachine
{
public:
    RuntimeMachine();
    virtual ~RuntimeMachine();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 返回 task_id
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.newTask","params":[false],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":26}
     * \endchinese
     * \english
     * Returns the task_id
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.newTask","params":[false],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":26}
     * \endenglish
     */
    int newTask(bool daemon = false);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 删除 task，会终止正在执行的运动
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.deleteTask","params":[26],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Delete a task, which will terminate any ongoing motion.
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.deleteTask","params":[26],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int deleteTask(int tid);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 等待 task 自然结束
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.detachTask","params":[26],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Wait for the task to finish naturally
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.detachTask","params":[26],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int detachTask(int tid);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 判断任务是否存活
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.isTaskAlive","params":[26],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Check if the task is alive
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.isTaskAlive","params":[26],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool isTaskAlive(int tid);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取任务中缓存的指令的数量
     *
     * @param tid
     * @return
     * \endchinese
     * \english
     * Get the number of cached instructions in the task
     *
     * @param tid
     * @return
     * \endenglish
     */
    int getTaskQueueSize(int tid);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 切换当前线程，切换之后接下来的指令将被插入切换后的线程中
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.switchTask","params":[26],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Switch the current thread. After switching, subsequent instructions will
     * be inserted into the switched thread.
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.switchTask","params":[26],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int switchTask(int tid);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 标记记下来的指令的行号和注释
     *
     * @param lineno
     * @param comment
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setLabel","params":[5,"moveJoint"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Mark the line number and comment of the recorded instruction
     *
     * @param lineno
     * @param comment
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setLabel","params":[5,"moveJoint"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setLabel(int lineno, const std::string &comment);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 向aubo_control日志中添加注释
     * 使用 setLabel 替换
     *
     * @param tid 指令的线程ID
     * @param lineno 行号
     * @param comment 注释
     * @return
     *
     * @par Python函数原型
     * setPlanContext(self: pyaubo_sdk.RuntimeMachine, arg0: int, arg1: int,
     * arg2: str) -> int
     *
     * @par Lua函数原型
     * setPlanContext(tid: number, lineno: number, comment: string) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setPlanContext","params":[26,3,"moveJoint"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Add a comment to the aubo_control log
     * Use setLabel instead
     *
     * @param tid Thread ID of the instruction
     * @param lineno Line number
     * @param comment Comment
     * @return
     *
     * @par Python function prototype
     * setPlanContext(self: pyaubo_sdk.RuntimeMachine, arg0: int, arg1: int,
     * arg2: str) -> int
     *
     * @par Lua function prototype
     * setPlanContext(tid: number, lineno: number, comment: string) -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setPlanContext","params":[26,3,"moveJoint"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    ARCS_DEPRECATED int setPlanContext(int tid, int lineno,
                                       const std::string &comment);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 空操作
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.nop","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * No operation
     *
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.nop","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int nop();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取耗时的接口(INST)执行状态, 如 setPersistentParameters
     *
     * @return 指令名字, 执行状态
     * 执行状态: EXECUTING/FINISHED
     *
     * @par Python函数原型
     * getExecutionStatus(self: pyaubo_sdk.RuntimeMachine) -> Tuple[str, str,
     * int]
     *
     * @par Lua函数原型
     * getExecutionStatus() -> string, string, number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getExecutionStatus","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":["confirmSafetyParameters","FINISHED"]}
     *
     * \endchinese
     * \english
     * Get the execution status of time-consuming interfaces (INST), such as
     * setPersistentParameters
     *
     * @return Instruction name, execution status
     * Execution status: EXECUTING/FINISHED
     *
     * @par Python function prototype
     * getExecutionStatus(self: pyaubo_sdk.RuntimeMachine) -> Tuple[str, str,
     * int]
     *
     * @par Lua function prototype
     * getExecutionStatus() -> string, string, number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getExecutionStatus","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":["confirmSafetyParameters","FINISHED"]}
     *
     * \endenglish
     */
    std::tuple<std::string, std::string> getExecutionStatus();
    std::tuple<std::string, std::string, int> getExecutionStatus1();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 跳转到指定行号
     *
     * @param lineno
     * @return
     *
     * @par Python函数原型
     * gotoLine(self: pyaubo_sdk.RuntimeMachine, arg0: int) -> int
     *
     * @par Lua函数原型
     * gotoLine(lineno: number) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.gotoLine","params":[10],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Jump to the specified line number
     *
     * @param lineno
     * @return
     *
     * @par Python function prototype
     * gotoLine(self: pyaubo_sdk.RuntimeMachine, arg0: int) -> int
     *
     * @par Lua function prototype
     * gotoLine(lineno: number) -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.gotoLine","params":[10],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int gotoLine(int lineno);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取当前运行上下文
     *
     * @param tid 任务编号
     * 如果指定(不是-1)，返回对应任务的运行上下文；如果不指定(是-1)，返回正在运行的线程的运行上下文
     *
     * @return
     *
     * @par Python函数原型
     * getPlanContext(self: pyaubo_sdk.RuntimeMachine) -> Tuple[int, int, str]
     *
     * @par Lua函数原型
     * getPlanContext() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getPlanContext","params":[-1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[-1,0,""]}
     *
     * \endchinese
     * \english
     * Get the current runtime context
     *
     * @param tid Task ID
     * If specified (not -1), returns the runtime context of the corresponding
     * task; if not specified (is -1), returns the runtime context of the
     * currently running thread
     *
     * @return
     *
     * @par Python function prototype
     * getPlanContext(self: pyaubo_sdk.RuntimeMachine) -> Tuple[int, int, str]
     *
     * @par Lua function prototype
     * getPlanContext() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getPlanContext","params":[-1],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":[-1,0,""]}
     *
     * \endenglish
     */
    std::tuple<int, int, std::string> getPlanContext(int tid = -1);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取提前运行规划器的上下文信息
     *
     * @param tid 任务编号
     * 如果指定(不是-1)，返回对应任务运行规划器的上下文信息；如果不指定(是-1)，返回正在运行的线程运行规划器的上下文信息
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getAdvancePlanContext","params":[-1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[-1,-1,""]}
     *
     * \endchinese
     * \english
     * Get the context information of the advance planner
     *
     * @param tid Task ID
     * If specified (not -1), returns the context information of the advance
     * planner for the corresponding task; if not specified (is -1), returns the
     * context information of the advance planner for the currently running
     * thread
     *
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getAdvancePlanContext","params":[-1],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":[-1,-1,""]}
     *
     * \endenglish
     */
    std::tuple<int, int, std::string> getAdvancePlanContext(int tid = -1);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取AdvanceRun的程序指针
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getAdvancePtr","params":[-1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endchinese
     * \english
     * Get the program pointer of AdvanceRun
     *
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getAdvancePtr","params":[-1],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endenglish
     */
    int getAdvancePtr(int tid = -1);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取机器人运动的程序指针
     *
     * @param tid 任务编号
     * 如果指定(不是-1)，返回对应任务的程序指针；如果不指定(是-1)，返回正在运行线程的程序指针
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getMainPtr","params":[-1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endchinese
     * \english
     * Get the program pointer of robot motion
     *
     * @param tid Task ID
     * If specified (not -1), returns the program pointer of the corresponding
     * task; if not specified (is -1), returns the program pointer of the
     * currently running thread
     *
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getMainPtr","params":[-1],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endenglish
     */
    int getMainPtr(int tid = -1);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取最近解释过的指令指针
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getInterpPtr","params":[26],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endchinese
     * \english
     * Get the pointer of the most recently interpreted instruction
     *
     * @param tid
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getInterpPtr","params":[26],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":-1}
     *
     * \endenglish
     */
    int getInterpPtr(int tid);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 加载本地工程文件
     * Lua 脚本，只需要给出文件名字，不需要后缀，需要从 ${ARCS_WS}/program
     * 目录中查找
     *
     * @param program
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.loadProgram","params":["demo"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Load a local project file.
     * For Lua scripts, only the file name is required (no extension), and it
     * will be searched in the ${ARCS_WS}/program directory.
     *
     * @param program
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.loadProgram","params":["demo"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int loadProgram(const std::string &program);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 预加载工程文件
     *
     * @param index 0~99 工程索引号
     * @param program 工程名字
     * @return
     * \endchinese
     * \english
     * Preload project file
     *
     * @param index Project index number (0~99)
     * @param program Project name
     * @return
     * \endenglish
     */
    int preloadProgram(int index, const std::string &program);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取预加载工程文件名字，如果没有加载或者超出索引范围则返回空字符串
     *
     * @param index 0~99 工程索引号
     * @return 工程文件名字
     * \endchinese
     * \english
     * Get the name of the preloaded project file. Returns an empty string if
     * not loaded or index is out of range.
     *
     * @param index Project index number (0~99)
     * @return Project file name
     * \endenglish
     */
    std::string getPreloadProgram(int index);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 清除所有已预加载的工程文件
     * 调用此方法将释放所有通过 preloadProgram
     * 预加载的工程索引及其关联的工程名称
     *
     * @return 成功返回0；
     * \endchinese
     * \english
     * Clear all preloaded project files.
     * Calling this method will release all project indices and their associated
     * program names that were previously preloaded via preloadProgram.
     *
     * @return Returns 0 on success;
     * \endenglish
     */
    int clearPreloadPrograms();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 运行已经加载的工程文件
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.runProgram","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Run the already loaded project file
     *
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.runProgram","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int runProgram();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 开始运行时
     *
     * @return
     *
     * @par Python函数原型
     * start(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * start() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.start","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Start the runtime
     *
     * @return
     *
     * @par Python function prototype
     * start(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * start() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.start","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int start();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 停止运行时即脚本运行，无法停止运行时状态为 Stopped 时的机器人运动
     *
     * 如果考虑停止机器人所有运动，可以调用 RuntimeMachine::abort 接口
     *
     * @return
     *
     * @par Python函数原型
     * stop(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * stop() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.stop","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Stop the runtime, i.e., stop script execution. Cannot stop robot motion
     * when the runtime state is Stopped.
     *
     * If you want to stop all robot motion, use the RuntimeMachine::abort
     * interface.
     *
     * @return
     *
     * @par Python function prototype
     * stop(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * stop() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.stop","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int stop();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 终止机器人运行.
     *
     * 如果只是考虑停止运行时，可以调用 RuntimeMachine::stop 接口
     *
     * 如果脚本运行时处于 Running 状态，则终止运行时；如果运行时处于 Stopped
     * 且机器人正在移动，则停止机器人移动；如果此时力控开启了，则机器人停止力控
     *
     * @return
     *
     * @par Python函数原型
     * abort(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * abort() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.abort","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Abort robot operation.
     *
     * If you only want to stop the runtime, you can call the
     * RuntimeMachine::stop interface.
     *
     * If the script runtime is in the Running state, aborts the runtime; if the
     * runtime is Stopped and the robot is moving, stops the robot motion; if
     * force control is enabled, stops force control.
     *
     * @return
     *
     * @par Python function prototype
     * abort(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * abort() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.abort","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int abort();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 暂停解释器
     *
     * @return
     *
     * @par Python函数原型
     * pause(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * pause() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.pause","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Pause the interpreter
     *
     * @return
     *
     * @par Python function prototype
     * pause(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * pause() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.pause","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int pause();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 单步运行
     *
     * @return
     *
     * @par Python函数原型
     * step(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * step() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.step","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Execute a single step
     *
     * @return
     *
     * @par Python function prototype
     * step(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * step() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.step","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int step();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 恢复解释器
     *
     * @return
     *
     * @par Python函数原型
     * resume(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * resume() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.resume","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Resume the interpreter
     *
     * @return
     *
     * @par Python function prototype
     * resume(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * resume() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.resume","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int resume();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 恢复解释器(不检查当前点和暂停点距离)
     *
     * @return
     *
     * @par Python函数原型
     * arbitraryResume(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * arbitraryResume() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.arbitraryResume","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Resume the interpreter
     *
     * @return
     *
     * @par Python function prototype
     * arbitraryResume(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * arbitraryResume() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.arbitraryResume","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int arbitraryResume();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 恢复解释器之前等待恢复前之前的序列完成
     *
     * @param wait
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setResumeWait","params":[true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Wait for the previous sequence to complete before resuming the
     * interpreter
     *
     * @param wait
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setResumeWait","params":[true],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setResumeWait(bool wait);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 进入临界区，abort 命令会被推迟执行，避免临界区内的指令被打断
     *
     * @param timeout 单位秒，范围 0~5 秒，表示 abort
     * 命令最大推迟时间，超过这个时间自动退出临界区并 abort
     * @return
     *
     * @par Python函数原型
     * enterCritical(self: pyaubo_sdk.RuntimeMachine, arg0: double) -> int
     *
     * @par Lua函数原型
     * enterCritical(timeout: number) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.enterCritical","params":[5.0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * The abort command is deferred during critical sections to avoid
     * interrupting internal instructions.
     *
     * @param timeout (seconds, 0~5): max deferral time for abort. Exceeding it
     * forces exit from critical section and triggers abort.
     * @return
     *
     * @par Python function prototype
     * enterCritical(self: pyaubo_sdk.RuntimeMachine, arg0: double) -> int
     *
     * @par Lua function prototype
     * enterCritical(timeout: number) -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.enterCritical","params":[5.0],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int enterCritical(double timeout);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 退出临界区
     *
     * @param
     * @return
     *
     * @par Python函数原型
     * exitCritical(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * exitCritical() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.exitCritical","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Exit the critical section
     *
     * @param
     * @return
     *
     * @par Python function prototype
     * exitCritical(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * exitCritical() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.exitCritical","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int exitCritical();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取规划器的状态
     *
     * @return
     *
     * @par Python函数原型
     * getStatus(self: pyaubo_sdk.RuntimeMachine) ->
     * arcs::common_interface::RuntimeState
     *
     * @par Lua函数原型
     * getStatus() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getStatus","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"Running"}
     *
     * \endchinese
     * \english
     * Get the status of the planner
     *
     * @return
     *
     * @par Python function prototype
     * getStatus(self: pyaubo_sdk.RuntimeMachine) ->
     * arcs::common_interface::RuntimeState
     *
     * @par Lua function prototype
     * getStatus() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getStatus","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":"Running"}
     *
     * \endenglish
     */
    ARCS_DEPRECATED RuntimeState getStatus();
    RuntimeState getRuntimeState();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 设置断点
     *
     * @param lineno
     * @return
     *
     * @par Python函数原型
     * setBreakPoint(self: pyaubo_sdk.RuntimeMachine, arg0: int) -> int
     *
     * @par Lua函数原型
     * setBreakPoint(lineno: number) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setBreakPoint","params":[15],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set a breakpoint
     *
     * @param lineno
     * @return
     *
     * @par Python function prototype
     * setBreakPoint(self: pyaubo_sdk.RuntimeMachine, arg0: int) -> int
     *
     * @par Lua function prototype
     * setBreakPoint(lineno: number) -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.setBreakPoint","params":[15],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setBreakPoint(int lineno);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 移除断点
     *
     * @param lineno
     * @return
     *
     * @par Python函数原型
     * removeBreakPoint(self: pyaubo_sdk.RuntimeMachine, arg0: int) -> int
     *
     * @par Lua函数原型
     * removeBreakPoint(lineno: number) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.removeBreakPoint","params":[15],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Remove a breakpoint
     *
     * @param lineno
     * @return
     *
     * @par Python function prototype
     * removeBreakPoint(self: pyaubo_sdk.RuntimeMachine, arg0: int) -> int
     *
     * @par Lua function prototype
     * removeBreakPoint(lineno: number) -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.removeBreakPoint","params":[15],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int removeBreakPoint(int lineno);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 清除所有断点
     *
     * @return
     *
     * @par Python函数原型
     * clearBreakPoints(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua函数原型
     * clearBreakPoints() -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.clearBreakPoints","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Clear all breakpoints
     *
     * @return
     *
     * @par Python function prototype
     * clearBreakPoints(self: pyaubo_sdk.RuntimeMachine) -> int
     *
     * @par Lua function prototype
     * clearBreakPoints() -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.clearBreakPoints","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int clearBreakPoints();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 定时器开始
     *
     * @param name
     * @return
     *
     * @par Python函数原型
     * timerStart(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua函数原型
     * timerStart(name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerStart","params":["timer"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Start the timer
     *
     * @param name
     * @return
     *
     * @par Python function prototype
     * timerStart(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua function prototype
     * timerStart(name: string) -> nil
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerStart","params":["timer"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int timerStart(const std::string &name);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 定时器结束
     *
     * @param name
     * @return
     *
     * @par Python函数原型
     * timerStop(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua函数原型
     * timerStop(name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerStop","params":["timer"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Stop the timer
     *
     * @param name
     * @return
     *
     * @par Python function prototype
     * timerStop(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua function prototype
     * timerStop(name: string) -> nil
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerStop","params":["timer"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int timerStop(const std::string &name);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 定时器重置
     *
     * @param name
     * @return
     *
     * @par Python函数原型
     * timerReset(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua函数原型
     * timerReset(name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerReset","params":["timer"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Reset the timer
     *
     * @param name
     * @return
     *
     * @par Python function prototype
     * timerReset(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua function prototype
     * timerReset(name: string) -> nil
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerReset","params":["timer"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int timerReset(const std::string &name);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 定时器删除
     *
     * @param name
     * @return
     *
     * @par Python函数原型
     * timerDelete(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua函数原型
     * timerDelete(name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerDelete","params":["timer"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Delete the timer
     *
     * @param name
     * @return
     *
     * @par Python function prototype
     * timerDelete(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> int
     *
     * @par Lua function prototype
     * timerDelete(name: string) -> nil
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.timerDelete","params":["timer"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int timerDelete(const std::string &name);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取定时器数值
     *
     * @param name
     * @return
     *
     * @par Python函数原型
     * getTimer(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> float
     *
     * @par Lua函数原型
     * getTimer(name: string) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getTimer","params":["timer"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":25.409769612}
     *
     * \endchinese
     * \english
     * Get the timer value
     *
     * @param name
     * @return
     *
     * @par Python function prototype
     * getTimer(self: pyaubo_sdk.RuntimeMachine, arg0: str) -> float
     *
     * @par Lua function prototype
     * getTimer(name: string) -> number
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getTimer","params":["timer"],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":25.409769612}
     *
     * \endenglish
     */
    double getTimer(const std::string &name);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 开始配置触发
     *
     * @param distance
     * @param delay
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.triggBegin","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Start configuring trigger
     *
     * @param distance
     * @param delay
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.triggBegin","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int triggBegin(double distance, double delay);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 终止配置触发
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.triggEnd","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * End configuring trigger
     *
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.triggEnd","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int triggEnd();

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 返回自动分配的中断号
     *
     * @param distance
     * @param delay
     * @param intnum
     * @return
     * \endchinese
     * \english
     * Returns the automatically assigned interrupt number
     *
     * @param distance
     * @param delay
     * @param intnum
     * @return
     * \endenglish
     */
    int triggInterrupt(double distance, double delay);

    /**
     * @ingroup RuntimeMachine
     * \chinese
     * 获取所有的中断号列表
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getTriggInterrupts","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endchinese
     * \english
     * Get the list of all interrupt numbers
     *
     * @return
     *
     * @par JSON-RPC Request Example
     * {"jsonrpc":"2.0","method":"RuntimeMachine.getTriggInterrupts","params":[],"id":1}
     *
     * @par JSON-RPC Response Example
     * {"id":1,"jsonrpc":"2.0","result":[]}
     *
     * \endenglish
     */
    std::vector<int> getTriggInterrupts();

protected:
    void *d_;
};

using RuntimeMachinePtr = std::shared_ptr<RuntimeMachine>;

} // namespace common_interface
} // namespace arcs
#endif // AUBO_SDK_RUNTIME_MACHINE_H
