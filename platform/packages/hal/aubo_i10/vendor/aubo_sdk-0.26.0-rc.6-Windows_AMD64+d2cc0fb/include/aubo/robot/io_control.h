/** @file  io_control.h
 *  @brief IO控制接口
 */
#ifndef AUBO_SDK_IO_CONTROL_INTERFACE_H
#define AUBO_SDK_IO_CONTROL_INTERFACE_H

#include <vector>
#include <thread>
#include <string>

#include <aubo/global_config.h>
#include <aubo/type_def.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup IoControl IoControl (IO输入输出控制)
 * @ingroup RobotInterface
 * \chinese
 * IoControl类提供了一系列的接口对机器人标配的一些数字、模拟IO进行配置，输出状态设置、读取
 *
 * 1. 获取各种IO的数量 \n
 * 2. 配置IO的输入输出功能 \n
 * 3. 可配置IO的配置 \n
 * 4. 模拟IO的输入输出范围设置、读取
 *
 * 标准数字输入输出：控制柜IO面板上的标准IO \n
 * 工具端数字输入输出：通过工具末端航插暴露的数字IO \n
 * 可配置输入输出：可以配置为安全IO或者普通数字IO \n
 * \endchinese
 * \english
 * The IoControl class provides a series of interfaces for configuring and
 * reading the robot's standard digital and analog IO, as well as setting output
 * states.
 *
 * 1. Get the number of various IOs \n
 * 2. Configure IO input/output functions \n
 * 3. Configuration of configurable IOs \n
 * 4. Set and read the input/output range of analog IOs
 *
 * Standard digital input/output: Standard IOs on the control cabinet IO panel
 * \n Tool digital input/output: Digital IOs exposed via the tool-end connector
 * \n Configurable input/output: Can be configured as safety IO or general
 * digital IO \n \endenglish
 */
