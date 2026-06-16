/** @file  serial.h
 *  @brief 串口通信
 */
#ifndef AUBO_SDK_SERIAL_INTERFACE_H
#define AUBO_SDK_SERIAL_INTERFACE_H

#include <vector>
#include <memory>

#include <aubo/type_def.h>
#include <aubo/global_config.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup Serial Serial (串口通信)
 * \~chinese 串口通信
 * \~english Serial control
 */
class ARCS_ABI_EXPORT Serial
{
public:
    Serial();
    virtual ~Serial();

    /**
     * @ingroup Serial
     * \chinese
     * 打开TCP/IP以太网通信串口
     *
     * @param device 设备名
     * @param baud 波特率
     * @param stop_bits 停止位
     * @param even 校验位
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialOpen(self: pyaubo_sdk.Serial, arg0: str, arg1: int, arg2: float,
     * arg3: int, arg4: str) -> int
     *
     * @par Lua函数原型
     * serialOpen(device: string, baud: number, stop_bits: number, even: number,
     * serial_name: string) -> nil
     * \endchinese
     * \english
     * Open TCP/IP ethernet communication serial
     *
     * @param device
     * @param baud
     * @param stop_bits
     * @param even
     * @param serial_name
     * @return
     *
     * @par Python function prototype
     * serialOpen(self: pyaubo_sdk.Serial, arg0: str, arg1: int, arg2: float,
     * arg3: int, arg4: str) -> int
     *
     * @par Lua function prototype
     * serialOpen(device: string, baud: number, stop_bits: number, even: number,
     * serial_name: string) -> nil
     * \endenglish
     */

