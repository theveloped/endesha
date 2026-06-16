/** @file  register_control.h
 *  @brief 寄存器操作接口，用于三个模块之间的数据交换功能
 */
#ifndef AUBO_SDK_REGISTER_CONTROL_INTERFACE_H
#define AUBO_SDK_REGISTER_CONTROL_INTERFACE_H

#include <stdint.h>
#include <memory>
#include <vector>

#include <aubo/type_def.h>
#include <aubo/global_config.h>

enum ModbusErrorNum
{
    /** MODBUS unit not initiallized
     */
    MB_ERR_NOT_INIT = -1,

    /** MODBUS unit disconnected
     */
    MB_ERR_DISCONNECTED = -2,

    /** The function code received in the query is not an allowable action for
     * the server (or slave).
     */
    MB_ERR_ILLEGAL_FUNCTION = 1,

    /** The function code received in the query is not an allowable action for
     * the server (or slave), check that the entered signal address corresponds
     * to the setup of the remote MODBUS server.
     */
    MB_ERR_ILLEGAL_DATA_ADDRESS = 2,

    /** A value contained in the query data field is not an allowable value for
     * server (or slave), check that the enterd signal value is valid for the
     * specified address on the remote MODBUS server.
     */
    MB_ERR_ILLEGAL_DATA_VALUE = 3,

    /** An unrecoverable error occurred while the server (or slave) was
     * attempting to perform the requested action.
     */
    MB_ERR_SLAVE_DEVICE_FAILURE = 4,

    /** Specialized use in conjunction with programming commands sent to the
     * remote MODBUS unit.
     */
    MB_ERR_ACKNOWLEDGE = 5,

    /** Specialized use in conjunction with programming commands sent to the
     * remote MODBUS unit, the slave (server) is not able to respond now
     */
    MB_ERR_SLAVE_DEVICE_BUSY = 6,
};