class ARCS_ABI_EXPORT IoControl
{
public:
    IoControl();
    virtual ~IoControl();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准数字输入数量
     *
     * @return 标准数字输入数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardDigitalInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStandardDigitalInputNum() -> number
     *
     * @par Lua示例
     * num = getStandardDigitalInputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":16}
     *
     * \endchinese
     * \english
     * Get the number of standard digital inputs.
     *
     * @return Number of standard digital inputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardDigitalInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStandardDigitalInputNum() -> number
     *
     * @par Lua example
     * num = getStandardDigitalInputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":16}
     *
     * \endenglish
     */
    int getStandardDigitalInputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端数字IO数量(包括数字输入和数字输出)
     *
     * @return 工具端数字IO数量(包括数字输入和数字输出)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolDigitalInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getToolDigitalInputNum() -> number
     *
     * @par Lua示例
     * num = getStandardDigitalInputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":4}
     *
     * \endchinese
     * \english
     * Get the number of tool digital IOs (including digital inputs and
     * outputs).
     *
     * @return Number of tool digital IOs (including digital inputs and
     * outputs).
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolDigitalInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getToolDigitalInputNum() -> number
     *
     * @par Lua example
     * num = getStandardDigitalInputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":4}
     *
     * \endenglish
     */
    int getToolDigitalInputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取可配置数字输入数量
     *
     * @return 可配置数字输入数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConfigurableDigitalInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getConfigurableDigitalInputNum() -> number
     *
     * @par Lua示例
     * num = getConfigurableDigitalInputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":16}
     *
     * \endchinese
     * \english
     * Get the number of configurable digital inputs.
     *
     * @return Number of configurable digital inputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConfigurableDigitalInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getConfigurableDigitalInputNum() -> number
     *
     * @par Lua example
     * num = getConfigurableDigitalInputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":16}
     *
     * \endenglish
     */
    int getConfigurableDigitalInputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准数字输出数量
     *
     * @return 标准数字输出数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardDigitalOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStandardDigitalOutputNum() -> number
     *
     * @par Lua示例
     * num = getStandardDigitalOutputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":8}
     *
     * \endchinese
     * \english
     * Get the number of standard digital outputs.
     *
     * @return Number of standard digital outputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardDigitalOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStandardDigitalOutputNum() -> number
     *
     * @par Lua example
     * num = getStandardDigitalOutputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":8}
     *
     * \endenglish
     */
    int getStandardDigitalOutputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端数字IO数量(包括数字输入和数字输出)
     *
     * @return 工具端数字IO数量(包括数字输入和数字输出)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolDigitalOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getToolDigitalOutputNum() -> number
     *
     * @par Lua示例
     * num = getToolDigitalOutputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":4}
     *
     * \endchinese
     * \english
     * Get the number of tool digital IOs (including digital inputs and
     * outputs).
     *
     * @return Number of tool digital IOs (including digital inputs and
     * outputs).
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolDigitalOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getToolDigitalOutputNum() -> number
     *
     * @par Lua example
     * num = getToolDigitalOutputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":4}
     *
     * \endenglish
     */
    int getToolDigitalOutputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 设置指定的工具端数字IO为输入或输出
     *
     * 工具端数字IO比较特殊，IO可以配置为输入或者输出
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param input: 表示指定IO是否为输入。
     * input 为true时，设置指定IO为输入，否则为输出
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolIoInput(self: pyaubo_sdk.IoControl, arg0: int, arg1: bool) -> int
     *
     * @par Lua函数原型
     * setToolIoInput(index: number, input: boolean) -> nil
     *
     * @par Lua示例
     * setToolIoInput(0,true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolIoInput","params":[0,true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the specified tool digital IO as input or output.
     *
     * Tool digital IOs are special and can be configured as input or output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param input: Indicates whether the specified IO is input.
     * If input is true, set the IO as input; otherwise, set as output.
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolIoInput(self: pyaubo_sdk.IoControl, arg0: int, arg1: bool) -> int
     *
     * @par Lua function prototype
     * setToolIoInput(index: number, input: boolean) -> nil
     *
     * @par Lua example
     * setToolIoInput(0,true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolIoInput","params":[0,true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolIoInput(int index, bool input);

    /**
     * @ingroup IoControl
     * \chinese
     * 判断指定的工具端数字IO类型是否为输入
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 当指定的IO为输入时返回 true, 否则为 false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * isToolIoInput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * isToolIoInput(index: number) -> boolean
     *
     * @par Lua示例
     * status = isToolIoInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.isToolIoInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Determine whether the specified tool digital IO is configured as input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Returns true if the specified IO is input, otherwise false.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * isToolIoInput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua function prototype
     * isToolIoInput(index: number) -> boolean
     *
     * @par Lua example
     * status = isToolIoInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.isToolIoInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool isToolIoInput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取可配置数字输出数量
     *
     * @return 可配置数字输出数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConfigurableDigitalOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getConfigurableDigitalOutputNum() -> number
     *
     * @par Lua示例
     * num = getConfigurableDigitalOutputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":16}
     *
     * \endchinese
     * \english
     * Get the number of configurable digital outputs.
     *
     * @return Number of configurable digital outputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConfigurableDigitalOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getConfigurableDigitalOutputNum() -> number
     *
     * @par Lua example
     * num = getConfigurableDigitalOutputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":16}
     *
     * \endenglish
     */
    int getConfigurableDigitalOutputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准模拟输入数量
     *
     * @return 标准模拟输入数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardAnalogInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStandardAnalogInputNum() -> number
     *
     * @par Lua示例
     * num = getStandardAnalogInputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogInputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":2}
     *
     * \endchinese
     * \english
     * Get the number of standard analog inputs.
     *
     * @return Number of standard analog inputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardAnalogInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStandardAnalogInputNum() -> number
     *
     * @par Lua example
     * num = getStandardAnalogInputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogInputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":2}
     *
     * \endenglish
     */
    int getStandardAnalogInputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端模拟输入数量
     *
     * @return 工具端模拟输入数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolAnalogInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getToolAnalogInputNum() -> number
     *
     * @par Lua示例
     * num = getToolAnalogInputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogInputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":2}
     *
     * \endchinese
     * \english
     * Get the number of tool analog inputs.
     *
     * @return Number of tool analog inputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolAnalogInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getToolAnalogInputNum() -> number
     *
     * @par Lua example
     * num = getToolAnalogInputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogInputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":2}
     *
     * \endenglish
     */
    int getToolAnalogInputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准模拟输出数量
     *
     * @return 标准模拟输出数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardAnalogOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStandardAnalogOutputNum() -> number
     *
     * @par Lua示例
     * num = getStandardAnalogOutputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":2}
     *
     * \endchinese
     * \english
     * Get the number of standard analog outputs.
     *
     * @return Number of standard analog outputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardAnalogOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStandardAnalogOutputNum() -> number
     *
     * @par Lua example
     * num = getStandardAnalogOutputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":2}
     *
     * \endenglish
     */
    int getStandardAnalogOutputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端模拟输出数量
     *
     * @return 工具端模拟输出数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolAnalogOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getToolAnalogOutputNum() -> number
     *
     * @par Lua示例
     * num = getToolAnalogOutputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the number of tool analog outputs.
     *
     * @return Number of tool analog outputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolAnalogOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getToolAnalogOutputNum() -> number
     *
     * @par Lua example
     * num = getToolAnalogOutputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getToolAnalogOutputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 设置所有数字输入动作为无触发
     *
     * @note
     * 当输入动作为无触发时，用户设置数字输入值为高电平，不会触发机器人发生动作
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setDigitalInputActionDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * setDigitalInputActionDefault() -> nil
     *
     * @par Lua示例
     * setDigitalInputActionDefault()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setDigitalInputActionDefault","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set all digital input actions to no trigger.
     *
     * @note
     * When the input action is set to no trigger, setting the digital input
     * value to high will not trigger any robot action.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setDigitalInputActionDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * setDigitalInputActionDefault() -> nil
     *
     * @par Lua example
     * setDigitalInputActionDefault()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setDigitalInputActionDefault","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setDigitalInputActionDefault();

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准数字输入触发动作
     *
     * @note
     * 当给输入设置为无触发动作(StandardInputAction::Default)时，
     * 用户设置数字输入值为高电平，不会触发机器人发生动作。\n
     * 当给输入设置触发动作时，用户设置数字输入值为高电平，会触发机器人执行相应的动作。\n
     * 例如，当设置DI0的触发动作为拖动示教(StandardInputAction::Handguide)时，
     * 用户设置DI0为高电平，机器人会进入拖动示教。
     * 设置DI0为低电平，机器人会退出拖动示教。
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param action: 触发动作
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardInputAction) -> int
     *
     * @par Lua函数原型
     * setStandardDigitalInputAction(index: number, action: number) -> nil
     *
     * @par Lua示例
     * setStandardDigitalInputAction(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalInputAction","params":[0,"Handguide"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the trigger action for standard digital input.
     *
     * @note
     * When the input is set to no trigger action
     * (StandardInputAction::Default), setting the digital input value to high
     * will not trigger any robot action.\n When a trigger action is set,
     * setting the digital input value to high will trigger the corresponding
     * robot action.\n For example, if DI0 is set to trigger Handguide
     * (StandardInputAction::Handguide), setting DI0 to high will enable
     * hand-guiding mode. Setting DI0 to low will exit hand-guiding mode.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param action: Trigger action
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardInputAction) -> int
     *
     * @par Lua function prototype
     * setStandardDigitalInputAction(index: number, action: number) -> nil
     *
     * @par Lua example
     * setStandardDigitalInputAction(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalInputAction","params":[0,"Handguide"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardDigitalInputAction(int index, StandardInputAction action);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具数字输入触发动作
     *
     * @note
     * 当给输入设置为无触发动作(StandardInputAction::Default)时，
     * 用户设置工具数字输入值为高电平，不会触发机器人发生动作。\n
     * 当给输入设置触发动作时，用户设置工具数字输入值为高电平，会触发机器人执行相应的动作。\n
     * 例如，当设置TOOL_IO[0]的类型为输入而且触发动作为拖动示教(StandardInputAction::Handguide)时，
     * 用户设置TOOL_IO[0]为高电平，机器人会进入拖动示教。
     * 设置TOOL_IO[0]为低电平，机器人会退出拖动示教。
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param action: 触发动作
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * arcs::common_interface::StandardInputAction) -> int
     *
     * @par Lua函数原型
     * setToolDigitalInputAction(index: number, action: number) -> nil
     *
     * @par Lua示例
     * setToolDigitalInputAction(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalInputAction","params":[0,"Handguide"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the trigger action for tool digital input.
     *
     * @note
     * When the input is set to no trigger action
     * (StandardInputAction::Default), setting the tool digital input value to
     * high will not trigger any robot action.\n When a trigger action is set,
     * setting the tool digital input value to high will trigger the
     * corresponding robot action.\n For example, if TOOL_IO[0] is set as input
     * and its trigger action is Handguide (StandardInputAction::Handguide),
     * setting TOOL_IO[0] to high will enable hand-guiding mode.
     * Setting TOOL_IO[0] to low will exit hand-guiding mode.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param action: Trigger action
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * arcs::common_interface::StandardInputAction) -> int
     *
     * @par Lua function prototype
     * setToolDigitalInputAction(index: number, action: number) -> nil
     *
     * @par Lua example
     * setToolDigitalInputAction(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalInputAction","params":[0,"Handguide"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolDigitalInputAction(int index, StandardInputAction action);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置可配置数字输入触发动作
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param action: 触发动作
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @note 需要将可配置输入的安全输入动作设置为
     * SafetyInputAction::Unassigned时这个函数的配置才会生效
     *
     * @par Python函数原型
     * setConfigurableDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardInputAction) -> int
     *
     * @par Lua函数原型
     * setConfigurableDigitalInputAction(index: number, action: number) -> nil
     *
     * @par Lua示例
     * setConfigurableDigitalInputAction(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalInputAction","params":[0,"Handguide"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the trigger action for configurable digital input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param action: Trigger action
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @note This function takes effect only when the safety input action of the
     * configurable input is set to SafetyInputAction::Unassigned.
     *
     * @par Python function prototype
     * setConfigurableDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardInputAction) -> int
     *
     * @par Lua function prototype
     * setConfigurableDigitalInputAction(index: number, action: number) -> nil
     *
     * @par Lua example
     * setConfigurableDigitalInputAction(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalInputAction","params":[0,"Handguide"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConfigurableDigitalInputAction(int index,
                                          StandardInputAction action);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准数字输入触发动作
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 标准数字输入触发动作
     *
     * @par Python函数原型
     * getStandardDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardInputAction
     *
     * @par Lua函数原型
     * getStandardDigitalInputAction(index: number) -> number
     *
     * @par Lua示例
     * num = getStandardDigitalInputAction(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInputAction","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"Default"}
     *
     * \endchinese
     * \english
     * Get the trigger action for standard digital input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Standard digital input trigger action
     *
     * @par Python function prototype
     * getStandardDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardInputAction
     *
     * @par Lua function prototype
     * getStandardDigitalInputAction(index: number) -> number
     *
     * @par Lua example
     * num = getStandardDigitalInputAction(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInputAction","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"Default"}
     *
     * \endenglish
     */
    StandardInputAction getStandardDigitalInputAction(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端数字输入触发动作
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 工具端数字输入触发动作
     *
     * @par Python函数原型
     * getToolDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardInputAction
     *
     * @par Lua函数原型
     * getToolDigitalInputAction(index: number) -> number
     *
     * @par Lua示例
     * getToolDigitalInputAction(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInputAction","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"Default"}
     *
     * \endchinese
     * \english
     * Get the trigger action for tool digital input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Tool digital input trigger action
     *
     * @par Python function prototype
     * getToolDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardInputAction
     *
     * @par Lua function prototype
     * getToolDigitalInputAction(index: number) -> number
     *
     * @par Lua example
     * getToolDigitalInputAction(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInputAction","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"Default"}
     *
     * \endenglish
     */
    StandardInputAction getToolDigitalInputAction(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取可配置数字输入的输入触发动作
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 返回输入触发动作
     *
     * @par Python函数原型
     * getConfigurableDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int)
     * -> arcs::common_interface::StandardInputAction
     *
     * @par Lua函数原型
     * getConfigurableDigitalInputAction(index: number) -> number
     *
     * @par Lua示例
     * num = getConfigurableDigitalInputAction(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInputAction","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"Default"}
     *
     * \endchinese
     * \english
     * Get the trigger action for configurable digital input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Returns the input trigger action.
     *
     * @par Python function prototype
     * getConfigurableDigitalInputAction(self: pyaubo_sdk.IoControl, arg0: int)
     * -> arcs::common_interface::StandardInputAction
     *
     * @par Lua function prototype
     * getConfigurableDigitalInputAction(index: number) -> number
     *
     * @par Lua example
     * num = getConfigurableDigitalInputAction(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInputAction","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"Default"}
     *
     * \endenglish
     */
    StandardInputAction getConfigurableDigitalInputAction(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置所有数字输出状态选择为无
     *
     * @note
     * 当给输出状态设置为无(StandardOutputRunState::None)时，
     * 用户可以设置数字输出值。\n
     * 当给输出设置状态时，用户不可设置数字输出值，控制器会自动设置数字输出值。\n
     * 例如，当设置DO0的输出状态为高电平指示正在拖动示教(StandardOutputRunState::Handguiding)时，
     * 机器人进入拖动示教，DO0会自动变为高电平。
     * 机器人退出拖动示教，DO0会自动变为低电平。
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setDigitalOutputRunstateDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * setDigitalOutputRunstateDefault() -> nil
     *
     * @par Lua示例
     * setDigitalOutputRunstateDefault()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setDigitalOutputRunstateDefault","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set all digital output runstates to None.
     *
     * @note
     * When the output runstate is set to None (StandardOutputRunState::None),
     * users can set the digital output value.\n
     * When the output runstate is set, users cannot set the digital output
     * value, and the controller will set it automatically.\n For example, when
     * DO0's output runstate is set to indicate hand-guiding
     * (StandardOutputRunState::Handguiding), the robot enters hand-guiding mode
     * and DO0 will automatically become high. When the robot exits
     * hand-guiding, DO0 will automatically become low.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setDigitalOutputRunstateDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * setDigitalOutputRunstateDefault() -> nil
     *
     * @par Lua example
     * setDigitalOutputRunstateDefault()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setDigitalOutputRunstateDefault","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setDigitalOutputRunstateDefault();

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准数字输出状态选择
     *
     * @note
     * 当给输出状态设置为无(StandardOutputRunState::None)时，
     * 用户可以设置数字输出值。\n
     * 当给输出设置状态时，用户不可设置数字输出值，控制器会自动设置数字输出值。\n
     * 例如，当设置DO0的输出状态为高电平指示正在拖动示教(StandardOutputRunState::Handguiding)时，
     * 机器人进入拖动示教，DO0会自动变为高电平。
     * 机器人退出拖动示教，DO0会自动变为低电平。
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param runstate: 输出状态选择
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua函数原型
     * setStandardDigitalOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua示例
     * setStandardDigitalOutputRunstate(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutputRunstate","params":[0,"PowerOn"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the runstate for standard digital output.
     *
     * @note
     * When the output runstate is set to None (StandardOutputRunState::None),
     * users can set the digital output value.\n
     * When the output runstate is set, users cannot set the digital output
     * value, and the controller will set it automatically.\n For example, when
     * DO0's output runstate is set to indicate hand-guiding
     * (StandardOutputRunState::Handguiding), the robot enters hand-guiding mode
     * and DO0 will automatically become high. When the robot exits
     * hand-guiding, DO0 will automatically become low.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param runstate: Output runstate selection
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua function prototype
     * setStandardDigitalOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua example
     * setStandardDigitalOutputRunstate(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutputRunstate","params":[0,"PowerOn"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardDigitalOutputRunstate(int index,
                                         StandardOutputRunState runstate);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端数字输出状态选择
     *
     * @note
     * 当给输出状态设置为无(StandardOutputRunState::None)时，
     * 用户可以设置数字输出值。\n
     * 当给输出设置状态时，用户不可设置数字输出值，控制器会自动设置数字输出值。\n
     * 例如，当设置TOOL_IO[0]类型为输出且输出状态为高电平指示正在拖动示教(StandardOutputRunState::Handguiding)时，
     * 机器人进入拖动示教，TOOL_IO[0]会自动变为高电平。
     * 机器人退出拖动示教，TOOL_IO[0]会自动变为低电平。
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param runstate: 输出状态选择
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua函数原型
     * setToolDigitalOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua示例
     * setToolDigitalOutputRunstate(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the runstate for tool digital output.
     *
     * @note
     * When the output runstate is set to None (StandardOutputRunState::None),
     * users can set the digital output value.\n
     * When the output runstate is set, users cannot set the digital output
     * value, and the controller will set it automatically.\n For example, when
     * TOOL_IO[0] is set as output and its runstate is set to indicate
     * hand-guiding (StandardOutputRunState::Handguiding), the robot enters
     * hand-guiding mode and TOOL_IO[0] will automatically become high. When the
     * robot exits hand-guiding, TOOL_IO[0] will automatically become low.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param runstate: Output runstate selection
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua function prototype
     * setToolDigitalOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua example
     * setToolDigitalOutputRunstate(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolDigitalOutputRunstate(int index,
                                     StandardOutputRunState runstate);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置可配置数字输出状态选择
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param runstate: 输出状态选择
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConfigurableDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0:
     * int, arg1: arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua函数原型
     * setConfigurableDigitalOutputRunstate(index: number, runstate: number) ->
     * nil
     *
     * @par Lua示例
     * setConfigurableDigitalOutputRunstate(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the runstate for configurable digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param runstate: Output runstate selection
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConfigurableDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0:
     * int, arg1: arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua function prototype
     * setConfigurableDigitalOutputRunstate(index: number, runstate: number) ->
     * nil
     *
     * @par Lua example
     * setConfigurableDigitalOutputRunstate(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConfigurableDigitalOutputRunstate(int index,
                                             StandardOutputRunState runstate);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置数字输出的状态选择，并支持基于路点/平面/障碍物的条件阈值判断。
     *
     * 详细说明：当需要根据机器人是否到达某个路点或与某个平面/障碍物的距离来触发数字输出时，
     * 可通过本接口指定条件对象及阈值。在条件满足时会将指定的数字输出设置为对应的运行状态。
     *
     * @param io_type
     * 数字输出类型（0=标准数字输出、1=工具数字输出、2=可配置数字输出），用整数表示
     * @param index 输出口的索引，管脚编号从0开始
     * @param runstate 输出动作状态
     * @param object_type
     * 条件对象类型：0=无条件，1=路点(Waypoint)，2=平面(Plane)，3=障碍物(Obstacle)
     * @param object_name 条件对象的名称
     * @param threshold 判断阈值：对路点为角度(度)，对平面/障碍物为距离(毫米)
     *
     * @return 返回操作结果码：0 表示成功，非0 表示失败
     *
     * @par Python函数原型
     * setDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int, arg2: arcs::common_interface::StandardOutputRunState, arg3: int=0,
     * arg4: str="", arg5: int=0) -> int
     *
     * @par Lua函数原型
     * setDigitalOutputRunstate(io_type: number, index: number, runstate:
     * number, object_type: number=0, object_name: string="", threshold:
     * number=0) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setDigitalOutputRunstate","params":[1,0,"WaypointArrived",1,"P1",3],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Set digital output runstate with optional condition checking based on
     * waypoint, plane or obstacle thresholds.
     *
     * Use this API to control a digital output when a specified condition is
     * met (for example, waypoint arrival or distance to a plane/obstacle).
     * Specify an object type, name and a threshold value to enable conditional
     * triggering. When the condition is satisfied, the given digital output
     * will be set to the requested runstate.
     *
     * @param io_type Numeric IO type (e.g. 0=standard, 1=tool, 2=configurable)
     * @param index IO pin index starting from 0
     * @param runstate The desired output action
     * @param object_type Condition object type: 0=None, 1=Waypoint, 2=Plane,
     * 3=Obstacle
     * @param object_name Unique identifier of the condition object (optional)
     * @param threshold Condition threshold: angle in degrees for waypoints,
     * or distance in millimeters for planes/obstacles(optional)
     *
     * @return Returns 0 on success, non-zero error code on failure.
     * \endenglish
     */
    int setDigitalOutputRunstate(int io_type, int index,
                                 StandardOutputRunState runstate,
                                 int object_type,
                                 const std::string &object_name, int threshold);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准数字输出状态选择
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 输出状态选择
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int)
     * -> arcs::common_interface::StandardOutputRunState
     *
     * @par Lua函数原型
     * getStandardDigitalOutputRunstate(index: number) -> number
     *
     * @par Lua示例
     * num = getStandardDigitalOutputRunstate(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endchinese
     * \english
     * Get the runstate for standard digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Output runstate selection
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int)
     * -> arcs::common_interface::StandardOutputRunState
     *
     * @par Lua function prototype
     * getStandardDigitalOutputRunstate(index: number) -> number
     *
     * @par Lua example
     * num = getStandardDigitalOutputRunstate(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endenglish
     */
    StandardOutputRunState getStandardDigitalOutputRunstate(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端数字输出状态选择
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 输出状态选择
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardOutputRunState
     *
     * @par Lua函数原型
     * getToolDigitalOutputRunstate(index: number) -> number
     *
     * @par Lua示例
     * num = getToolDigitalOutputRunstate(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endchinese
     * \english
     * Get the runstate for tool digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Output runstate selection
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardOutputRunState
     *
     * @par Lua function prototype
     * getToolDigitalOutputRunstate(index: number) -> number
     *
     * @par Lua example
     * num = getToolDigitalOutputRunstate(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endenglish
     */
    StandardOutputRunState getToolDigitalOutputRunstate(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取可配置数字输出状态选择
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 输出状态选择
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConfigurableDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0:
     * int)
     * -> arcs::common_interface::StandardOutputRunState
     *
     * @par Lua函数原型
     * getConfigurableDigitalOutputRunstate(index: number) -> number
     *
     * @par Lua示例
     * num = getConfigurableDigitalOutputRunstate(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endchinese
     * \english
     * Get the runstate for configurable digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Output runstate selection
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConfigurableDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0:
     * int)
     * -> arcs::common_interface::StandardOutputRunState
     *
     * @par Lua function prototype
     * getConfigurableDigitalOutputRunstate(index: number) -> number
     *
     * @par Lua example
     * num = getConfigurableDigitalOutputRunstate(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endenglish
     */
    StandardOutputRunState getConfigurableDigitalOutputRunstate(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取指定类型数字输出状态选择。
     *
     * 用于查询不同类型的数字输出（标准数字输出、工具端数字输出、可配置数字输出）的
     * 当前运行状态选择（例如 WaypointArrived 等）,
     * 一般跟 setDigitalOutputRunstate 一起使用。
     *
     * @param io_type
     * 数字输出类型（0=标准数字输出、1=工具数字输出、2=可配置数字输出）
     * @param index 输出口的索引，管脚编号从0开始
     * @return 返回对应的 `StandardOutputRunState` 枚举值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getDigitalOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int) -> arcs::common_interface::StandardOutputRunState
     *
     * @par Lua函数原型
     * getDigitalOutputRunstate(io_type: number, index: number) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getDigitalOutputRunstate","params":[1,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     * \endchinese
     * \english
     * Get the current runstate of a digital output of the specified type.
     *
     * Use this API to query the runstate selection (for example None,
     * Handguiding, WaypointArrived) of different digital output types
     * (standard, tool, configurable).
     *
     * @param io_type Numeric IO type (0=standard, 1=tool, 2=configurable)
     * @param index IO pin index starting from 0
     * @return Returns the corresponding `StandardOutputRunState` enum value
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    StandardOutputRunState getDigitalOutputRunstate(int io_type, int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准模拟输出状态选择
     *
     * @note
     * 当给输出状态设置为无(StandardOutputRunState::None)时，
     * 用户可以设置模拟输出值。\n
     * 当给输出设置状态时，用户不可设置模拟输出值，控制器会自动设置模拟输出值。\n
     * 例如，当设置AO0的输出状态为高电平指示正在拖动示教(StandardOutputRunState::Handguiding)时，
     * 机器人进入拖动示教，AO0的值会自动变为最大值。
     * 机器人退出拖动示教，AO0的值会自动变为0。
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param runstate: 输出状态选择
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua函数原型
     * setStandardAnalogOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua示例
     * setStandardAnalogOutputRunstate(0,6)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardAnalogOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the runstate for standard analog output.
     *
     * @note
     * When the output runstate is set to None (StandardOutputRunState::None),
     * users can set the analog output value.\n
     * When the output runstate is set, users cannot set the analog output
     * value, and the controller will set it automatically.\n For example, when
     * AO0's output runstate is set to indicate hand-guiding
     * (StandardOutputRunState::Handguiding), the robot enters hand-guiding mode
     * and AO0 will automatically become the maximum value. When the robot exits
     * hand-guiding, AO0 will automatically become 0.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param runstate: Output runstate selection
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua function prototype
     * setStandardAnalogOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua example
     * setStandardAnalogOutputRunstate(0,6)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardAnalogOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardAnalogOutputRunstate(int index,
                                        StandardOutputRunState runstate);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端模拟输出状态选择
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param runstate: 输出状态选择
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua函数原型
     * setToolAnalogOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua示例
     * setToolAnalogOutputRunstate(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolAnalogOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the runstate for tool analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param runstate: Output runstate selection
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * arcs::common_interface::StandardOutputRunState) -> int
     *
     * @par Lua function prototype
     * setToolAnalogOutputRunstate(index: number, runstate: number) -> nil
     *
     * @par Lua example
     * setToolAnalogOutputRunstate(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolAnalogOutputRunstate","params":[0,"None"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolAnalogOutputRunstate(int index, StandardOutputRunState runstate);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准模拟输出状态选择
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 标准模拟输出状态选择
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardOutputRunState
     *
     * @par Lua函数原型
     * getStandardAnalogOutputRunstate(index: number) -> number
     *
     * @par Lua示例
     * num = getStandardAnalogOutputRunstate(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endchinese
     * \english
     * Get the runstate for standard analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Standard analog output runstate selection
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardOutputRunState
     *
     * @par Lua function prototype
     * getStandardAnalogOutputRunstate(index: number) -> number
     *
     * @par Lua example
     * num = getStandardAnalogOutputRunstate(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endenglish
     */
    StandardOutputRunState getStandardAnalogOutputRunstate(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端模拟输出状态选择
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 工具端模拟输出状态选择
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardOutputRunState
     *
     * @par Lua函数原型
     * getToolAnalogOutputRunstate(index: number) -> number
     *
     * @par Lua示例
     * num = getToolAnalogOutputRunstate(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endchinese
     * \english
     * Get the runstate for tool analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Tool analog output runstate selection
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolAnalogOutputRunstate(self: pyaubo_sdk.IoControl, arg0: int) ->
     * arcs::common_interface::StandardOutputRunState
     *
     * @par Lua function prototype
     * getToolAnalogOutputRunstate(index: number) -> number
     *
     * @par Lua example
     * num = getToolAnalogOutputRunstate(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutputRunstate","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"None"}
     *
     * \endenglish
     */
    StandardOutputRunState getToolAnalogOutputRunstate(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置所有数字输出急停后状态为默认（不做改变）
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setDigitalOutputAfterEStopDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * setDigitalOutputAfterEStopDefault() -> nil
     *
     * @par Lua示例
     * setDigitalOutputAfterEStopDefault()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setDigitalOutputAfterEStopDefault","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set all digital output states after emergency stop to default(no change)
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setDigitalOutputAfterEStopDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * setDigitalOutputAfterEStopDefault() -> nil
     *
     * @par Lua example
     * setDigitalOutputAfterEStopDefault()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setDigitalOutputAfterEStopDefault","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setDigitalOutputAfterEStopDefault();

    /**
     * @ingroup IoControl
     * \chinese
     * 设置所有模拟输出急停后状态为默认（不做改变）
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setAnalogOutputAfterEStopDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * setAnalogOutputAfterEStopDefault() -> nil
     *
     * @par Lua示例
     * setAnalogOutputAfterEStopDefault()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setAnalogOutputAfterEStopDefault","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set all analog output states after emergency stop to default(no change)
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setAnalogOutputAfterEStopDefault(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * setAnalogOutputAfterEStopDefault() -> nil
     *
     * @par Lua example
     * setAnalogOutputAfterEStopDefault()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setAnalogOutputAfterEStopDefault","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setAnalogOutputAfterEStopDefault();

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准数字输出急停后的输出值
     *
     * @param index:  表示IO口的管脚，
     * @param value: 输出值
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardDigitalOutputAfterEStop(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: bool) -> int
     *
     * @par Lua函数原型
     * setStandardDigitalOutputAfterEStop(index: number, value: boolean) -> nil
     *
     * @par Lua示例
     * setStandardDigitalOutputAfterEStop(0,true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutputAfterEStop","params":[0,true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the value of a standard digital output after emergency stop
     *
     * @param index: Indicates the IO pin.
     * @param value: Output value.
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardDigitalOutputAfterEStop(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: bool) -> int
     *
     * @par Lua function prototype
     * setStandardDigitalOutputAfterEStop(index: number, value: boolean) -> nil
     *
     * @par Lua example
     * setStandardDigitalOutputAfterEStop(0,true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutputAfterEStop","params":[0,true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardDigitalOutputAfterEStop(int index, bool value);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置可配置数字输出急停后的输出值
     *
     * @param index:  表示IO口的管脚，
     * @param value: 输出值
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConfigurableDigitalOutputAfterEStop(self: pyaubo_sdk.IoControl, arg0:
     * int, arg1: bool) -> int
     *
     * @par Lua函数原型
     * setConfigurableDigitalOutputAfterEStop(index: number, value: boolean) ->
     * nil
     *
     * @par Lua示例
     * setConfigurableDigitalOutputAfterEStop(0,true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutputAfterEStop","params":[0,true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the value of a configurable digital output after emergency stop
     *
     * @param index: Indicates the IO pin.
     * @param value: Output value.
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConfigurableDigitalOutputAfterEStop(self: pyaubo_sdk.IoControl, arg0:
     * int, arg1: bool) -> int
     *
     * @par Lua function prototype
     * setConfigurableDigitalOutputAfterEStop(index: number, value: boolean) ->
     * nil
     *
     * @par Lua example
     * setConfigurableDigitalOutputAfterEStop(0,true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutputAfterEStop","params":[0,true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConfigurableDigitalOutputAfterEStop(int index, bool value);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准模拟输出急停后的输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param value: 模拟输出值
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardAnalogOutputAfterEStop(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: float) -> int
     *
     * @par Lua函数原型
     * setStandardAnalogOutputAfterEStop(index: number, value: number) -> nil
     *
     * @par Lua示例
     * setStandardAnalogOutputAfterEStop(0,5.4)
     *
     * \endchinese
     * \english
     * Set the value of standard analog output after emergency stop
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param value: Output value.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardAnalogOutputAfterEStop(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: float) -> int
     *
     * @par Lua function prototype
     * setStandardAnalogOutputAfterEStop(index: number, value: number) -> nil
     *
     * @par Lua example
     * setStandardAnalogOutputAfterEStop(0,5.4)
     *
     * \endenglish
     */
    int setStandardAnalogOutputAfterEStop(int index, double value);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准模拟输入的范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param domain: 输入的范围
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int) -> int
     *
     * @par Lua函数原型
     * setStandardAnalogInputDomain(index: number, domain: number) -> nil
     *
     * @par Lua示例
     * setStandardAnalogInputDomain(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardAnalogInputDomain","params":[0,8],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the range of standard analog input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param domain: Input range
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int) -> int
     *
     * @par Lua function prototype
     * setStandardAnalogInputDomain(index: number, domain: number) -> nil
     *
     * @par Lua example
     * setStandardAnalogInputDomain(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardAnalogInputDomain","params":[0,8],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardAnalogInputDomain(int index, int domain);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端模拟输入的范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param domain: 输入的范围
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int) -> int
     *
     * @par Lua函数原型
     * setToolAnalogInputDomain(index: number, domain: number) -> nil
     *
     * @par Lua示例
     * setToolAnalogInputDomain(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolAnalogInputDomain","params":[0,8],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the range of tool analog input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param domain: Input range
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int) -> int
     *
     * @par Lua function prototype
     * setToolAnalogInputDomain(index: number, domain: number) -> nil
     *
     * @par Lua example
     * setToolAnalogInputDomain(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolAnalogInputDomain","params":[0,8],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolAnalogInputDomain(int index, int domain);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准模式输入范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 标准模式输入范围
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int) ->
     * int
     *
     * @par Lua函数原型
     * getStandardAnalogInputDomain(index: number) -> number
     *
     * @par Lua示例
     * num = getStandardAnalogInputDomain(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogInputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the domain of standard analog input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Standard analog input domain
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int) ->
     * int
     *
     * @par Lua function prototype
     * getStandardAnalogInputDomain(index: number) -> number
     *
     * @par Lua example
     * num = getStandardAnalogInputDomain(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogInputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getStandardAnalogInputDomain(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端模式输入范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 工具端模式输入范围
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * getToolAnalogInputDomain(index: number) -> number
     *
     * @par Lua示例
     * num = getToolAnalogInputDomain(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogInputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":10}
     *
     * \endchinese
     * \english
     * Get the domain of tool analog input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Tool analog input domain
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolAnalogInputDomain(self: pyaubo_sdk.IoControl, arg0: int) -> int
     *
     * @par Lua function prototype
     * getToolAnalogInputDomain(index: number) -> number
     *
     * @par Lua example
     * num = getToolAnalogInputDomain(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogInputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":10}
     *
     * \endenglish
     */
    int getToolAnalogInputDomain(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准模拟输出的范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param domain: 输出的范围
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: int) -> int
     *
     * @par Lua函数原型
     * setStandardAnalogOutputDomain(index: number, domain: number) -> nil
     *
     * @par Lua示例
     * setStandardAnalogOutputDomain(0,1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardAnalogOutputDomain","params":[0,8],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the range of standard analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param domain: Output range
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: int) -> int
     *
     * @par Lua function prototype
     * setStandardAnalogOutputDomain(index: number, domain: number) -> nil
     *
     * @par Lua example
     * setStandardAnalogOutputDomain(0,1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardAnalogOutputDomain","params":[0,8],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardAnalogOutputDomain(int index, int domain);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端模拟输出范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param domain: 输出的范围
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int) -> int
     *
     * @par Lua函数原型
     * setToolAnalogOutputDomain(index: number, domain: number) -> nil
     *
     * @par Lua示例
     * setToolAnalogOutputDomain(0,1)
     *
     * \endchinese
     * \english
     * Set the range of tool analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param domain: Output range
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * int) -> int
     *
     * @par Lua function prototype
     * setToolAnalogOutputDomain(index: number, domain: number) -> nil
     *
     * @par Lua example
     * setToolAnalogOutputDomain(0,1)
     *
     * \endenglish
     */
    int setToolAnalogOutputDomain(int index, int domain);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准模拟输出范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 标准模拟输出范围
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int) ->
     * int
     *
     * @par Lua函数原型
     * getStandardAnalogOutputDomain(index: number) -> number
     *
     * @par Lua示例
     * num = getStandardAnalogOutputDomain(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the domain of standard analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Standard analog output domain
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int) ->
     * int
     *
     * @par Lua function prototype
     * getStandardAnalogOutputDomain(index: number) -> number
     *
     * @par Lua example
     * num = getStandardAnalogOutputDomain(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getStandardAnalogOutputDomain(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端模拟输出范围
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @return 工具端模拟输出范围
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * getToolAnalogOutputDomain(index: number) -> number
     *
     * @par Lua示例
     * num = getToolAnalogOutputDomain(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the domain of tool analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @return Tool analog output domain
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolAnalogOutputDomain(self: pyaubo_sdk.IoControl, arg0: int) -> int
     *
     * @par Lua function prototype
     * getToolAnalogOutputDomain(index: number) -> number
     *
     * @par Lua example
     * num = getToolAnalogOutputDomain(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutputDomain","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getToolAnalogOutputDomain(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端电源电压值(单位V)
     *
     * @param domain: 工具端电源电压值，可选三个档位，分别为0、12和24。\n
     *  0表示0V, 12表示12V, 24表示24V。
     *
     * @return 成功返回0; 失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolVoltageOutputDomain(self: pyaubo_sdk.IoControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * setToolVoltageOutputDomain(domain: number) -> nil
     *
     * @par Lua示例
     * setToolVoltageOutputDomain(24)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolVoltageOutputDomain","params":[24],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the tool voltage output value (unit: V)
     *
     * @param domain: Tool voltage output value, can be 0, 12, or 24.\n
     *  0 means 0V, 12 means 12V, 24 means 24V.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolVoltageOutputDomain(self: pyaubo_sdk.IoControl, arg0: int) -> int
     *
     * @par Lua function prototype
     * setToolVoltageOutputDomain(domain: number) -> nil
     *
     * @par Lua example
     * setToolVoltageOutputDomain(24)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolVoltageOutputDomain","params":[24],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolVoltageOutputDomain(int domain);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端电源电压值(单位V)
     *
     * @return 工具端电源电压值(单位V)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolVoltageOutputDomain(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getToolVoltageOutputDomain() -> number
     *
     * @par Lua示例
     * num = getToolVoltageOutputDomain()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolVoltageOutputDomain","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the tool voltage output value (unit: V)
     *
     * @return Tool voltage output value (unit: V)
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolVoltageOutputDomain(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getToolVoltageOutputDomain() -> number
     *
     * @par Lua example
     * num = getToolVoltageOutputDomain()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolVoltageOutputDomain","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getToolVoltageOutputDomain();

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准数字输出值
     *
     * @param index:  表示IO口的管脚，
     * @param value: 输出值
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * bool) -> int
     *
     * @par Lua函数原型
     * setStandardDigitalOutput(index: number, value: boolean) -> nil
     *
     * @par Lua示例
     * setStandardDigitalOutput(0,true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutput","params":[0,true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the value of a standard digital output.
     *
     * @param index: Indicates the IO pin.
     * @param value: Output value.
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * bool) -> int
     *
     * @par Lua function prototype
     * setStandardDigitalOutput(index: number, value: boolean) -> nil
     *
     * @par Lua example
     * setStandardDigitalOutput(0,true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutput","params":[0,true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardDigitalOutput(int index, bool value);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置数字输出脉冲
     *
     * @param index
     * @param value
     * @param duration
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardDigitalOutputPulse(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: bool, arg2: float) -> int
     *
     * @par Lua函数原型
     * setStandardDigitalOutputPulse(index: number, value: boolean, duration:
     * number) -> nil
     *
     * @par Lua示例
     * setStandardDigitalOutputPulse(0,true,2.5)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutputPulse","params":[0,true,0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set digital output pulse.
     *
     * @param index
     * @param value
     * @param duration
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardDigitalOutputPulse(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: bool, arg2: float) -> int
     *
     * @par Lua function prototype
     * setStandardDigitalOutputPulse(index: number, value: boolean, duration:
     * number) -> nil
     *
     * @par Lua example
     * setStandardDigitalOutputPulse(0,true,2.5)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setStandardDigitalOutputPulse","params":[0,true,0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setStandardDigitalOutputPulse(int index, bool value, double duration);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端数字输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param value: 数字输出值
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1: bool)
     * -> int
     *
     * @par Lua函数原型
     * setToolDigitalOutput(index: number, value: boolean) -> nil
     *
     * @par Lua示例
     * setToolDigitalOutput(0,true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalOutput","params":[0,true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the value of tool digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param value: Output value.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1: bool)
     * -> int
     *
     * @par Lua function prototype
     * setToolDigitalOutput(index: number, value: boolean) -> nil
     *
     * @par Lua example
     * setToolDigitalOutput(0,true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalOutput","params":[0,true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolDigitalOutput(int index, bool value);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端数字输出脉冲
     *
     * @param index
     * @param value
     * @param duration
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolDigitalOutputPulse(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * bool, arg2: float) -> int
     *
     * @par Lua函数原型
     * setToolDigitalOutputPulse(index: number, value: boolean, duration:
     * number) -> nil
     *
     * @par Lua示例
     * setToolDigitalOutputPulse(0,true,2)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalOutputPulse","params":[0,true,0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set tool digital output pulse.
     *
     * @param index
     * @param value
     * @param duration
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolDigitalOutputPulse(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * bool, arg2: float) -> int
     *
     * @par Lua function prototype
     * setToolDigitalOutputPulse(index: number, value: boolean, duration:
     * number) -> nil
     *
     * @par Lua example
     * setToolDigitalOutputPulse(0,true,2)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolDigitalOutputPulse","params":[0,true,0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setToolDigitalOutputPulse(int index, bool value, double duration);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置可配置数字输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param value: 数字输出值
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConfigurableDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * bool) -> int
     *
     * @par Lua函数原型
     * setConfigurableDigitalOutput(index: number, value: boolean) -> nil
     *
     * @par Lua示例
     * setConfigurableDigitalOutput(0,true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutput","params":[0,true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the value of configurable digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param value: Output value.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConfigurableDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * bool) -> int
     *
     * @par Lua function prototype
     * setConfigurableDigitalOutput(index: number, value: boolean) -> nil
     *
     * @par Lua example
     * setConfigurableDigitalOutput(0,true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutput","params":[0,true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConfigurableDigitalOutput(int index, bool value);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置可配置数字输出脉冲
     *
     * @param index
     * @param value
     * @param duration
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setConfigurableDigitalOutputPulse(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: bool, arg2: float) -> int
     *
     * @par Lua函数原型
     * setConfigurableDigitalOutputPulse(index: number, value: boolean,
     * duration: number) -> nil
     *
     * @par Lua示例
     * setConfigurableDigitalOutputPulse(0,true,2.3)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutputPulse","params":[0,true,0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set configurable digital output pulse.
     *
     * @param index
     * @param value
     * @param duration
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setConfigurableDigitalOutputPulse(self: pyaubo_sdk.IoControl, arg0: int,
     * arg1: bool, arg2: float) -> int
     *
     * @par Lua function prototype
     * setConfigurableDigitalOutputPulse(index: number, value: boolean,
     * duration: number) -> nil
     *
     * @par Lua example
     * setConfigurableDigitalOutputPulse(0,true,2.3)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setConfigurableDigitalOutputPulse","params":[0,true,0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setConfigurableDigitalOutputPulse(int index, bool value,
                                          double duration);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置标准模拟输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param value: 模拟输出值
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setStandardAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * float) -> int
     *
     * @par Lua函数原型
     * setStandardAnalogOutput(index: number, value: number) -> nil
     *
     * @par Lua示例
     * setStandardAnalogOutput(0,5.4)
     *
     * \endchinese
     * \english
     * Set the value of standard analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param value: Output value.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setStandardAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1:
     * float) -> int
     *
     * @par Lua function prototype
     * setStandardAnalogOutput(index: number, value: number) -> nil
     *
     * @par Lua example
     * setStandardAnalogOutput(0,5.4)
     *
     * \endenglish
     */
    int setStandardAnalogOutput(int index, double value);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置工具端模拟输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     * @param value: 模拟输出
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * setToolAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua函数原型
     * setToolAnalogOutput(index: number, value: number) -> nil
     *
     * @par Lua示例
     * setToolAnalogOutput(0,1.2)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolAnalogOutput","params":[0,0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":13}
     *
     * \endchinese
     * \english
     * Set the value of tool analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     * @param value: Output value.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_REQUEST_IGNORE
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * setToolAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua function prototype
     * setToolAnalogOutput(index: number, value: number) -> nil
     *
     * @par Lua example
     * setToolAnalogOutput(0,1.2)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.setToolAnalogOutput","params":[0,0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":13}
     *
     * \endenglish
     */
    int setToolAnalogOutput(int index, double value);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准数字输入值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 高电平返回true; 低电平返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardDigitalInput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * getStandardDigitalInput(index: number) -> boolean
     *
     * @par Lua示例
     * status = getStandardDigitalInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Get the value of a standard digital input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Returns true for high level; false for low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardDigitalInput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua function prototype
     * getStandardDigitalInput(index: number) -> boolean
     *
     * @par Lua example
     * status = getStandardDigitalInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool getStandardDigitalInput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的标准数字输入值
     *
     * @return 所有的标准数字输入值 \n
     * 例如，当返回值是2863267846时,换成2进制后是10101010101010100000000000000110。
     * 后16位就是所有的标准数字输入状态值，
     * 最后一位表示DI00的输入状态值,倒数第二位表示DI01的输入状态值，以此类推。\n
     * 1表示高电平状态，0表示低电平状态
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardDigitalInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStandardDigitalInputs() -> number
     *
     * @par Lua示例
     * num = getStandardDigitalInputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get all standard digital input values.
     *
     * @return All standard digital input values.\n
     * For example, if the return value is 2863267846, its binary representation
     * is 10101010101010100000000000000110. The lower 16 bits represent the
     * status of all standard digital inputs, the least significant bit
     * indicates the input status of DI00, the second least significant bit
     * indicates DI01, and so on.\n 1 means high level, 0 means low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardDigitalInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStandardDigitalInputs() -> number
     *
     * @par Lua example
     * num = getStandardDigitalInputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalInputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    uint32_t getStandardDigitalInputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端数字输入值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 高电平返回true; 低电平返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolDigitalInput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * getToolDigitalInput(index: number) -> boolean
     *
     * @par Lua示例
     * status = getToolDigitalInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Get the value of tool digital input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Returns true for high level; false for low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolDigitalInput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua function prototype
     * getToolDigitalInput(index: number) -> boolean
     *
     * @par Lua example
     * status = getToolDigitalInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool getToolDigitalInput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的工具端数字输入值
     *
     * @return 返回所有的工具端数字输入值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolDigitalInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getToolDigitalInputs() -> number
     *
     * @par Lua示例
     * num = getToolDigitalInputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get all tool digital input values.
     *
     * @return Returns all tool digital input values.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolDigitalInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getToolDigitalInputs() -> number
     *
     * @par Lua example
     * num = getToolDigitalInputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalInputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    uint32_t getToolDigitalInputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取可配置数字输入值
     *
     * @note 可用于获取安全IO的输入值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 高电平返回true; 低电平返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConfigurableDigitalInput(self: pyaubo_sdk.IoControl, arg0: int) ->
     * bool
     *
     * @par Lua函数原型
     * getConfigurableDigitalInput(index: number) -> boolean
     *
     * @par Lua示例
     * status = getConfigurableDigitalInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Get the value of configurable digital input.
     *
     * @note Can be used to get the value of safety IO.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Returns true for high level; false for low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConfigurableDigitalInput(self: pyaubo_sdk.IoControl, arg0: int) ->
     * bool
     *
     * @par Lua function prototype
     * getConfigurableDigitalInput(index: number) -> boolean
     *
     * @par Lua example
     * status = getConfigurableDigitalInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool getConfigurableDigitalInput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的可配置数字输入值
     *
     * @note 可用于获取安全IO的输入值
     *
     * @return 所有的可配置数字输入值\n
     * 例如，当返回值是2863267846时,换成2进制后是10101010101010100000000000000110。
     * 后16位就是所有的输入状态值，
     * 最后一位表示管脚0的输入状态值,倒数第二位表示管脚1的输入状态值，以此类推。\n
     * 1表示高电平状态，0表示低电平状态
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConfigurableDigitalInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getConfigurableDigitalInputs() -> number
     *
     * @par Lua示例
     * num = getConfigurableDigitalInputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get all configurable digital input values.
     *
     * @note Can be used to get the value of safety IO.
     *
     * @return All configurable digital input values.\n
     * For example, if the return value is 2863267846, its binary representation
     * is 10101010101010100000000000000110. The lower 16 bits represent the
     * status of all input pins, the least significant bit indicates the input
     * status of pin 0, the second least significant bit indicates pin 1, and so
     * on.\n 1 means high level, 0 means low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConfigurableDigitalInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getConfigurableDigitalInputs() -> number
     *
     * @par Lua example
     * num = getConfigurableDigitalInputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalInputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    uint32_t getConfigurableDigitalInputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准数字输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 高电平返回true; 低电平返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * getStandardDigitalOutput(index: number) -> boolean
     *
     * @par Lua示例
     * status = getStandardDigitalOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Get the value of a standard digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Returns true for high level; false for low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua function prototype
     * getStandardDigitalOutput(index: number) -> boolean
     *
     * @par Lua example
     * status = getStandardDigitalOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool getStandardDigitalOutput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的标准数字输出值
     *
     * @return 所有的标准数字输出值 \n
     * 例如，当返回值是2863267846时,换成2进制后是10101010101010100000000000000110。
     * 后16位就是所有的标准数字输出状态值，
     * 最后一位表示DI00的输出状态值,倒数第二位表示DI01的输出状态值，以此类推。\n
     * 1表示高电平状态，0表示低电平状态.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardDigitalOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStandardDigitalOutputs() -> number
     *
     * @par Lua示例
     * num = getStandardDigitalOutputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":69}
     *
     * \endchinese
     * \english
     * Get all standard digital output values.
     *
     * @return All standard digital output values.\n
     * For example, if the return value is 2863267846, its binary representation
     * is 10101010101010100000000000000110. The lower 16 bits represent the
     * status of all standard digital outputs, the least significant bit
     * indicates the output status of DO00, the second least significant bit
     * indicates DO01, and so on.\n 1 means high level, 0 means low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardDigitalOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStandardDigitalOutputs() -> number
     *
     * @par Lua example
     * num = getStandardDigitalOutputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardDigitalOutputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":69}
     *
     * \endenglish
     */
    uint32_t getStandardDigitalOutputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端数字输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 高电平返回true; 低电平返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * getToolDigitalOutput(index: number) -> boolean
     *
     * @par Lua示例
     * status = getToolDigitalOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Get the value of tool digital output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Returns true for high level; false for low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int) -> bool
     *
     * @par Lua function prototype
     * getToolDigitalOutput(index: number) -> boolean
     *
     * @par Lua example
     * status = getToolDigitalOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool getToolDigitalOutput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的工具端数字输出值
     *
     * @return 所有的工具端数字输出值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolDigitalOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getToolDigitalOutputs() -> number
     *
     * @par Lua示例
     * num = getToolDigitalOutputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":9}
     *
     * \endchinese
     * \english
     * Get all tool digital output values.
     *
     * @return All tool digital output values.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolDigitalOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getToolDigitalOutputs() -> number
     *
     * @par Lua example
     * num = getToolDigitalOutputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolDigitalOutputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":9}
     *
     * \endenglish
     */
    uint32_t getToolDigitalOutputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取可配值数字输出值
     *
     * @note 可用于获取安全IO的输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 高电平返回true; 低电平返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConfigurableDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int) ->
     * bool
     *
     * @par Lua函数原型
     * getConfigurableDigitalOutput(index: number) -> boolean
     *
     * @par Lua示例
     * status = getConfigurableDigitalOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Get the value of configurable digital output.
     *
     * @note Can be used to get the value of safety IO.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Returns true for high level; false for low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConfigurableDigitalOutput(self: pyaubo_sdk.IoControl, arg0: int) ->
     * bool
     *
     * @par Lua function prototype
     * getConfigurableDigitalOutput(index: number) -> boolean
     *
     * @par Lua example
     * status = getConfigurableDigitalOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool getConfigurableDigitalOutput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的可配值数字输出值
     *
     * @note 可用于获取安全IO的输出值
     *
     * @return 所有的可配值数字输出\n
     * 例如，当返回值是2863267846时,换成2进制后是10101010101010100000000000000110。
     * 后16位就是所有的输出值，
     * 最后一位表示管脚0的输出状态值,倒数第二位表示管脚1的输出状态值，以此类推。\n
     * 1表示高电平状态，0表示低电平状态.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getConfigurableDigitalOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getConfigurableDigitalOutputs() -> number
     *
     * @par Lua示例
     * num = getConfigurableDigitalOutputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endchinese
     * \english
     * Get all configurable digital output values.
     *
     * @note Can be used to get the value of safety IO.
     *
     * @return All configurable digital output values.\n
     * For example, if the return value is 2863267846, its binary representation
     * is 10101010101010100000000000000110. The lower 16 bits represent the
     * status of all output pins, the least significant bit indicates the output
     * status of pin 0, the second least significant bit indicates pin 1, and so
     * on.\n 1 means high level, 0 means low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getConfigurableDigitalOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getConfigurableDigitalOutputs() -> number
     *
     * @par Lua example
     * num = getConfigurableDigitalOutputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getConfigurableDigitalOutputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endenglish
     */
    uint32_t getConfigurableDigitalOutputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准模拟输入值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 标准模拟输入值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardAnalogInput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getStandardAnalogInput(index: number) -> number
     *
     * @par Lua示例
     * getStandardAnalogInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     * Get the value of standard analog input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Standard analog input value.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardAnalogInput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua function prototype
     * getStandardAnalogInput(index: number) -> number
     *
     * @par Lua example
     * getStandardAnalogInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getStandardAnalogInput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端模拟输入值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 工具端模拟输入值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolAnalogInput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getToolAnalogInput(index: number) -> number
     *
     * @par Lua示例
     * num = getToolAnalogInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     * Get the value of tool analog input.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Tool analog input value.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolAnalogInput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua function prototype
     * getToolAnalogInput(index: number) -> number
     *
     * @par Lua example
     * num = getToolAnalogInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getToolAnalogInput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取标准模拟输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 标准模拟输出值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStandardAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getStandardAnalogOutput(index: number) -> number
     *
     * @par Lua示例
     * num = getStandardAnalogOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     * Get the value of standard analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Standard analog output value.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStandardAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua function prototype
     * getStandardAnalogOutput(index: number) -> number
     *
     * @par Lua example
     * num = getStandardAnalogOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStandardAnalogOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getStandardAnalogOutput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取工具端模拟输出值
     *
     * @param index: 表示IO口的管脚，管脚编号从0开始。
     * 例如，0表示第一个管脚。
     *
     * @return 工具端模拟输出值
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getToolAnalogOutput(index: number) -> number
     *
     * @par Lua示例
     * num = getToolAnalogOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     * Get the value of tool analog output.
     *
     * @param index: Indicates the IO pin, starting from 0.
     * For example, 0 means the first pin.
     *
     * @return Tool analog output value.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolAnalogOutput(self: pyaubo_sdk.IoControl, arg0: int) -> float
     *
     * @par Lua function prototype
     * getToolAnalogOutput(index: number) -> number
     *
     * @par Lua example
     * num = getToolAnalogOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolAnalogOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getToolAnalogOutput(int index);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取联动输入数量
     *
     * @return 联动输入数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStaticLinkInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStaticLinkInputNum() -> number
     *
     * @par Lua示例
     * num = getStaticLinkInputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkInputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":8}
     *
     * \endchinese
     * \english
     * Get the number of static link inputs.
     *
     * @return Number of static link inputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStaticLinkInputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStaticLinkInputNum() -> number
     *
     * @par Lua example
     * num = getStaticLinkInputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkInputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":8}
     *
     * \endenglish
     */
    int getStaticLinkInputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取联动输出数量
     *
     * @return 联动输出数量
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStaticLinkOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStaticLinkOutputNum() -> number
     *
     * @par Lua示例
     * num = getStaticLinkOutputNum()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the number of static link outputs.
     *
     * @return Number of static link outputs.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStaticLinkOutputNum(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStaticLinkOutputNum() -> number
     *
     * @par Lua example
     * num = getStaticLinkOutputNum()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkOutputNum","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getStaticLinkOutputNum();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的联动输入值
     *
     * @return 所有的联动输入值\n
     * 例如，当返回值是2863267846时,换成2进制后是10101010101010100000000000000110。
     * 后16位就是所有的联动输入状态值，
     * 最后一位表示管脚0的输入状态值,倒数第二位表示管脚1的输入状态值，以此类推。\n
     * 1表示高电平状态，0表示低电平状态.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStaticLinkInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStaticLinkInputs() -> number
     *
     * @par Lua示例
     * num = getStaticLinkInputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkInputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get all static link input values.
     *
     * @return All static link input values.\n
     * For example, if the return value is 2863267846, its binary representation
     * is 10101010101010100000000000000110. The lower 16 bits represent the
     * status of all static link inputs, the least significant bit indicates the
     * input status of pin 0, the second least significant bit indicates pin 1,
     * and so on.\n 1 means high level, 0 means low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStaticLinkInputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStaticLinkInputs() -> number
     *
     * @par Lua example
     * num = getStaticLinkInputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkInputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    uint32_t getStaticLinkInputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取所有的联动输出值
     *
     * @return 返回所有的联动输出值 \n
     * 例如，当返回值是2863267846时,换成2进制后是10101010101010100000000000000110。
     * 后16位就是所有的联动输出状态值，
     * 最后一位表示管脚0的输出状态值,倒数第二位表示管脚1的输出状态值，以此类推。\n
     * 1表示高电平状态，0表示低电平状态.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getStaticLinkOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getStaticLinkOutputs() -> number
     *
     * @par Lua示例
     * num = getStaticLinkOutputs()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkOutputs","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get all static link output values.
     *
     * @return Returns all static link output values.\n
     * For example, if the return value is 2863267846, its binary representation
     * is 10101010101010100000000000000110. The lower 16 bits represent the
     * status of all static link outputs, the least significant bit indicates
     * the output status of pin 0, the second least significant bit indicates
     * pin 1, and so on.\n 1 means high level, 0 means low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getStaticLinkOutputs(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getStaticLinkOutputs() -> number
     *
     * @par Lua example
     * num = getStaticLinkOutputs()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getStaticLinkOutputs","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    uint32_t getStaticLinkOutputs();

    /**
     * @ingroup IoControl
     * \chinese
     * 机器人是否配置了编码器
     * 集成编码器的编号为 0
     *
     * @return 机器人配置编码器返回 true, 反之返回 false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.hasEncoderSensor","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Whether the robot is equipped with an encoder.
     * The integrated encoder number is 0.
     *
     * @return Returns true if the robot is equipped with an encoder, otherwise
     * false.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.hasEncoderSensor","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool hasEncoderSensor();
    /**
     * @ingroup IoControl
     * \chinese
     * 设置集成编码器的解码方式
     *
     * @param type
     * 0-禁用编码器
     * 1-AB正交
     * 2-AB正交+Z
     * 3-AB差分正交
     * 4-AB差分正交+Z差分
     *
     * @param range_id
     * 0 表示32位有符号编码器，范围为 [-2147483648, 2147483647]
     * 1 表示8位无符号编码器，范围为 [0, 255]
     * 2 表示16位无符号编码器，范围为 [0, 65535]
     * 3 表示24位无符号编码器，范围为 [0, 16777215]
     * 4 表示32位无符号编码器，范围为 [0, 4294967295]
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Set the decoding method of the integrated encoder.
     *
     * @param type
     * 0 - Disable encoder
     * 1 - AB quadrature
     * 2 - AB quadrature + Z
     * 3 - AB differential quadrature
     * 4 - AB differential quadrature + Z differential
     *
     * @param range_id
     * 0 is a 32-bit signed encoder, range [-2147483648, 2147483647]
     * 1 is an 8-bit unsigned encoder, range [0, 255]
     * 2 is a 16-bit unsigned encoder, range [0, 65535]
     * 3 is a 24-bit unsigned encoder, range [0, 16777215]
     * 4 is a 32-bit unsigned encoder, range [0, 4294967295]
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int setEncDecoderType(int type, int range_id);

    /**
     * @ingroup IoControl
     * \chinese
     * 设置集成编码器脉冲数
     *
     * @param tick 脉冲数
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Set the tick count of the integrated encoder.
     *
     * @param tick Tick count
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_INVL_ARGUMENT
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int setEncTickCount(int tick);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取编码器的解码方式
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getEncDecoderType","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the decoder type of the encoder.
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getEncDecoderType","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getEncDecoderType();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取脉冲数
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getEncTickCount","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the tick count
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getEncTickCount","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getEncTickCount();

    /**
     * @ingroup IoControl
     * \chinese
     * 防止在计数超出范围时计数错误
     *
     * @param delta_count
     *
     * @return 成功返回0；失败返回错误码
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endchinese
     * \english
     * Prevent counting errors when the count exceeds the range
     *
     * @param delta_count
     *
     * @return Returns 0 on success; error code on failure.
     * AUBO_NO_ACCESS
     * AUBO_BUSY
     * AUBO_BAD_STATE
     * -AUBO_BAD_STATE
     *
     * @throws arcs::common_interface::AuboException
     * \endenglish
     */
    int unwindEncDeltaTickCount(int delta_count);

    /**
     * @ingroup IoControl
     * \chinese
     * 获取末端按钮状态
     *
     * @return 按下返回true; 否则返回false
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getToolButtonStatus() -> bool
     *
     * @par Lua函数原型
     * getToolButtonStatus() -> boolean
     *
     * @par Lua示例
     * status = getToolButtonStatus()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolButtonStatus","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Get the status of the tool button.
     *
     * @return Returns true if pressed; otherwise false.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getToolButtonStatus() -> bool
     *
     * @par Lua function prototype
     * getToolButtonStatus() -> boolean
     *
     * @par Lua example
     * status = getToolButtonStatus()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getToolButtonStatus","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool getToolButtonStatus();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取手柄按键状态
     *
     * @note 获取手柄按键状态
     *
     * @return 所有的手柄按键输入值\n
     * 例如，当返回值是2863267846时,换成2进制后是10101010101010100000000000000110。
     * 后16位就是所有的输入状态值，
     * 最后一位表示管脚0的输入状态值,倒数第二位表示管脚1的输入状态值，以此类推。\n
     * 1表示高电平状态，0表示低电平状态
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getHandleIoStatus(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua函数原型
     * getHandleIoStatus() -> number
     *
     * @par Lua示例
     * num = getHandleIoStatus()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getHandleIoStatus","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the status of handle buttons.
     *
     * @note Get the status of handle buttons.
     *
     * @return All handle button input values.\n
     * For example, if the return value is 2863267846, its binary representation
     * is 10101010101010100000000000000110. The lower 16 bits represent the
     * status of all input pins, the least significant bit indicates the input
     * status of pin 0, the second least significant bit indicates pin 1, and so
     * on.\n 1 means high level, 0 means low level.
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getHandleIoStatus(self: pyaubo_sdk.IoControl) -> int
     *
     * @par Lua function prototype
     * getHandleIoStatus() -> number
     *
     * @par Lua example
     * num = getHandleIoStatus()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getHandleIoStatus","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    uint32_t getHandleIoStatus();

    /**
     * @ingroup IoControl
     * \chinese
     * 获取手柄类型
     *
     * @return type
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python函数原型
     * getHandleType() -> int
     *
     * @par Lua函数原型
     * getHandleType() -> int
     *
     * @par Lua示例
     * int_num = getHandleType()
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getHandleType","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the handle type.
     *
     * @return type
     *
     * @throws arcs::common_interface::AuboException
     *
     * @par Python function prototype
     * getHandleType() -> int
     *
     * @par Lua function prototype
     * getHandleType() -> int
     *
     * @par Lua example
     * int_num = getHandleType()
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"rob1.IoControl.getHandleType","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getHandleType();

protected:
    void *d_;
};
using IoControlPtr = std::shared_ptr<IoControl>;
} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_IO_CONTROL_INTERFACE_H