    int serialOpen(const std::string &device, int baud, float stop_bits,
                   int even, const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     * 关闭TCP/IP串口通信
     * 关闭与服务器的串口连接。
     *
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialClose(self: pyaubo_sdk.Serial, arg0: str) -> int
     *
     * @par Lua函数原型
     * serialClose(serial_name: string) -> nil
     * \endchinese
     * \english
     * Close TCP/IP serial communication
     * Close down the serial connection to the server.
     *
     * @param serial_name
     * @return
     *
     * @par Python function prototype
     * serialClose(self: pyaubo_sdk.Serial, arg0: str) -> int
     *
     * @par Lua function prototype
     * serialClose(serial_name: string) -> nil
     * \endenglish
     */
    int serialClose(const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     * 从串口读取指定数量的字节。字节为网络字节序。一次最多可读取30个值。
     *
     * @param variable 变量
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialReadByte(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * serialReadByte(variable: string, serial_name: string) -> number
     * \endchinese
     * \english
     * Reads a number of bytes from the serial. Bytes are in network byte
     * order. A maximum of 30 values can be read in one command.
     *
     * @param variable
     * @param serial_name
     * @return
     *
     * @par Python function prototype
     * serialReadByte(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * serialReadByte(variable: string, serial_name: string) -> number
     * \endenglish
     */
    int serialReadByte(const std::string &variable,
                       const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     * 从串口读取指定数量的字节。字节为网络字节序。一次最多可读取30个值。
     * 返回读取到的数字列表（int列表，长度=number+1）。
     *
     * @param number 读取的字节数
     * @param variable 变量
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialReadByteList(self: pyaubo_sdk.Serial, arg0: int, arg1: str, arg2: str) -> int
     *
     * @par Lua函数原型
     * serialReadByteList(number: number, variable: string, serial_name: string) -> number
     * \endchinese
     * \english
     * Reads a number of bytes from the serial. Bytes are in network byte
     * order. A maximum of 30 values can be read in one command.
     * A list of numbers read (list of ints, length=number+1)
     *
     * @param number Number of bytes to read
     * @param variable
     * @param serial_name Serial port name
     * @return Return value
     *
     * @par Python function prototype
     * serialReadByteList(self: pyaubo_sdk.Serial, arg0: int, arg1: str, arg2: str) -> int
     *
     * @par Lua function prototype
     * serialReadByteList(number: number, variable: string, serial_name: string) -> number
     * \endenglish
     */
    int serialReadByteList(int number, const std::string &variable,
                           const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     * 从串口读取所有数据，并将数据作为字符串返回。
     * 字节为网络字节序。
     *
     * 可选参数 "prefix" 和 "suffix" 用于指定从串口提取的内容。
     * "prefix" 指定提取子串（消息）的起始位置。直到 "prefix" 结束的数据会被忽略并从串口移除。
     * "suffix" 指定提取子串（消息）的结束位置。串口中 "suffix" 之后的剩余数据会被保留。
     * 例如，如果串口服务器发送字符串 "noise>hello<"，控制器可以通过设置 prefix=">" 和 suffix="<" 来接收 "hello"。
     * 通过使用 "prefix" 和 "suffix"，还可以一次向控制器发送多条字符串，因为 "suffix" 定义了消息的结束位置。
     * 例如发送 ">hello<>world<"
     *
     * @param variable 变量
     * @param serial_name 串口名称
     * @param prefix 前缀
     * @param suffix 后缀
     * @param interpret_escape 是否解释转义字符
     * @return 返回值
     *
     * @par Python函数原型
     * serialReadString(self: pyaubo_sdk.Serial, arg0: str, arg1: str, arg2: str, arg3: str, arg4: bool) -> int
     *
     * @par Lua函数原型
     * serialReadString(variable: string, serial_name: string, prefix: string, suffix: string, interpret_escape: boolean) -> number
     * \endchinese
     * \english
     * Reads all data from the serial and returns the data as a string.
     * Bytes are in network byte order.
     *
     * The optional parameters "prefix" and "suffix", can be used to express
     * what is extracted from the serial. The "prefix" specifies the start
     * of the substring (message) extracted from the serial. The data up to
     * the end of the "prefix" will be ignored and removed from the serial.
     * The "suffix" specifies the end of the substring (message) extracted
     * from the serial. Any remaining data on the serial, after the "suffix",
     * will be preserved. E.g. if the serial server sends a string
     * "noise>hello<", the controller can receive the "hello" by calling this
     * script function with the prefix=">" and suffix="<". By using the
     * "prefix" and "suffix" it is also possible send multiple string to the
     * controller at once, because the suffix defines where the message ends.
     * E.g. sending ">hello<>world<"
     *
     * @param variable
     * @param serial_name
     * @param prefix
     * @param suffix
     * @param interpret_escape
     * @return
     *
     * @par Python function prototype
     * serialReadString(self: pyaubo_sdk.Serial, arg0: str, arg1: str, arg2: str, arg3: str, arg4: bool) -> int
     *
     * @par Lua function prototype
     * serialReadString(variable: string, serial_name: string, prefix: string, suffix: string, interpret_escape: boolean) -> number
     * \endenglish
     */
    int serialReadString(const std::string &variable,
                         const std::string &serial_name = "serial_0",
                         const std::string &prefix = "",
                         const std::string &suffix = "",
                         bool interpret_escape = false);

    /**
     * @ingroup Serial
     * \chinese
     * 发送一个字节到服务器
     * 通过串口发送字节 <value>。不期望有响应。可用于发送特殊的ASCII字符；10为换行符，2为文本开始，3为文本结束。
     *
     * @param value 字节值
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialSendByte(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * serialSendByte(value: string, serial_name: string) -> nil
     * \endchinese
     * \english
     * Sends a byte to the server
     * Sends the byte <value> through the serial. Expects no response. Can
     * be used to send special ASCII characters; 10 is newline, 2 is start of
     * text, 3 is end of text.
     *
     * @param value
     * @param serial_name
     * @return
     *
     * @par Python function prototype
     * serialSendByte(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * serialSendByte(value: string, serial_name: string) -> nil
     * \endenglish
     */
    int serialSendByte(char value, const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     * 发送一个整数（int32_t）到服务器
     * 通过串口发送整数 <value>。以网络字节序发送。不期望有响应。
     *
     * @param value 整数值
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialSendInt(self: pyaubo_sdk.Serial, arg0: int, arg1: str) -> int
     *
     * @par Lua函数原型
     * serialSendInt(value: number, serial_name: string) -> nil
     * \endchinese
     * \english
     * Sends an int (int32_t) to the server
     * Sends the int <value> through the serial. Send in network byte order.
     * Expects no response.
     *
     * @param value
     * @param serial_name
     * @return
     *
     * @par Python function prototype
     * serialSendInt(self: pyaubo_sdk.Serial, arg0: int, arg1: str) -> int
     *
     * @par Lua function prototype
     * serialSendInt(value: number, serial_name: string) -> nil
     * \endenglish
     */
    int serialSendInt(int value, const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     * 发送带有换行符的字符串到服务器
     * 以ASCII编码通过串口发送字符串<str>，并在末尾添加换行符。不期望有响应。
     *
     * @param str 字符串
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialSendLine(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * serialSendLine(str: string, serial_name: string) -> nil
     * \endchinese
     * \english
     * Sends a string with a newline character to the server 
     * Sends the string <str> through the serial in ASCII coding, appending a newline at the end. Expects no response.
     *
     * @param str
     * @param serial_name
     * @return
     *
     * @par Python function prototype
     * serialSendLine(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * serialSendLine(str: string, serial_name: string) -> nil
     * \endenglish
     */
    int serialSendLine(const std::string &str,
                       const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     * 发送字符串到服务器
     * 以ASCII编码通过串口发送字符串<str>。不期望有响应。
     *
     * @param str 字符串
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialSendString(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * serialSendString(str: string, serial_name: string) -> nil
     * \endchinese
     * \english
     * Sends a string to the server
     * Sends the string <str> through the serial in ASCII coding. Expects no
     * response.
     *
     * @param str
     * @param serial_name
     * @return
     *
     * @par Python function prototype
     * serialSendString(self: pyaubo_sdk.Serial, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * serialSendString(str: string, serial_name: string) -> nil
     * \endenglish
     */
    int serialSendString(const std::string &str,
                         const std::string &serial_name = "serial_0");

    /**
     * @ingroup Serial
     * \chinese
     *
     * @param is_check 是否校验
     * @param str 字符串数组
     * @param serial_name 串口名称
     * @return 返回值
     *
     * @par Python函数原型
     * serialSendAllString(self: pyaubo_sdk.Serial, arg0: bool, arg1: List[str], arg2: str) -> int
     *
     * @par Lua函数原型
     * serialSendAllString(is_check: boolean, str: table, serial_name: string) -> nil
     * \endchinese
     * \english
     *
     * @param is_check Whether to check
     * @param str Array of strings
     * @param serial_name Serial port name
     * @return Return value
     *
     * @par Python function prototype
     * serialSendAllString(self: pyaubo_sdk.Serial, arg0: bool, arg1: List[str], arg2: str) -> int
     *
     * @par Lua function prototype
     * serialSendAllString(is_check: boolean, str: table, serial_name: string) -> nil
     * \endenglish
     */
    int serialSendAllString(bool is_check, const std::vector<char> &str,
                            const std::string &serial_name = "serial_0");

protected:
    void *d_;
};
using SerialPtr = std::shared_ptr<Serial>;

} // namespace common_interface
} // namespace arcs
#endif