namespace arcs {
namespace common_interface {

/**
 * @defgroup RegisterControl RegisterControl (寄存器操作)
 * \~chinese 通用寄存器 \~english General Registers
 */
class ARCS_ABI_EXPORT RegisterControl
{
public:
    RegisterControl();
    virtual ~RegisterControl();

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * 从一个输入寄存器中读取布尔值，也可以通过现场总线进行访问。
     * 注意，它使用自己的内存空间。
     *
     * @param address 寄存器的地址（0:127）
     * @return 寄存器中保存的布尔值（true、false）
     *
     * @note 布尔输入寄存器的较低范围[0:63]保留供FieldBus/PLC接口使用。
     * 较高范围[64:127]无法通过FieldBus/PLC接口访问，因为它保留供外部RTDE客户端使用。
     *
     * @par Python函数原型
     * getBoolInput(self: pyaubo_sdk.RegisterControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * getBoolInput(address: number) -> boolean
     *
     * @par Lua示例
     * BoolInput_0 = getBoolInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getBoolInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     *
     * \english
     * Reads the boolean from one of the input registers, which can also be
     * accessed by a Field bus. Note, uses its own memory space.
     *
     * @param address Address of the register (0:127)
     * @return Boolean value held by the register (true, false)
     *
     * @note The lower range of the boolean input registers [0:63] is reserved
     * for FieldBus/PLC interface usage. The upper range [64:127] cannot be
     * accessed by FieldBus/PLC interfaces, since it is reserved for external
     * RTDE clients.
     *
     * @par Python interface prototype
     * getBoolInput(self: pyaubo_sdk.RegisterControl, arg0: int) -> bool
     *
     * @par Lua interface prototype
     * getBoolInput(address: number) -> boolean
     *
     * @par Lua example
     * BoolInput_0 = getBoolInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getBoolInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool getBoolInput(uint32_t address);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address
     * @param value
     * @return
     *
     * @note 只有在实现 RTDE/Modbus Slave/PLC 服务端时使用
     *
     * @par Python函数原型
     * setBoolInput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: bool) ->
     * int
     *
     * @par Lua函数原型
     * setBoolInput(address: number, value: boolean) -> nil
     *
     * @par Lua示例
     * setBoolInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setBoolInput","params":[0,true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Address of the register (0:127)
     * @param value Boolean value to set (true or false)
     * @return Returns 0 on success, or an error code
     *
     * @note Only used when implementing RTDE/Modbus Slave/PLC server
     *
     * @par Python interface prototype
     * setBoolInput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: bool) ->
     * int
     *
     * @par Lua interface prototype
     * setBoolInput(address: number, value: boolean) -> nil
     *
     * @par Lua example
     * setBoolInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setBoolInput","params":[0,true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setBoolInput(uint32_t address, bool value);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * 从一个输入寄存器中读取整数值，也可以通过现场总线进行访问。
     * 注意，它使用自己的内存空间。
     *
     * @param address 寄存器的地址（0:47）
     * @return 寄存器中保存的整数值[-2,147,483,648 : 2,147,483,647]
     *
     * @note 整数输入寄存器的较低范围[0:23]保留供FieldBus/PLC接口使用。
     * 较高范围[24:47]无法通过FieldBus/PLC接口访问，因为它保留供外部RTDE客户端使用。
     *
     * @par Python函数原型
     * getInt32Input(self: pyaubo_sdk.RegisterControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * getInt32Input(address: number) -> number
     *
     * @par Lua示例
     * Int32Input_0 = getInt32Input(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt32Input","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     *
     * \english
     * Reads the integer from one of the input registers, which can also be
     * accessed by a FieldBus. Note, uses it’s own memory space.
     *
     * @param address Address of the register (0:47)
     * @return The value held by the register [-2,147,483,648 : 2,147,483,647]
     *
     * @note The lower range of the integer input registers [0:23] is reserved
     * for FieldBus/PLC interface usage. The upper range [24:47] cannot be
     * accessed by FieldBus/PLC interfaces, since it is reserved for external
     * RTDE clients.
     *
     * @par Python interface prototype
     * getInt32Input(self: pyaubo_sdk.RegisterControl, arg0: int) -> int
     *
     * @par Lua interface prototype
     * getInt32Input(address: number) -> number
     *
     * @par Lua example
     * Int32Input_0 = getInt32Input(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt32Input","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int getInt32Input(uint32_t address);

    /**
     * @ingroup RegisterControl
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address 寄存器的地址（0:47）
     * @param value 要设置的整数值
     * @return 返回0表示成功，其他为错误码
     *
     * @note 只有在实现 RTDE/Modbus Slave/PLC 服务端时使用
     *
     * @par Python函数原型
     * setInt32Input(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: int) ->
     * int
     *
     * @par Lua函数原型
     * setInt32Input(address: number, value: number) -> nil
     *
     * @par Lua示例
     * setInt32Input(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt32Input","params":[0,33],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Address of the register (0:47)
     * @param value Integer value to set
     * @return Returns 0 on success, or an error code
     *
     * @note Only used when implementing RTDE/Modbus Slave/PLC server
     *
     * @par Python interface prototype
     * setInt32Input(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: int) ->
     * int
     *
     * @par Lua interface prototype
     * setInt32Input(address: number, value: number) -> nil
     *
     * @par Lua example
     * setInt32Input(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt32Input","params":[0,33],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setInt32Input(uint32_t address, int value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * Reads the float from one of the input registers, which can also be
     * accessed by a Field bus. Note, uses it’s own memory space.
     *
     * 从一个输入寄存器中读取浮点数，也可以通过现场总线进行访问。
     * 注意，它使用自己的内存空间。
     *
     * @param address Address of the register (0:47)
     * 寄存器地址（0:47）
     * @return The value held by the register (float)
     * 寄存器中保存的浮点数值
     *
     * @note The lower range of the float input registers [0:23] is reserved
     * for FieldBus/PLC interface usage. The upper range [24:47] cannot be
     * accessed by FieldBus/PLC interfaces, since it is reserved for external
     * RTDE clients.
     * 浮点数输入寄存器的较低范围[0:23]保留供现场总线/PLC接口使用。
     * 较高范围[24:47]不能通过现场总线/PLC接口访问，因为它们是为外部RTDE客户端保留的。
     *
     * @par Python函数原型
     * getFloatInput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getFloatInput(address: number) -> number
     *
     * @par Lua示例
     * FloatInput_0 = getFloatInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getFloatInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     *
     * \english
     * Reads the float from one of the input registers, which can also be
     * accessed by a Field bus. Note, uses it’s own memory space.
     *
     * @param address Address of the register (0:47)
     * @return The value held by the register (float)
     *
     * @note The lower range of the float input registers [0:23] is reserved
     * for FieldBus/PLC interface usage. The upper range [24:47] cannot be
     * accessed by FieldBus/PLC interfaces, since it is reserved for external
     * RTDE clients.
     *
     * @par Python interface prototype
     * getFloatInput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua interface prototype
     * getFloatInput(address: number) -> number
     *
     * @par Lua example
     * FloatInput_0_0 = getFloatInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getFloatInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     */
    float getFloatInput(uint32_t address);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address 寄存器的地址（0:47）
     * @param value 要设置的浮点数值
     * @return 返回0表示成功，其他为错误码
     *
     * @note 只有在实现 RTDE/Modbus Slave/PLC 服务端时使用
     *
     * @par Python函数原型
     * setFloatInput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua函数原型
     * setFloatInput(address: number, value: number) -> nil
     *
     * @par Lua示例
     * setFloatInput(0, 3.3)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setFloatInput","params":[0,3.3],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Address of the register (0:47)
     * @param value Float value to set
     * @return Returns 0 on success, or an error code
     *
     * @note Only used when implementing RTDE/Modbus Slave/PLC server
     *
     * @par Python interface prototype
     * setFloatInput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua interface prototype
     * setFloatInput(address: number, value: number) -> nil
     *
     * @par Lua example
     * setFloatInput(0, 3.3)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setFloatInput","params":[0,3.3],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setFloatInput(uint32_t address, float value);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * 从一个输入寄存器中读取双精度浮点数，也可以通过现场总线进行访问。
     * 注意，它使用自己的内存空间。
     *
     * @param address 寄存器的地址（0:47）
     * @return 寄存器中保存的双精度浮点数值
     *
     * @par Python函数原型
     * getDoubleInput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getDoubleInput(address: number) -> number
     *
     * @par Lua示例
     * DoubleInput_0 = getDoubleInput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getDoubleInput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     *
     * Reads the double value from one of the input registers, which can also be
     * accessed by a FieldBus. Note, uses its own memory space.
     *
     * @param address Address of the register (0:47)
     * @return The double value held by the register
     *
     * @par Python interface prototype
     * getDoubleInput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua interface prototype
     * getDoubleInput(address: number) -> number
     *
     * @par Lua example
     * DoubleInput_0 = getDoubleInput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getDoubleInput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getDoubleInput(uint32_t address);

    /**
     * \english
     * @param address
     * @param value
     * @return
     *
     * @note Only used when implementing RTDE/Modbus Slave/PLC server
     *
     * @par Python interface prototype
     * setDoubleInput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua interface prototype
     * setDoubleInput(address: number, value: number) -> nil
     *
     * @par Lua example
     * setDoubleInput(0, 3.3)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setDoubleInput","params":[0,6.6],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     *
     * @ingroup RegisterControl
     * \chinese
     * @param address
     * @param value
     * @return
     *
     * @note 只有在实现 RTDE/Modbus Slave/PLC 服务端时使用
     *
     * @par Python函数原型
     * setDoubleInput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua函数原型
     * setDoubleInput(address: number, value: number) -> nil
     *
     * @par Lua示例
     * setDoubleInput(0, 3.3)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setDoubleInput","params":[0,6.6],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int setDoubleInput(uint32_t address, double value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 从一个输出寄存器中读取布尔值，也可以通过现场总线进行访问。
     * 注意，它使用自己的内存空间。
     *
     * @param address 寄存器地址（0:127）
     * @return 寄存器中保存的布尔值（true, false）
     *
     * @note 布尔输出寄存器的较低范围[0:63]保留供现场总线/PLC接口使用。
     * 较高范围[64:127]不能通过现场总线/PLC接口访问，因为它们是为外部RTDE客户端保留的。
     *
     * @par Python函数原型
     * getBoolOutput(self: pyaubo_sdk.RegisterControl, arg0: int) -> bool
     *
     * @par Lua函数原型
     * getBoolOutput(address: number) -> boolean
     *
     * @par Lua示例
     * BoolOutput_0 = getBoolOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getBoolOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endchinese
     *
     * \english
     * Reads the boolean from one of the output registers, which can also be
     * accessed by a Field bus.
     * Note, uses its own memory space.
     *
     * @param address Address of the register (0:127)
     * @return The boolean value held by the register (true, false)
     *
     * @note The lower range of the boolean output registers [0:63] is reserved
     * for FieldBus/PLC interface usage. The upper range [64:127] cannot be
     * accessed by FieldBus/PLC interfaces, since it is reserved for external
     * RTDE clients.
     *
     * @par Python interface prototype
     * getBoolOutput(self: pyaubo_sdk.RegisterControl, arg0: int) -> bool
     *
     * @par Lua interface prototype
     * getBoolOutput(address: number) -> boolean
     *
     * @par Lua example
     * BoolOutput_0 = getBoolOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getBoolOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     * \endenglish
     */
    bool getBoolOutput(uint32_t address);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address 寄存器地址（0:127）
     * @param value 要设置的布尔值（true 或 false）
     * @return 返回0表示成功，其他为错误码
     *
     * @par Python函数原型
     * setBoolOutput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: bool) ->
     * int
     *
     * @par Lua函数原型
     * setBoolOutput(address: number, value: boolean) -> nil
     *
     * @par Lua示例
     * setBoolOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setBoolOutput","params":[0,false],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Address of the register (0:127)
     * @param value Boolean value to set (true or false)
     * @return Returns 0 on success, or an error code
     *
     * @par Python interface prototype
     * setBoolOutput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: bool) ->
     * int
     *
     * @par Lua interface prototype
     * setBoolOutput(address: number, value: boolean) -> nil
     *
     * @par Lua example
     * setBoolOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setBoolOutput","params":[0,false],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setBoolOutput(uint32_t address, bool value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 从一个输出寄存器中读取整数值，也可以通过现场总线进行访问。
     * 注意，它使用自己的内存空间。
     *
     * @param address 寄存器地址（0:47）
     * @return 寄存器中保存的整数值（-2,147,483,648 : 2,147,483,647）
     *
     * @note 整数输出寄存器的较低范围[0:23]保留供现场总线/PLC接口使用。
     * 较高范围[24:47]不能通过现场总线/PLC接口访问，因为它们是为外部RTDE客户端保留的。
     *
     * @par Python函数原型
     * getInt32Output(self: pyaubo_sdk.RegisterControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * getInt32Output(address: number) -> number
     *
     * @par Lua示例
     * Int32Output_0 = getInt32Output(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt32Output","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     *
     * \english
     * Reads the integer from one of the output registers, which can also be
     * accessed by a FieldBus. Note, uses its own memory space.
     *
     * @param address Address of the register (0:47)
     * @return The int value held by the register [-2,147,483,648 :
     * 2,147,483,647]
     *
     * @note The lower range of the integer output registers [0:23] is reserved
     * for FieldBus/PLC interface usage. The upper range [24:47] cannot be
     * accessed by FieldBus/PLC interfaces, since it is reserved for external
     * RTDE clients.
     *
     * @par Python interface prototype
     * getInt32Output(self: pyaubo_sdk.RegisterControl, arg0: int) -> int
     *
     * @par Lua interface prototype
     * getInt32Output(address: number) -> number
     *
     * @par Lua example
     * Int32Output_0 = getInt32Output(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt32Output","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int getInt32Output(uint32_t address);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address 寄存器地址（0:47）
     * @param value 要设置的整数值
     * @return 返回0表示成功，其他为错误码
     *
     * @par Python函数原型
     * setInt32Output(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: int) ->
     * int
     *
     * @par Lua函数原型
     * setInt32Output(address: number, value: number) -> nil
     *
     * @par Lua示例
     * setInt32Output(0, 100)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt32Output","params":[0,100],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Address of the register (0:47)
     * @param value Integer value to set
     * @return Returns 0 on success, or an error code
     *
     * @par Python interface prototype
     * setInt32Output(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: int) ->
     * int
     *
     * @par Lua interface prototype
     * setInt32Output(address: number, value: number) -> nil
     *
     * @par Lua example
     * setInt32Output(0, 100)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt32Output","params":[0,100],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setInt32Output(uint32_t address, int value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 从一个输出寄存器中读取浮点数，也可以通过现场总线进行访问。
     * 注意，它使用自己的内存空间。
     *
     * @param address 寄存器地址（0:47）
     * @return 寄存器中保存的浮点数值（float）
     *
     * @note 浮点数输出寄存器的较低范围[0:23]保留供现场总线/PLC接口使用。
     * 较高范围[24:47]不能通过现场总线/PLC接口访问，因为它们是为外部RTDE客户端保留的。
     *
     * @par Python函数原型
     * getFloatOutput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getFloatOutput(address: number) -> number
     *
     * @par Lua示例
     * FloatOutput_0 = getFloatOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getFloatOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":3.3}
     * \endchinese
     *
     * \english
     * Reads the float from one of the output registers, which can also be
     * accessed by a FieldBus. Note, uses its own memory space.
     *
     * @param address Address of the register (0:47)
     * @return The value held by the register (float)
     *
     * @note The lower range of the float output registers [0:23] is reserved
     * for FieldBus/PLC interface usage. The upper range [24:47] cannot be
     * accessed by FieldBus/PLC interfaces, since it is reserved for external
     * RTDE clients.
     *
     * @par Python interface prototype
     * getFloatOutput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua interface prototype
     * getFloatOutput(address: number) -> number
     *
     * @par Lua example
     * FloatOutput_0 = getFloatOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getFloatOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":3.3}
     * \endenglish
     */
    float getFloatOutput(uint32_t address);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address 寄存器地址（0:47）
     * @param value 要设置的浮点数值
     * @return 返回0表示成功，其他为错误码
     *
     * @par Python函数原型
     * setFloatOutput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua函数原型
     * setFloatOutput(address: number, value: number) -> nil
     *
     * @par Lua示例
     * setFloatOutput(0,5.5)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setFloatOutput","params":[0,5.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Address of the register (0:47)
     * @param value Float value to set
     * @return Returns 0 on success, or an error code
     *
     * @par Python interface prototype
     * setFloatOutput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua interface prototype
     * setFloatOutput(address: number, value: number) -> nil
     *
     * @par Lua example
     * setFloatOutput(0,5.5)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setFloatOutput","params":[0,5.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setFloatOutput(uint32_t address, float value);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * 从一个输出寄存器中读取双精度浮点数。
     *
     * @param address 寄存器地址
     * @return 寄存器中保存的双精度浮点数值
     *
     * @par Python函数原型
     * getDoubleOutput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua函数原型
     * getDoubleOutput(address: number) -> number
     *
     * @par Lua示例
     * DoubleOutput_0 = getDoubleOutput(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getDoubleOutput","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     *
     * Reads the double value from one of the output registers.
     *
     * @param address Address of the register
     * @return The double value held by the register
     *
     * @par Python interface prototype
     * getDoubleOutput(self: pyaubo_sdk.RegisterControl, arg0: int) -> float
     *
     * @par Lua interface prototype
     * getDoubleOutput(address: number) -> number
     *
     * @par Lua example
     * DoubleOutput_0 = getDoubleOutput(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getDoubleOutput","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getDoubleOutput(uint32_t address);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address 寄存器地址
     * @param value 要设置的双精度浮点数值
     * @return 返回0表示成功，其他为错误码
     *
     * @par Python函数原型
     * setDoubleOutput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua函数原型
     * setDoubleOutput(address: number, value: number) -> nil
     *
     * @par Lua示例
     * setDoubleOutput(0,4.4)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setDoubleOutput","params":[0,4.4],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Address of the register
     * @param value Double value to set
     * @return Returns 0 on success, or an error code
     *
     * @par Python interface prototype
     * setDoubleOutput(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: float)
     * -> int
     *
     * @par Lua interface prototype
     * setDoubleOutput(address: number, value: number) -> nil
     *
     * @par Lua example
     * setDoubleOutput(0,4.4)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setDoubleOutput","params":[0,4.4],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setDoubleOutput(uint32_t address, double value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 用于 Modbus Slave
     *
     * @param address
     * @return
     *
     * @par Python函数原型
     * getInt16Register(self: pyaubo_sdk.RegisterControl, arg0: int) -> int
     *
     * @par Lua函数原型
     * getInt16Register(address: number) -> number
     *
     * @par Lua示例
     * Int16Register_0 = getInt16Register(0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt16Register","params":[0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Used for Modbus Slave
     *
     * @param address
     * @return
     *
     * @par Python interface prototype
     * getInt16Register(self: pyaubo_sdk.RegisterControl, arg0: int) -> int
     *
     * @par Lua interface prototype
     * getInt16Register(address: number) -> number
     *
     * @par Lua example
     * Int16Register_0 = getInt16Register(0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt16Register","params":[0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int16_t getInt16Register(uint32_t address);

    /**
     * @ingroup RegisterControl
     * \chinese
     *
     * @param address 寄存器地址
     * @param value 要设置的值
     * @return 返回0表示成功，其他为错误码
     *
     * @par Python函数原型
     * setInt16Register(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: int)
     * -> int
     *
     * @par Lua函数原型
     * setInt16Register(address: number, value: number) -> nil
     *
     * @par Lua示例
     * setInt16Register(0,4.4)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt16Register","params":[0,0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     *
     * @param address Register address
     * @param value Value to set
     * @return Returns 0 on success, otherwise error code
     *
     * @par Python interface prototype
     * setInt16Register(self: pyaubo_sdk.RegisterControl, arg0: int, arg1: int)
     * -> int
     *
     * @par Lua interface prototype
     * setInt16Register(address: number, value: number) -> nil
     *
     * @par Lua example
     * setInt16Register(0,4.4)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt16Register","params":[0,0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setInt16Register(uint32_t address, int16_t value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取 Int16 寄存器的某个bit的状态
     *
     * @param address: Int16 寄存器地址
     * @param bit_offset: 寄存器中的bit偏移，0 ~ 15
     * @return 指定bit的状态，true表示1，false表示0或参数无效
     *
     * @par Python函数原型
     * getInt16RegisterBit(self: pyaubo_sdk.RegisterControl, address: int,
     * bit_offset: int) -> bool
     *
     * @par Lua函数原型
     * getInt16RegisterBit(address: number, bit_offset: number) -> boolean
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt16RegisterBit","params":[1,
     * 5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Get the status of a specific bit in an Int16 register
     *
     * @param address Int16 register address
     * @param bit_offset Bit offset in the register, 0 ~ 15
     * @return Status of the specified bit, true for 1, false for 0 or invalid
     * parameters
     *
     * @par Python interface prototype
     * getInt16RegisterBit(self: pyaubo_sdk.RegisterControl, address: int,
     * bit_offset: int) -> bool
     *
     * @par Lua interface prototype
     * getInt16RegisterBit(address: number, bit_offset: number) -> boolean
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt16RegisterBit","params":[1,
     * 5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool getInt16RegisterBit(uint32_t address, uint8_t bit_offset);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置 Int16 寄存器的某个bit的状态
     *
     * @param address: Int16 寄存器地址
     * @param bit_offset: 寄存器中的bit偏移，0 ~ 15
     * @param value: 要设置的值，true表示置1，false表示清0
     * @return 成功返回0，失败返回错误码
     *
     * @par Python函数原型
     * setInt16RegisterBit(self: pyaubo_sdk.RegisterControl, address: int,
     * bit_offset: int, value: bool) -> int
     *
     * @par Lua函数原型
     * setInt16RegisterBit(address: number, bit_offset: number, value: boolean)
     * -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt16RegisterBit","params":[1,
     * 5, true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set the status of a specific bit in an Int16 register
     *
     * @param address Int16 register address
     * @param bit_offset Bit offset in the register, 0 ~ 15
     * @param value Value to set, true to set to 1, false to clear to 0
     * @return Returns 0 on success, error code on failure
     *
     * @par Python interface prototype
     * setInt16RegisterBit(self: pyaubo_sdk.RegisterControl, address: int,
     * bit_offset: int, value: bool) -> int
     *
     * @par Lua interface prototype
     * setInt16RegisterBit(address: number, bit_offset: number, value: boolean)
     * -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt16RegisterBit","params":[1,
     * 5, true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setInt16RegisterBit(uint32_t address, uint8_t bit_offset, bool value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 具名变量是否存在
     *
     * @param key 变量名
     * @return
     *
     * @par Lua函数原型
     * hasNamedVariable(key: string) -> boolean
     *
     * @par Lua示例
     * NamedVariable = hasNamedVariable("custom")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.hasNamedVariable","params":["custom"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endchinese
     * \english
     * Whether the named variable exists
     *
     * @param key Variable name
     * @return
     *
     * @par Lua interface prototype
     * hasNamedVariable(key: string) -> boolean
     *
     * @par Lua example
     * NamedVariable = hasNamedVariable("custom")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.hasNamedVariable","params":["custom"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":false}
     *
     * \endenglish
     */
    bool hasNamedVariable(const std::string &key);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取具名变量的类型
     *
     * @param key
     * @return
     *
     * @par Lua函数原型
     * getNamedVariableType(key: string) -> string
     *
     * @par Lua示例
     * NamedVariableType = getNamedVariableType("custom")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getNamedVariableType","params":["custom"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"NONE"}
     *
     * \endchinese
     * \english
     * Get the type of a named variable
     *
     * @param key
     * @return
     *
     * @par Lua interface prototype
     * getNamedVariableType(key: string) -> string
     *
     * @par Lua example
     * NamedVariableType = getNamedVariableType("custom")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getNamedVariableType","params":["custom"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"NONE"}
     *
     * \endenglish
     */
    std::string getNamedVariableType(const std::string &key);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 具名变量是否更新
     *
     * @param key
     * @param since
     * @return
     *
     * @par Python函数原型
     * variableUpdated(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int)
     * -> bool
     *
     * @par Lua函数原型
     * variableUpdated(key: string, since: number) -> boolean
     *
     * @par Lua示例
     * Variable_Updated = variableUpdated("custom" , 0)
     *
     * \endchinese
     *
     * \english
     * Whether the named variable has been updated
     *
     * @param key
     * @param since
     * @return
     *
     * @par Python interface prototype
     * variableUpdated(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int)
     * -> bool
     *
     * @par Lua interface prototype
     * variableUpdated(key: string, since: number) -> boolean
     *
     * @par Lua example
     * Variable_Updated = variableUpdated("custom" , 0)
     *
     * \endchinese
     */
    bool variableUpdated(const std::string &key, uint64_t since);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getBool(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: bool) -> bool
     *
     * @par Lua函数原型
     * getBool(key: string, default_value: boolean) -> boolean
     *
     * @par Lua示例
     * Bool_var = getBool("custom",false)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getBool","params":["custom",false],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getBool(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: bool) -> bool
     *
     * @par Lua interface prototype
     * getBool(key: string, default_value: boolean) -> boolean
     *
     * @par Lua example
     * Bool_var = getBool("custom",false)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getBool","params":["custom",false],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":true}
     *
     * \endenglish
     */
    bool getBool(const std::string &key, bool default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setBool(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: bool) -> int
     *
     * @par Lua函数原型
     * setBool(key: string, value: boolean) -> nil
     *
     * @par Lua示例
     * setBool("custom",true)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setBool","params":["custom",true],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return Returns 0 on success, otherwise error code
     *
     * @par Python interface prototype
     * setBool(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: bool) -> int
     *
     * @par Lua interface prototype
     * setBool(key: string, value: boolean) -> nil
     *
     * @par Lua example
     * setBool("custom",true)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setBool","params":["custom",true],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setBool(const std::string &key, bool value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getVecChar(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[str])
     * -> List[str]
     *
     * @par Lua函数原型
     * getVecChar(key: string, default_value: table) -> table
     *
     * @par Lua示例
     * VecChar = getVecChar("custom",{})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecChar","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0,1,0]}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getVecChar(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[str])
     * -> List[str]
     *
     * @par Lua interface prototype
     * getVecChar(key: string, default_value: table) -> table
     *
     * @par Lua example
     * VecChar = getVecChar("custom",{})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecChar","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0,1,0]}
     *
     * \endenglish
     */
    std::vector<char> getVecChar(const std::string &key,
                                 const std::vector<char> &default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setVecChar(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[str])
     * -> int
     *
     * @par Lua函数原型
     * setVecChar(key: string, value: table) -> nil
     *
     * @par Lua示例
     * setVecChar("custom",{0,1,0})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecChar","params":["custom",[0,1,0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return Returns 0 on success, otherwise error code
     *
     * @par Python interface prototype
     * setVecChar(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[str])
     * -> int
     *
     * @par Lua interface prototype
     * setVecChar(key: string, value: table) -> nil
     *
     * @par Lua example
     * setVecChar("custom",{0,1,0})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecChar","params":["custom",[0,1,0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setVecChar(const std::string &key, const std::vector<char> &value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int) -> int
     *
     * @par Lua函数原型
     * getInt32(key: string, default_value: number) -> number
     *
     * @par Lua示例
     * Int32 = getInt32("custom",0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt32","params":["custom",0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":6}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int) -> int
     *
     * @par Lua interface prototype
     * getInt32(key: string, default_value: number) -> number
     *
     * @par Lua example
     * Int32 = getInt32("custom",0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getInt32","params":["custom",0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":6}
     *
     * \endenglish
     */
    int getInt32(const std::string &key, int default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int) -> int
     *
     * @par Lua函数原型
     * setInt32(key: string, value: number) -> nil
     *
     * @par Lua示例
     * setInt32("custom",6)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt32","params":["custom",6],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python interface prototype
     * setInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int) -> int
     *
     * @par Lua interface prototype
     * setInt32(key: string, value: number) -> nil
     *
     * @par Lua example
     * setInt32("custom",6)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setInt32","params":["custom",6],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setInt32(const std::string &key, int value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getVecInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[int])
     * -> List[int]
     *
     * @par Lua函数原型
     * getVecInt32(key: string, default_value: table) -> table
     *
     * @par Lua示例
     * VecInt32 = getVecInt32("custom",{})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecInt32","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[1,2,3,4]}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getVecInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[int])
     * -> List[int]
     *
     * @par Lua interface prototype
     * getVecInt32(key: string, default_value: table) -> table
     *
     * @par Lua example
     * VecInt32 = getVecInt32("custom",{})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecInt32","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[1,2,3,4]}
     *
     * \endenglish
     */
    std::vector<int32_t> getVecInt32(const std::string &key,
                                     const std::vector<int32_t> &default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setVecInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[int])
     * -> int
     *
     * @par Lua函数原型
     * setVecInt32(key: string, value: table) -> nil
     *
     * @par Lua示例
     * setVecInt32("custom",{1,2,3,4})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecInt32","params":["custom",[1,2,3,4]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python interface prototype
     * setVecInt32(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: List[int])
     * -> int
     *
     * @par Lua interface prototype
     * setVecInt32(key: string, value: table) -> nil
     *
     * @par Lua example
     * setVecInt32("custom",{1,2,3,4})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecInt32","params":["custom",[1,2,3,4]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setVecInt32(const std::string &key, const std::vector<int32_t> &value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) ->
     * float
     *
     * @par Lua函数原型
     * getFloat(key: string, default_value: number) -> number
     *
     * @par Lua示例
     * var_Float = getFloat("custom",0.0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getFloat","params":["custom",0.0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":4.400000095367432}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) ->
     * float
     *
     * @par Lua interface prototype
     * getFloat(key: string, default_value: number) -> number
     *
     * @par Lua example
     * var_Float = getFloat("custom",0.0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getFloat","params":["custom",0.0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":4.400000095367432}
     *
     * \endenglish
     */
    float getFloat(const std::string &key, float default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) -> int
     *
     * @par Lua函数原型
     * setFloat(key: string, value: number) -> nil
     *
     * @par Lua示例
     * setFloat("custom",4.4)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setFloat","params":["custom",4.4],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python interface prototype
     * setFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) -> int
     *
     * @par Lua interface prototype
     * setFloat(key: string, value: number) -> nil
     *
     * @par Lua example
     * setFloat("custom",4.4)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setFloat","params":["custom",4.4],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setFloat(const std::string &key, float value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getVecFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> List[float]
     *
     * @par Lua函数原型
     * getVecFloat(key: string, default_value: table) -> table
     *
     * @par Lua示例
     * VecFloat = getVecFloat("custom",{})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecFloat","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.10000000149011612,3.299999952316284]}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getVecFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> List[float]
     *
     * @par Lua interface prototype
     * getVecFloat(key: string, default_value: table) -> table
     *
     * @par Lua example
     * VecFloat = getVecFloat("custom",{})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecFloat","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.0,0.10000000149011612,3.299999952316284]}
     *
     * \endenglish
     */
    std::vector<float> getVecFloat(const std::string &key,
                                   const std::vector<float> &default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setVecFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> int
     *
     * @par Lua函数原型
     * setVecFloat(key: string, value: table) -> nil
     *
     * @par Lua示例
     * setVecFloat("custom", {0.0,0.1,3.3})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecFloat","params":["custom",[0.0,0.1,3.3]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python interface prototype
     * setVecFloat(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> int
     *
     * @par Lua interface prototype
     * setVecFloat(key: string, value: table) -> nil
     *
     * @par Lua example
     * setVecFloat("custom", {0.0,0.1,3.3})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecFloat","params":["custom",[0.0,0.1,3.3]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setVecFloat(const std::string &key, const std::vector<float> &value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) ->
     * float
     *
     * @par Lua函数原型
     * getDouble(key: string, default_value: number) -> number
     *
     * @par Lua示例
     * var_Double = getDouble("custom",0.0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getDouble","params":["custom",0.0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) ->
     * float
     *
     * @par Lua interface prototype
     * getDouble(key: string, default_value: number) -> number
     *
     * @par Lua example
     * var_Double = getDouble("custom",0.0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getDouble","params":["custom",0.0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0.0}
     *
     * \endenglish
     */
    double getDouble(const std::string &key, double default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) ->
     * int
     *
     * @par Lua函数原型
     * setDouble(key: string, value: number) -> nil
     *
     * @par Lua示例
     * setDouble("custom",6.6)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setDouble","params":["custom",6.6],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python interface prototype
     * setDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: float) ->
     * int
     *
     * @par Lua interface prototype
     * setDouble(key: string, value: number) -> nil
     *
     * @par Lua example
     * setDouble("custom",6.6)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setDouble","params":["custom",6.6],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setDouble(const std::string &key, double value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getVecDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> List[float]
     *
     * @par Lua函数原型
     * getVecDouble(key: string, default_value: table) -> table
     *
     * @par Lua示例
     * VecDouble = getVecDouble("custom",{})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecDouble","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[0.1,0.2,0.3]}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getVecDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> List[float]
     *
     * @par Lua interface prototype
     * getVecDouble(key: string, default_value: table) -> table
     *
     * @par Lua example
     * VecDouble = getVecDouble("custom",{})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getVecDouble","params":["custom",[]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[0.1,0.2,0.3]}
     *
     * \endenglish
     */
    std::vector<double> getVecDouble(const std::string &key,
                                     const std::vector<double> &default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setVecDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> int
     *
     * @par Lua函数原型
     * setVecDouble(key: string, value: table) -> nil
     *
     * @par Lua示例
     * setVecDouble("custom",{0.1,0.2,0.3})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecDouble","params":["custom",[0.1,0.2,0.3]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python interface prototype
     * setVecDouble(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * List[float]) -> int
     *
     * @par Lua interface prototype
     * setVecDouble(key: string, value: table) -> nil
     *
     * @par Lua example
     * setVecDouble("custom",{0.1,0.2,0.3})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setVecDouble","params":["custom",[0.1,0.2,0.3]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setVecDouble(const std::string &key, const std::vector<double> &value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取变量值
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python函数原型
     * getString(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: str) -> str
     *
     * @par Lua函数原型
     * getString(key: string, default_value: string) -> string
     *
     * @par Lua示例
     * var_String = getString("custom","")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getString","params":["custom",""],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"test"}
     *
     * \endchinese
     * \english
     * Get variable value
     *
     * @param key
     * @param default_value
     * @return
     *
     * @par Python interface prototype
     * getString(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: str) -> str
     *
     * @par Lua interface prototype
     * getString(key: string, default_value: string) -> string
     *
     * @par Lua example
     * var_String = getString("custom","")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getString","params":["custom",""],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"test"}
     *
     * \endenglish
     */
    std::string getString(const std::string &key,
                          const std::string &default_value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置/更新变量值
     *
     * @param key
     * @param value
     * @return
     *
     * @par Python函数原型
     * setString(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * setString(key: string, value: string) -> nil
     *
     * @par Lua示例
     * setString("custom","test")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.setString","params":["custom","test"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set or update the variable value
     *
     * @param key
     * @param value
     * @return Returns 0 on success, otherwise error code
     *
     * @par Python interface prototype
     * setString(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: str) -> int
     *
     * @par Lua interface prototype
     * setString(key: string, value: string) -> nil
     *
     * @par Lua example
     * setString("custom","test")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.setString","params":["custom","test"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int setString(const std::string &key, const std::string &value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 清除变量
     *
     * @param key
     * @return
     *
     * @par Python函数原型
     * clearNamedVariable(self: pyaubo_sdk.RegisterControl, arg0: str) -> int
     *
     * @par Lua函数原型
     * clearNamedVariable(key: string) -> nil
     *
     * @par Lua示例
     * clearNamedVariable("custom")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.clearNamedVariable","params":["custom"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endchinese
     * \english
     * Clear variable
     *
     * @param key
     * @return
     *
     * @par Python interface prototype
     * clearNamedVariable(self: pyaubo_sdk.RegisterControl, arg0: str) -> int
     *
     * @par Lua interface prototype
     * clearNamedVariable(key: string) -> nil
     *
     * @par Lua example
     * clearNamedVariable("custom")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.clearNamedVariable","params":["custom"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     *
     * \endenglish
     */
    int clearNamedVariable(const std::string &key);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置看门狗
     *
     * 看门狗被触发之后控制器会执行对应的动作，并自动删除看门狗
     *
     * @param key
     * @param timeout 超时时间，单位秒(s)，超时时间最小为 0.1s
     * @param action
     *   NONE (0): 无动作
     *   PAUSE(1): 暂停运行时
     *   STOP (2): 停止运行时/停止机器人运动
     *   PROTECTIVE_STOP (3): 触发防护停止
     * @return
     * \endchinese
     * \english
     * Set the watchdog
     *
     * After the watchdog is triggered, the controller will perform the
     * corresponding action and automatically delete the watchdog.
     *
     * @param key
     * @param timeout Timeout in seconds (s), minimum timeout is 0.1s
     * @param action
     *   NONE (0): No action
     *   PAUSE(1): Pause runtime
     *   STOP (2): Stop runtime/stop robot motion
     *   PROTECTIVE_STOP (3): Trigger protective stop
     * @return
     * \endenglish
     */
    int setWatchDog(const std::string &key, double timeout, int action);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取看门狗动作
     *
     * @param key
     * @return
     * \endchinese
     * \english
     * Get the watchdog action
     *
     * @param key
     * @return
     * \endenglish
     */
    int getWatchDogAction(const std::string &key);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取看门狗超时时间
     *
     * @param key
     * @return
     * \endchinese
     * \english
     * Get the watchdog timeout value
     *
     * @param key
     * @return
     * \endenglish
     */
    int getWatchDogTimeout(const std::string &key);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 添加一个新的Modbus信号以供控制器监视。不需要返回响应。
     *
     * @param device_info 设备信息
     * 设备信息是RTU格式，例如："serial_port,baud,parity,data_bit,stop_bit"
     * (1)serial_port参数指定串口的名称，例如，在Linux上为"/dev/ttyS0"或"/dev/ttyUSB0"，在Windows上为"\.\COM10"
     * (2)baud参数指定通信的波特率，例如9600、19200、57600、115200等
     * (3)parity参数指定奇偶校验方式，N表示无校验，E表示偶校验，O表示奇校验
     * (4)data_bit参数指定数据位数，允许的值为5、6、7和8
     * (5)stop_bit参数指定停止位数，允许的值为1和2
     *
     * 设备信息是TCP格式，例如："ip address,port"
     * (1)ip address参数指定服务器的IP地址
     * (2)port参数指定服务器监听的端口号
     * @param slave_number 通常不使用，设置为255即可，但可以在0到255之间自由选择
     * @param signal_address
     * 指定新信号应该反映的线圈或寄存器的地址。请参考Modbus单元的配置以获取此信息。
     * @param signal_type 指定要添加的信号类型。0 = 数字输入，1 = 数字输出，2 =
     * 寄存器输入，3 = 寄存器输出。
     * @param signal_name
     * 唯一标识信号的名词。如果提供的字符串与已添加的信号相等，则新信号将替换旧信号。字符串的长度不能超过20个字符。
     * @param sequential_mode
     * 设置为True会强制Modbus客户端在发送下一个请求之前等待响应。某些fieldbus单元需要此模式。可选参数。
     * @return
     *
     * @par Python函数原型
     * modbusAddSignal(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int,
     * arg2: int, arg3: int, arg4: str, arg5: bool) -> int
     *
     * @par Lua函数原型
     * modbusAddSignal(device_info: string, slave_number: number,
     * signal_address: number, signal_type: number, signal_name: string,
     * sequential_mode: boolean) -> nil
     *
     * @par Lua示例
     * modbusAddSignal("/dev/ttyRobotTool,115200,N,8,1", 1, signal_address:
     * number, 264, "Modbus_0", false)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusAddSignal","params":["/dev/ttyRobotTool,115200,N,8,1",1,264,3,"Modbus_0",false],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Adds a new modbus signal for the controller to supervise. Expects no
     * response.
     *
     * @param device_info is rtu format.
     * eg,"serial_port,baud,parity,data_bit,stop_bit"
     * (1)The serial_port argument specifies the name of the serial port eg. On
     * Linux ,"/dev/ttyS0" or "/dev/ttyUSB0". On Windows, "\.\COM10". (2)The
     * baud argument specifies the baud rate of the communication, eg. 9600,
     * 19200, 57600, 115200, etc. (3)parity:N for none,E for even,O for odd.
     * (4)data_bit:The data_bits argument specifies the number of bits of data,
     * the allowed values are 5, 6, 7 and 8. (5)stop_bit:The stop_bits argument
     * specifies the bits of stop, the allowed values are 1 and 2.
     *
     * device_info is tcp format.eg,"ip address,port"
     * (1)The ip address parameter specifies the ip address of the server
     * (2)The port parameter specifies the port number that the server is
     * listening on.
     * @param slave_number An integer normally not used and set to 255, but is a
     * free choice between 0 and 255.
     * @param signal_address An integer specifying the address of the either the
     * coil or the register that this new signal should reflect. Consult the
     * configuration of the modbus unit for this information.
     * @param signal_type An integer specifying the type of signal to add. 0 =
     * digital input, 1 = digital output, 2 = register input and 3 = register
     * output.
     * @param signal_name  A string uniquely identifying the signal. If a string
     * is supplied which is equal to an already added signal, the new signal
     * will replace the old one. The length of the string cannot exceed 20
     * characters.
     * @param sequential_mode Setting to True forces the modbus client to wait
     * for a response before sending the next request. This mode is required by
     * some fieldbus units (Optional).
     * @return
     *
     * @par Python interface prototype
     * modbusAddSignal(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: int,
     * arg2: int, arg3: int, arg4: str, arg5: bool) -> int
     *
     * @par Lua interface prototype
     * modbusAddSignal(device_info: string, slave_number: number,
     * signal_address: number, signal_type: number, signal_name: string,
     * sequential_mode: boolean) -> nil
     *
     * @par Lua example
     * modbusAddSignal("/dev/ttyRobotTool,115200,N,8,1", 1, signal_address:
     * number, 264, "Modbus_0", false)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusAddSignal","params":["/dev/ttyRobotTool,115200,N,8,1",1,264,3,"Modbus_0",false],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusAddSignal(const std::string &device_info, int slave_number,
                        int signal_address, int signal_type,
                        const std::string &signal_name, bool sequential_mode);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 为指定Modbus寄存器信号创建固定读取分组，优化连续地址的批量读取效率
     *
     * 功能：根据传入的起始信号名定位到对应的16位Modbus寄存器地址，
     * 并基于该起始地址和连续数量创建“不可扩展的固定分组”，该分组会被独立管理，
     * 不会与其他普通分组合并或扩展，适用于需要稳定、原子化读取的连续寄存器地址段；
     * 固定分组创建后，对该段地址的读取操作会严格按照分组范围执行，避免因动态分组扩展导致的读取范围变化。
     *
     * @param signal_name
     * 起始信号名（作为固定分组的基准信号，需为已通过modbusAddSignal创建的16位Modbus寄存器信号，
     * 支持保持寄存器/输入寄存器类型，不支持数字量信号）
     * @param count 固定分组包含的连续信号（寄存器）数量（大于等于1）：
     * - 值为1：
     * 仅包含起始信号对应的单个寄存器地址（取消包含该信号的固定分组）；
     * - 值>1：
     * 从起始信号地址开始的连续count个寄存器地址，需确保地址连续且不超出设备支持范围；
     *
     * @return 成功返回0，失败返回错误码。
     *
     * @note
     * 1. 该接口仅针对16位Modbus寄存器信号（signal_type为2/3）生效；
     * 2. 单个固定分组的最大连续数量受设备限制（默认最大30个）；
     * 3. 重复为同一信号创建固定分组会覆盖原有配置（以最后一次的count值为准）。
     *
     * @par Python接口原型
     * addFixedModbusGroup(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * int) -> int
     *
     * @par Lua接口原型
     * addFixedModbusGroup(signal_name: string, count: number) -> nil
     *
     * @par Lua示例
     * -- 为起始信号"Modbus_0"创建包含10个连续寄存器的固定分组
     * addFixedModbusGroup("Modbus_0", 10)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.addFixedModbusGroup","params":["Modbus_0",10],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Create a fixed read group for the specified Modbus register signal to
     * optimize the batch reading efficiency of continuous addresses
     *
     * Function: Locate the address of the corresponding 16-bit Modbus register
     * according to the input start signal name, and create a "non-extensible
     * fixed group" based on the start address and continuous count. This group
     * will be managed independently, and will not be merged or expanded with
     * other normal groups. It is suitable for continuous register address
     * segments that require stable and atomic reading; After the fixed group is
     * created, the read operation for this address segment will be strictly
     * executed according to the group range, avoiding read range changes caused
     * by dynamic group expansion.
     *
     * @param signal_name
     * Start signal name (used as the reference signal for the fixed group, must
     * be a 16-bit Modbus register signal created via modbusAddSignal,
     * supporting holding register/input register types, not supporting digital
     * signals)
     * @param count Number of continuous signals (registers) contained in the
     * fixed group (greater than or equal to 1):
     * - Value = 1: Only include the single register address
     * corresponding to the start signal (cancel the fixed group containing this
     * signal);
     * - Value > 1: Continuous count register addresses starting
     * from the start signal address, ensure the addresses are continuous and do
     * not exceed the device support range;
     *
     * @return Returns 0 on success, returns an error code on failure.
     *
     * @note
     * 1. This interface only takes effect for 16-bit Modbus register signals
     * (signal_type is 2/3);
     * 2. The maximum continuous count of a single fixed group is limited by the
     * device (default maximum 30);
     * 3. Repeated creation of a fixed group for the same start signal will
     * overwrite the original configuration (the last count value shall
     * prevail).
     *
     * @par Python interface prototype
     * addFixedModbusGroup(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * int) -> int
     *
     * @par Lua interface prototype
     * addFixedModbusGroup(signal_name: string, count: number) -> nil
     *
     * @par Lua example
     * -- Create a fixed group containing 10 consecutive registers for the start
     * signal "Modbus_0" addFixedModbusGroup("Modbus_0", 10)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.addFixedModbusGroup","params":["Modbus_0",10],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int addFixedModbusGroup(const std::string &signal_name, int count);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 删除指定名称的信号。
     *
     * @param signal_name 要删除的信号的名称
     * @return
     *
     * @par Python函数原型
     * modbusDeleteSignal(self: pyaubo_sdk.RegisterControl, arg0: str) -> int
     *
     * @par Lua函数原型
     * modbusDeleteSignal(signal_name: string) -> nil
     *
     * @par Lua示例
     * modbusDeleteSignal("Modbus_1")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusDeleteSignal","params":["Modbus_1"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Deletes the signal identified by the supplied signal name.
     *
     * @param signal_name A string equal to the name of the signal that should
     * be deleted.
     * @return
     *
     * @par Python interface prototype
     * modbusDeleteSignal(self: pyaubo_sdk.RegisterControl, arg0: str) -> int
     *
     * @par Lua interface prototype
     * modbusDeleteSignal(signal_name: string) -> nil
     *
     * @par Lua example
     * modbusDeleteSignal("Modbus_1")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusDeleteSignal","params":["Modbus_1"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusDeleteSignal(const std::string &signal_name);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 删除所有modbus信号
     *
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusDeleteAllSignals","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Delete all modbus signals
     *
     * @return
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusDeleteAllSignals","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int modbusDeleteAllSignals();

    /**
     * @ingroup RegisterControl
     * \chinese
     * 读取特定信号的当前值。
     *
     * @param signal_name 要获取值的信号的名称
     * @return 对于数字信号：1或0。
     * 对于寄存器信号：表示为整数的寄存器值。如果值为-1，则表示该信号不存在。
     *
     * @par Python函数原型
     * modbusGetSignalStatus(self: pyaubo_sdk.RegisterControl, arg0: str) -> int
     *
     * @par Lua函数原型
     * modbusGetSignalStatus(signal_name: string) -> number
     *
     * @par Lua示例
     * var0 = modbusGetSignalStatus("Modbus_0")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalStatus","params":["Modbus_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endchinese
     * \english
     * Reads the current value of a specific signal.
     *
     * @param signal_name A string equal to the name of the signal for which the
     * value should be gotten.
     * @return An integer or a boolean. For digital signals: 1 or 0. For
     * register signals: The register value expressed as an integer. If the
     * value is -1, it means the signal does not exist.
     *
     * @par Python interface prototype
     * modbusGetSignalStatus(self: pyaubo_sdk.RegisterControl, arg0: str) -> int
     *
     * @par Lua interface prototype
     * modbusGetSignalStatus(signal_name: string) -> number
     *
     * @par Lua example
     * var0 = modbusGetSignalStatus("Modbus_0")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalStatus","params":["Modbus_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":1}
     * \endenglish
     */
    int modbusGetSignalStatus(const std::string &signal_name);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取所有信号的名字集合
     *
     * @return 所有信号的名字集合
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalNames","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":["Modbus_0"]}
     *
     * \endchinese
     * \english
     * Get the collection of all signal names
     *
     * @return Collection of all signal names
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalNames","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":["Modbus_0"]}
     *
     * \endenglish
     */
    std::vector<std::string> modbusGetSignalNames();

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取所有信号的类型集合
     *
     * @return 所有信号的类型集合
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalTypes","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[1,0,2,3]}
     *
     * \endchinese
     * \english
     * Get the collection of all signal types
     *
     * @return Collection of all signal types
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalTypes","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[1,0,2,3]}
     *
     * \endenglish
     */
    std::vector<int> modbusGetSignalTypes();

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取所有信号的数值集合
     *
     * @return 所有信号的数值集合
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalValues","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[1,1,88,33]}
     *
     * \endchinese
     * \english
     * Get the collection of all signal values
     *
     * @return Collection of all signal values
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalValues","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[1,1,88,33]}
     *
     * \endenglish
     */
    std::vector<int> modbusGetSignalValues();

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取所有信号的请求是否有错误(0:无错误,其他:有错误)集合
     *
     * @return ModbusErrorNum
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalErrors","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":[6,6,6,6]}
     *
     * \endchinese
     * \english
     * Get the error status of all signal requests (0: no error, others: error)
     * as a collection
     *
     * @return ModbusErrorNum
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalErrors","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":[6,6,6,6]}
     *
     * \endenglish
     */
    std::vector<int> modbusGetSignalErrors();

    /**
     * @ingroup RegisterControl
     * \chinese
     * 将用户指定的命令发送到指定IP地址上的Modbus单元。
     * 由于不会接收到响应，因此不能用于请求数据。
     * 用户负责提供对所提供的功能码有意义的数据。
     * 内置函数负责构建Modbus帧，因此用户不需要关心命令的长度。
     *
     * @param device_info 设备信息
     * 设备信息是RTU格式，例如："serial_port,baud,parity,data_bit,stop_bit"
     * (1)serial_port参数指定串口的名称，例如，在Linux上为"/dev/ttyS0"或"/dev/ttyUSB0"，在Windows上为"\.\COM10"
     * (2)baud参数指定通信的波特率，例如9600、19200、57600、115200等
     * (3)parity参数指定奇偶校验方式，N表示无校验，E表示偶校验，O表示奇校验
     * (4)data_bit参数指定数据位数，允许的值为5、6、7和8
     * (5)stop_bit参数指定停止位数，允许的值为1和2
     *
     * 设备信息是TCP格式，例如："ip address,port"
     * (1)ip address参数指定服务器的IP地址
     * (2)port参数指定服务器监听的端口号
     * @param slave_number 指定用于自定义命令的从站号
     * @param function_code 指定自定义命令的功能码
     *
     * Modbus功能码
     * MODBUS_FC_READ_COILS                0x01
     * MODBUS_FC_READ_DISCRETE_INPUTS      0x02
     * MODBUS_FC_READ_HOLDING_REGISTERS    0x03
     * MODBUS_FC_READ_INPUT_REGISTERS      0x04
     * MODBUS_FC_WRITE_SINGLE_COIL         0x05
     * MODBUS_FC_WRITE_SINGLE_REGISTER     0x06
     * MODBUS_FC_READ_EXCEPTION_STATUS     0x07
     * MODBUS_FC_WRITE_MULTIPLE_COILS      0x0F
     * MODBUS_FC_WRITE_MULTIPLE_REGISTERS  0x10
     * MODBUS_FC_REPORT_SLAVE_ID           0x11
     * MODBUS_FC_MASK_WRITE_REGISTER       0x16
     * MODBUS_FC_WRITE_AND_READ_REGISTERS  0x17
     *
     * @param data 必须是有效的字节值（0-255）
     * @return
     *
     * @par Python函数原型
     * modbusSendCustomCommand(self: pyaubo_sdk.RegisterControl, arg0: str,
     * arg1: int, arg2: int, arg3: List[int]) -> int
     *
     * @par Lua函数原型
     * modbusSendCustomCommand(device_info: string, slave_number: number,
     * function_code: number, data: table) -> nil
     *
     * @par Lua示例
     * modbusSendCustomCommand("/dev/ttyRobotTool,115200,N,8,1", 1, 10,
     * {1,2,0,2,4,0,0,0,0}) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSendCustomCommand","params":["/dev/ttyRobotTool,115200,N,8,1",1,10,[1,2,0,2,4,0,0,0,0]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Sends a command specified by the user to the modbus unit located on the
     * specified IP address. Cannot be used to request data, since the response
     * will not be received. The user is responsible for supplying data which
     * is meaningful to the supplied function code. The builtin function takes
     * care of constructing the modbus frame, so the user should not be
     * concerned with the length of the command.
     *
     * @param device_info is rtu format.
     * eg,"serial_port,baud,parity,data_bit,stop_bit"
     * (1)The serial_port argument specifies the name of the serial port eg. On
     * Linux ,"/dev/ttyS0" or "/dev/ttyUSB0". On Windows, "\.\COM10".
     * (2)The baud argument specifies the baud rate of the communication, eg.
     * 9600, 19200, 57600, 115200, etc.
     * (3)parity:N for none,E for even,O for odd.
     * (4)data_bit:The data_bits argument specifies the number of bits of data,
     * the allowed values are 5, 6, 7 and 8.
     * (5)stop_bit:The stop_bits argument
     * specifies the bits of stop, the allowed values are 1 and 2.
     *
     * device_info is tcp format.eg,"ip address,port"
     * (1)The ip address parameter specifies the ip address of the server
     * (2)The port parameter specifies the port number that the server is
     * listening on.
     * @param slave_number An integer specifying the slave number to use for
     * the custom command.
     * @param function_code An integer specifying the function code for the
     * custom command.
     *
     * Modbus function codes
     * MODBUS_FC_READ_COILS                0x01
     * MODBUS_FC_READ_DISCRETE_INPUTS      0x02
     * MODBUS_FC_READ_HOLDING_REGISTERS    0x03
     * MODBUS_FC_READ_INPUT_REGISTERS      0x04
     * MODBUS_FC_WRITE_SINGLE_COIL         0x05
     * MODBUS_FC_WRITE_SINGLE_REGISTER     0x06
     * MODBUS_FC_READ_EXCEPTION_STATUS     0x07
     * MODBUS_FC_WRITE_MULTIPLE_COILS      0x0F
     * MODBUS_FC_WRITE_MULTIPLE_REGISTERS  0x10
     * MODBUS_FC_REPORT_SLAVE_ID           0x11
     * MODBUS_FC_MASK_WRITE_REGISTER       0x16
     * MODBUS_FC_WRITE_AND_READ_REGISTERS  0x17
     *
     * @param data An array of integers in which each entry must be a valid
     * byte (0-255) value.
     * @return
     *
     * @par Python interface prototype
     * modbusSendCustomCommand(self: pyaubo_sdk.RegisterControl, arg0: str,
     * arg1: int, arg2: int, arg3: List[int]) -> int
     *
     * @par Lua interface prototype
     * modbusSendCustomCommand(device_info: string, slave_number: number,
     * function_code: number, data: table) -> nil
     *
     * @par Lua example
     * modbusSendCustomCommand("/dev/ttyRobotTool,115200,N,8,1", 1, 10,
     * {1,2,0,2,4,0,0,0,0}) -> nil
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSendCustomCommand","params":["/dev/ttyRobotTool,115200,N,8,1",1,10,[1,2,0,2,4,0,0,0,0]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusSendCustomCommand(const std::string &device_info,
                                int slave_number, int function_code,
                                const std::vector<uint8_t> &data);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 将选择的数字输入信号设置为“default”或“freedrive”
     *
     * @param robot_name 连接的机器人名称
     * @param signal_name 先前被添加的数字输入信号
     * @param action 操作类型。操作可以是“default”或“freedrive”
     * @return
     *
     * @par Python函数原型
     * modbusSetDigitalInputAction(self: pyaubo_sdk.RegisterControl, arg0: str,
     * arg1: str, arg2: int)
     *
     * @par Lua函数原型
     * modbusSetDigitalInputAction(robot_name: string, signal_name: string,
     * action: number) -> nil
     *
     * @par Lua示例
     * modbusSetDigitalInputAction("rob1", "Modbus_0","Handguide")
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetDigitalInputAction","params":["rob1","Modbus_0","Handguide"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Sets the selected digital input signal to either a "default" or
     * "freedrive" action.
     *
     * @param robot_name A string identifying a robot name that connected robot
     * @param signal_name A string identifying a digital input signal that was
     * previously added.
     * @param action The type of action. The action can either be "default" or
     * "freedrive". (string)
     * @return
     *
     * @par Python interface prototype
     * modbusSetDigitalInputAction(self: pyaubo_sdk.RegisterControl, arg0: str,
     * arg1: str, arg2: int)
     *
     * @par Lua interface prototype
     * modbusSetDigitalInputAction(robot_name: string, signal_name: string,
     * action: number) -> nil
     *
     * @par Lua example
     * modbusSetDigitalInputAction("rob1", "Modbus_0","Handguide")
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetDigitalInputAction","params":["rob1","Modbus_0","Handguide"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusSetDigitalInputAction(const std::string &robot_name,
                                    const std::string &signal_name,
                                    StandardInputAction action);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置 Modbus 信号输出动作
     *
     * @param robot_name
     * @param signal_name
     * @param runstate
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputRunstate","params":["rob1","Modbus_0","None"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set Modbus signal output action
     *
     * @param robot_name
     * @param signal_name
     * @param runstate
     * @return
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputRunstate","params":["rob1","Modbus_0","None"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int modbusSetOutputRunstate(const std::string &robot_name,
                                const std::string &signal_name,
                                StandardOutputRunState runstate);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置 Modbus 信号输出动作，并支持基于路点/平面/障碍物的条件阈值判断。
     *
     * 详细说明：当需要根据机器人是否到达某个路点或与某个平面/障碍物的距离来触发Modbus信号时，
     * 可通过本接口指定条件对象及阈值。在条件满足时会将指定的Modbus信号设置为对应的运行状态。
     *
     * @param robot_name 目标机器人的名称，用于标识要监听/触发条件的机器人实例
     * @param signal_name 要设置的 Modbus 信号名称（需已通过 modbusAddSignal 添加）
     * @param runstate 输出动作状态
     * @param object_type 条件对象类型：
     *                    - 1: 路点（Waypoint）
     *                    - 2: 平面（Plane）
     *                    - 3: 障碍物（Obstacle）
     * @param object_name 条件对象的名称（与对象类型配合使用，需为系统中已定义的唯一标识）
     * @param threshold 判断阈值：
     *                  - 对于路点：表示角度阈值，单位为度(°)
     *                  - 对于平面/障碍物：表示距离阈值，单位为毫米(mm)
     *
     * @return 返回操作结果码：
     *         - 0: 操作成功
     *         - 非0: 操作失败，返回具体错误码（参见系统错误码定义）
     *
     * @par Python接口原型
     * modbusSetOutputRunstate1(self: pyaubo_sdk.RegisterControl, arg0: str, arg1: str, arg2: str, arg3: int, arg4: str, arg5: int) -> int
     *
     * @par Lua接口原型
     * modbusSetOutputRunstate1(robot_name: string, signal_name: string, runstate: string, object_type: number, object_name: string, threshold: number) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputRunstate1","params":["rob1","Modbus_0","WaypointArrived",1,"P1",3],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * @note 使用说明：
     *       1. 请确保 object_name 与 object_type 对应且已在系统中定义；
     *       2. threshold 的单位依据 object_type 不同而不同，务必使用正确单位以避免触发误判；
     * \endchinese
     * \english
     * Set Modbus signal output action with optional condition checking based on
     * waypoint, plane or obstacle thresholds.
     *
     * Detailed description: Use this API to control a Modbus output signal when
     * a specified robot condition is met (for example, waypoint arrival or
     * distance to a plane/obstacle). Specify an object type, name and a
     * threshold value to enable conditional triggering. When the condition is
     * satisfied, the given Modbus signal will be set to the requested
     * runstate.
     *
     * @param robot_name The target robot name identifying which robot's
     *                   conditions to monitor.
     * @param signal_name The Modbus signal name to set (must be previously
     *                    added via modbusAddSignal).
     * @param runstate The desired output action.
     * @param object_type Condition object type: 1=Waypoint, 2=Plane, 3=Obstacle
     * @param object_name Unique identifier of the condition object
     * @param threshold Condition threshold: angle in degrees for waypoints, or
     *                  distance in millimeters for planes/obstacles
     *
     * @return Returns 0 on success, non-zero error code on failure.
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputRunstate1","params":["rob1","Modbus_0","WaypointArrived",1,"P1",3],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusSetOutputRunstate1(const std::string &robot_name,
                                 const std::string &signal_name,
                                 StandardOutputRunState runstate,
                                 int object_type,
                                 const std::string &object_name,
                                 int threshold);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 将指定名称的输出寄存器信号设置为给定的值
     *
     * @param signal_name 提前被添加的输出寄存器信号
     * @param value 必须是有效的整数，范围是 0-65535
     * @return
     *
     * @par Python函数原型
     * modbusSetOutputSignal(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * int) -> int
     *
     * @par Lua函数原型
     * modbusSetOutputSignal(signal_name: string, value: number) -> nil
     *
     * @par Lua示例
     * modbusSetOutputSignal("Modbus_0",0)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignal","params":["Modbus_0",0],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Sets the output register signal identified by the given name to the given
     * value.
     *
     * @param signal_name A string identifying an output register signal that in
     * advance has been added.
     * @param value An integer which must be a valid word (0-65535)
     * @return
     *
     * @par Python interface prototype
     * modbusSetOutputSignal(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * int) -> int
     *
     * @par Lua interface prototype
     * modbusSetOutputSignal(signal_name: string, value: number) -> nil
     *
     * @par Lua example
     * modbusSetOutputSignal("Modbus_0",0)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignal","params":["Modbus_0",0],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusSetOutputSignal(const std::string &signal_name, uint16_t value);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 将从指定名称开始的若干个连续输出寄存器信号设置为给定的值
     *
     * @param signal_name 提前被添加的输出寄存器信号的起始名称
     * @param values 整数数组，每个元素范围是 0-65535，对应连续的多个信号
     * @return
     *
     * @par Python函数原型
     * modbusSetOutputSignal1(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * list[int]) -> int
     *
     * @par Lua函数原型
     * modbusSetOutputSignal1(signal_name: string, value: table) -> nil
     *
     * @par Lua示例
     * modbusSetOutputSignal1("Modbus_0", {0, 1, 2})
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignal1","params":["Modbus_0",[0,1,2]],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Sets multiple consecutive output register signals starting from the given
     * name to the given values.
     *
     * @param signal_name A string identifying the starting output register
     * signal that in advance has been added.
     * @param values An array of integers where each element must be a valid
     * word (0-65535), corresponding to multiple consecutive signals
     * @return
     *
     * @par Python interface prototype
     * modbusSetOutputSignal1(self: pyaubo_sdk.RegisterControl, arg0: str, arg1:
     * list[int]) -> int
     *
     * @par Lua interface prototype
     * modbusSetOutputSignal1(signal_name: string, value: table) -> nil
     *
     * @par Lua example
     * modbusSetOutputSignal1("Modbus_0", {0, 1, 2})
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignal1","params":["Modbus_0",[0,1,2]],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusSetOutputSignal1(const std::string &signal_name,
                               const std::vector<uint16_t> &values);

    /**
     * \chinese
     * 将指定名称的输出寄存器信号设置为给定的值，并且带超时判断
     *
     * @param signal_name 提前被添加的输出寄存器信号
     * @param value 必须是有效的整数，范围是 0-65535
     * @param timeout 超时时间，单位秒
     * @return
     *
     * @par Python函数原型
     * modbusSetOutputSignalWithTimeout(self: pyaubo_sdk.RegisterControl, arg0:
     * str, arg1: int, arg2: double) -> int
     *
     * @par Lua函数原型
     * modbusSetOutputSignalWithTimeout(signal_name: string, value: number,
     * timeout: number) -> nil
     *
     * @par Lua示例
     * modbusSetOutputSignalWithTimeout("Modbus_0",0,0.5)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignalWithTimeout","params":["Modbus_0",0,0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Sets the output register signal identified by the given name to the
     * given, with timeout value.
     *
     * @param signal_name A string identifying an output register signal that in
     * advance has been added.
     * @param value An integer which must be a valid word (0-65535)
     * @param timeout seconds
     * @return
     *
     * @par Python interface prototype
     * modbusSetOutputSignalWithTimeout(self: pyaubo_sdk.RegisterControl, arg0:
     * str, arg1: int, arg2: timeout) -> int
     *
     * @par Lua interface prototype
     * modbusSetOutputSignalWithTimeout(signal_name: string, value: number,
     * timeout: number) -> nil
     *
     * @par Lua example
     * modbusSetOutputSignalWithTimeout("Modbus_0",0,0.5)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignalWithTimeout","params":["Modbus_0",0,0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusSetOutputSignalWithTimeout(const std::string &signal_name,
                                         uint16_t value, double timeout);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置modbus信号输出脉冲(仅支持线圈输出类型)
     *
     * @param signal_name: 提前被添加的输出寄存器信号
     * @param value: 必须是有效的整数，范围是 0-65535
     * @param duration: 信号持续时间，单位为秒
     * @return
     *
     * @par Python函数原型
     * modbusSetOutputSignalPulse(self: pyaubo_sdk.RegisterControl, arg0: str,
     * arg1: int, arg2 double) -> int
     *
     * @par Lua函数原型
     * modbusSetOutputSignalPulse(signal_name: string, value: number, duration:
     * number) -> nil
     *
     * @par Lua示例
     * modbusSetOutputSignalPulse("Modbus_0",1,0.5)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignalPulse","params":["Modbus_0",1,0.5],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Set modbus signal output pulse (only supports coil output type)
     *
     * @param signal_name: A string identifying an output register signal that
     * has been added in advance.
     * @param value: An integer which must be a valid word (0-65535)
     * @param duration: Duration of the signal, in seconds
     * @return
     *
     * @par Python interface prototype
     * modbusSetOutputSignalPulse(self: pyaubo_sdk.RegisterControl, arg0: str,
     * arg1: int, arg2: double) -> int
     *
     * @par Lua interface prototype
     * modbusSetOutputSignalPulse(signal_name: string, value: number, duration:
     * number) -> nil
     *
     * @par Lua example
     * modbusSetOutputSignalPulse("Modbus_0",1,0.5)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetOutputSignalPulse","params":["Modbus_0",1,0.5],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int modbusSetOutputSignalPulse(const std::string &signal_name,
                                   uint16_t value, double duration);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 设置机器人向Modbus控制器发送请求的频率，用于读取或写入信号值
     *
     * @param signal_name 提前被添加的输出数字信号
     * @param update_frequency 更新频率（以赫兹为单位），范围是0-125
     * @return
     *
     * @par Python函数原型
     * modbusSetSignalUpdateFrequency(self: pyaubo_sdk.RegisterControl, arg0:
     * str, arg1: int) -> int
     *
     * @par Lua函数原型
     * modbusSetSignalUpdateFrequency(signal_name: string, update_frequency:
     * number) -> nil
     *
     * @par Lua示例
     * modbusSetSignalUpdateFrequency("Modbus_0",1)
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetSignalUpdateFrequency","params":["Modbus_0",1],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     * \english
     * Sets the frequency with which the robot will send requests to the Modbus
     * controller to either read or write the signal value.
     *
     * @param signal_name A string identifying an output digital signal that
     * in advance has been added.
     * @param update_frequency An integer in the range 0-125 specifying the
     * update frequency in Hz.
     * @return
     *
     * @par Python interface prototype
     * modbusSetSignalUpdateFrequency(self: pyaubo_sdk.RegisterControl, arg0:
     * str, arg1: int) -> int
     *
     * @par Lua interface prototype
     * modbusSetSignalUpdateFrequency(signal_name: string, update_frequency:
     * number) -> nil
     *
     * @par Lua example
     * modbusSetSignalUpdateFrequency("Modbus_0",1)
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusSetSignalUpdateFrequency","params":["Modbus_0",1],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     */
    int modbusSetSignalUpdateFrequency(const std::string &signal_name,
                                       int update_frequency);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取指定 modbus 信号索引，从0开始，不能存在则返回-1
     *
     * @param signal_name
     * @return
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalIndex","params":["Modbus_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the index of the specified modbus signal, starting from 0. Returns -1
     * if it does not exist.
     *
     * @param signal_name
     * @return
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalIndex","params":["Modbus_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int modbusGetSignalIndex(const std::string &signal_name);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取指定 modbus 信号的错误状态
     *
     * @param signal_name
     * @return 返回错误代码 ModbusErrorNum
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalError","params":["Modbus_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":6}
     * \endchinese
     * \english
     * Get the error status of the specified modbus signal
     *
     * @param signal_name
     * @return Returns error code ModbusErrorNum
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.modbusGetSignalError","params":["Modbus_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":6}
     * \endenglish
     */
    int modbusGetSignalError(const std::string &signal_name);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 获取指定 modbus 设备的连接状态
     *
     * @param device_name
     * 设备名是TCP格式，"ip:port", 例如："127.0.0.1:502" \n
     * 设备名是RTU格式，"serial_port", 例如："/dev/ttyUSB0" \n
     *
     * @return
     * 0: 表示设备处于连接状态
     * -1: 表示设备不存在
     * -2: 表示设备处于断开状态
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"RegisterControl.getModbusDeviceStatus","params":["172.16.26.248:502"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endchinese
     * \english
     * Get the connection status of the specified modbus device
     *
     * @param device_name
     * Device name in TCP format: "ip:port", e.g. "127.0.0.1:502" \n
     * Device name in RTU format: "serial_port", e.g. "/dev/ttyUSB0" \n
     *
     * @return
     * 0: Device is connected
     * -1: Device does not exist
     * -2: Device is disconnected
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"RegisterControl.getModbusDeviceStatus","params":["172.16.26.248:502"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     *
     * \endenglish
     */
    int getModbusDeviceStatus(const std::string &device_name);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 将某个 modbus 寄存器信号作为编码器
     *
     * @param encoder_id 不能为0
     * @param signal_name modbus 信号名字，必须为寄存器类型
     * @return
     * \endchinese
     * \english
     * Use a modbus register signal as an encoder
     *
     * @param encoder_id Must not be 0
     * @param signal_name Name of the modbus signal, must be of register type
     * @return
     * \endenglish
     */
    int addModbusEncoder(int encoder_id, int range_id,
                         const std::string &signal_name);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 添加Int32寄存器的虚拟编码器
     *
     * @param encoder_id 编码器ID
     * @param range_id 范围ID
     * @param key 变量名
     * @return
     * \endchinese
     * \english
     * Add a virtual encoder for an Int32 register
     *
     * @param encoder_id Encoder ID
     * @param range_id Range ID
     * @param key Variable name
     * @return
     * \endenglish
     */
    int addInt32RegEncoder(int encoder_id, int range_id,
                           const std::string &key);

    /**
     * @ingroup RegisterControl
     * \chinese
     * 删除虚拟编码器
     *
     * @param encoder_id
     * @return
     * \endchinese
     * \english
     * Delete virtual encoder
     *
     * @param encoder_id
     * @return
     * \endenglish
     */
    int deleteVirtualEncoder(int encoder_id);

protected:
    void *d_;
};
using RegisterControlPtr = std::shared_ptr<RegisterControl>;

} // namespace common_interface
} // namespace arcs

#endif // AUBO_SDK_REGISTER_CONTROL_INTERFACE_H
