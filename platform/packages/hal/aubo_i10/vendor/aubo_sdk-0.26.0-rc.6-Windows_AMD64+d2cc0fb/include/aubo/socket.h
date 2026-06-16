/** @file  socket.h
 *  @brief socket通信
 */
#ifndef AUBO_SDK_SOCKET_INTERFACE_H
#define AUBO_SDK_SOCKET_INTERFACE_H

#include <vector>
#include <memory>

#include <aubo/type_def.h>
#include <aubo/global_config.h>

namespace arcs {
namespace common_interface {


/**
 * @defgroup Socket Socket (socket网络通信)
 * \~chinese 串口通信
 * \~english Socket control
 */
class ARCS_ABI_EXPORT Socket
{
public:
    Socket();
    virtual ~Socket();

    /**
     * @ingroup Socket
     * \english
     * Open TCP/IP ethernet communication socket
     *
     * Instruction
     *
     * @param address
     * @param port
     * @param socket_name
     * @return
     * 
     * @par Python function prototype
     * socketOpen(self: pyaubo_sdk.Socket, arg0: str, arg1: int, arg2: str) -> int
     *
     * @par Lua function prototype
     * socketOpen(address: string, port: number, socket_name: string) -> nil
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Socket.socketOpen","params":["172.16.26.248",8000,"socket_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
    *  \chinese
     * 打开TCP/IP以太网通信socket
     *
     * 指令
     *
     * @param address 地址
     * @param port 端口
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketOpen(self: pyaubo_sdk.Socket, arg0: str, arg1: int, arg2: str) -> int
     *
     * @par Lua函数原型
     * socketOpen(address: string, port: number, socket_name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Socket.socketOpen","params":["172.16.26.248",8000,"socket_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int socketOpen(const std::string &address, int port,
                   const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Closes TCP/IP socket communication
     * Closes down the socket connection to the server.
     *
     * Instruction
     *
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketClose(self: pyaubo_sdk.Socket, arg0: str) -> int
     *
     * @par Lua function prototype
     * socketClose(socket_name: string) -> nil
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Socket.socketClose","params":["socket_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     * \chinese
     * 关闭TCP/IP socket 通信
     * 关闭与服务器的 socket 连接。
     *
     * 指令
     *
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketClose(self: pyaubo_sdk.Socket, arg0: str) -> int
     *
     * @par Lua函数原型
     * socketClose(socket_name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Socket.socketClose","params":["socket_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int socketClose(const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Reads a number of ascii formatted floats from the socket. A maximum
     * of 30 values can be read in one command.
     * A list of numbers read (list of floats, length=number+1)
     *
     * Result will be stored in a register named reg_key. Use getFloatVec
     * to retrieve data
     *
     * @param number
     * @param variable
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketReadAsciiFloat(self: pyaubo_sdk.Socket, arg0: int, arg1: str, arg2:
     * str) -> int
     *
     * @par Lua function prototype
     * socketReadAsciiFloat(number: number, variable: string, socket_name:
     * string) -> number
     * \endenglish
     * \chinese
     * 从socket读取指定数量的ASCII格式浮点数。一次最多可读取30个值。
     * 读取到的数字列表（浮点数列表，长度=number+1）
     *
     * 结果将存储在名为reg_key的寄存器中。使用getFloatVec获取数据
     *
     * @param number 数量
     * @param variable 变量名
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketReadAsciiFloat(self: pyaubo_sdk.Socket, arg0: int, arg1: str, arg2:
     * str) -> int
     *
     * @par Lua函数原型
     * socketReadAsciiFloat(number: number, variable: string, socket_name:
     * string) -> number
     * \endchinese
     */
    int socketReadAsciiFloat(int number, const std::string &variable,
                             const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Reads a number of 32 bit integers from the socket. Bytes are in
     * network byte order. A maximum of 30 values can be read in one
     * command.
     * A list of numbers read (list of ints, length=number+1)
     *
     * Instruction
     *
     * std::vector<int>
     *
     * @param number
     * @param variable
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketReadBinaryInteger(self: pyaubo_sdk.Socket, arg0: int, arg1: str,
     * arg2: str) -> int
     *
     * @par Lua function prototype
     * socketReadBinaryInteger(number: number, variable: string, socket_name:
     * string) -> number
     * \endenglish
     * \chinese
     * 从socket读取指定数量的32位整数。字节为网络字节序。一次最多可读取30个值。
     * 读取到的数字列表（整数列表，长度=number+1）
     *
     * 指令
     *
     * std::vector<int>
     *
     * @param number 数量
     * @param variable 变量名
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketReadBinaryInteger(self: pyaubo_sdk.Socket, arg0: int, arg1: str,
     * arg2: str) -> int
     *
     * @par Lua函数原型
     * socketReadBinaryInteger(number: number, variable: string, socket_name:
     * string) -> number
     * \endchinese
     */
    int socketReadBinaryInteger(int number, const std::string &variable,
                                const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Reads a number of bytes from the socket. Bytes are in network byte
     * order. A maximum of 30 values can be read in one command.
     * A list of numbers read (list of ints, length=number+1)
     *
     * Instruction
     *
     * std::vector<char>
     *
     * @param number
     * @param variable
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketReadByteList(self: pyaubo_sdk.Socket, arg0: int, arg1: str, arg2:
     * str) -> int
     *
     * @par Lua function prototype
     * socketReadByteList(number: number, variable: string, socket_name: string)
     * -> number
     * \endenglish
     * \chinese
     * 从socket读取指定数量的字节。字节为网络字节序。一次最多可读取30个值。
     * 读取到的数字列表（整数列表，长度=number+1）
     *
     * 指令
     *
     * std::vector<char>
     *
     * @param number 数量
     * @param variable 变量名
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketReadByteList(self: pyaubo_sdk.Socket, arg0: int, arg1: str, arg2:
     * str) -> int
     *
     * @par Lua函数原型
     * socketReadByteList(number: number, variable: string, socket_name: string)
     * -> number
     * \endchinese
     */
    int socketReadByteList(int number, const std::string &variable,
                           const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Reads all data from the socket and returns the data as a string.
     * Bytes are in network byte order.
     *
     * The optional parameters "prefix" and "suffix", can be used to express
     * what is extracted from the socket. The "prefix" specifies the start
     * of the substring (message) extracted from the socket. The data up to
     * the end of the "prefix" will be ignored and removed from the socket.
     * The "suffix" specifies the end of the substring (message) extracted
     * from the socket. Any remaining data on the socket, after the "suffix",
     * will be preserved. E.g. if the socket server sends a string
     * "noise>hello<", the controller can receive the "hello" by calling this
     * script function with the prefix=">" and suffix="<". By using the
     * "prefix" and "suffix" it is also possible send multiple string to the
     * controller at once, because the suffix defines where the message ends.
     * E.g. sending ">hello<>world<"
     *
     * Instruction
     *
     * std::string
     *
     * @param variable
     * @param socket_name
     * @param prefix
     * @param suffix
     * @param interpret_escape
     * @return
     *
     * @par Python function prototype
     * socketReadString(self: pyaubo_sdk.Socket, arg0: str, arg1: str, arg2:
     * str, arg3: str, arg4: bool) -> int
     *
     * @par Lua function prototype
     * socketReadString(variable: string, socket_name: string, prefix: string,
     * suffix: string, interpret_escape: boolean) -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Socket.socketReadString","params":["camera","socket_0","","",false],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     * \chinese
     * 从socket读取所有数据并将其作为字符串返回。
     * 字节为网络字节序。
     *
     * 可选参数"prefix"和"suffix"可用于指定从socket中提取的内容。
     * "prefix"指定提取子字符串（消息）的起始位置。直到"prefix"结尾的数据将被忽略并从socket中移除。
     * "suffix"指定提取子字符串（消息）的结束位置。"suffix"之后的任何剩余数据将保留在socket中。
     * 例如，如果socket服务器发送字符串"noise>hello<"，控制器可以通过调用此脚本函数并设置prefix=">"和suffix="<"来接收"hello"。
     * 通过使用"prefix"和"suffix"，还可以一次向控制器发送多条字符串，因为"suffix"定义了消息的结束位置。例如发送">hello<>world<"
     *
     * 指令
     *
     * std::string
     *
     * @param variable 变量名
     * @param socket_name 套接字名称
     * @param prefix 前缀
     * @param suffix 后缀
     * @param interpret_escape 是否解释转义字符
     * @return 返回值
     *
     * @par Python函数原型
     * socketReadString(self: pyaubo_sdk.Socket, arg0: str, arg1: str, arg2:
     * str, arg3: str, arg4: bool) -> int
     *
     * @par Lua函数原型
     * socketReadString(variable: string, socket_name: string, prefix: string,
     * suffix: string, interpret_escape: boolean) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Socket.socketReadString","params":["camera","socket_0","","",false],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int socketReadString(const std::string &variable,
                         const std::string &socket_name = "socket_0",
                         const std::string &prefix = "",
                         const std::string &suffix = "",
                         bool interpret_escape = false);

    /**
     * @ingroup Socket
     * \english
     * Reads all data from the socket and returns the data as a vector of chars.
     *
     * Instruction
     * std::vector<char>
     *
     * @param variable
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketReadAllString(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * socketReadAllString(variable: string, socket_name: string) -> number
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Socket.socketReadAllString","params":["camera","socket_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     * \chinese
     * 从socket读取所有数据并将其作为char向量返回。
     *
     * 指令
     * std::vector<char>
     *
     * @param variable 变量名
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketReadAllString(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * socketReadAllString(variable: string, socket_name: string) -> number
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Socket.socketReadAllString","params":["camera","socket_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int socketReadAllString(const std::string &variable,
                            const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Sends a byte to the server
     * Sends the byte <value> through the socket. Expects no response. Can
     * be used to send special ASCII characters; 10 is newline, 2 is start of
     * text, 3 is end of text.
     *
     * Instruction
     *
     * @param value
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketSendByte(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * socketSendByte(value: string, socket_name: string) -> nil
     *
     * \endenglish
     * \chinese
     * 发送一个字节到服务器
     * 通过socket发送字节<value>，不期望响应。可用于发送特殊ASCII字符；10为换行符，2为文本开始，3为文本结束。
     *
     * 指令
     *
     * @param value 字节值
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketSendByte(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * socketSendByte(value: string, socket_name: string) -> nil
     *
     * \endchinese
     */
    int socketSendByte(char value, const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Sends an int (int32_t) to the server
     * Sends the int <value> through the socket. Send in network byte order.
     * Expects no response
     *
     * Instruction
     *
     * @param value
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketSendInt(self: pyaubo_sdk.Socket, arg0: int, arg1: str) -> int
     *
     * @par Lua function prototype
     * socketSendInt(value: number, socket_name: string) -> nil
     *
     * \endenglish
     * \chinese
     * 发送一个int（int32_t）到服务器
     * 通过socket发送int <value>，以网络字节序发送。不期望响应。
     *
     * 指令
     *
     * @param value 整数值
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketSendInt(self: pyaubo_sdk.Socket, arg0: int, arg1: str) -> int
     *
     * @par Lua函数原型
     * socketSendInt(value: number, socket_name: string) -> nil
     *
     * \endchinese
     */
    int socketSendInt(int value, const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Sends a string with a newline character to the server
     * Sends the string <str> through the socket in ASCII coding. Expects no
     * response.
     *
     * Instruction
     *
     * @param str
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketSendLine(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * socketSendLine(str: string, socket_name: string) -> nil
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Socket.socketSendLine","params":["abcd","socket_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     * \chinese
     * 发送带有换行符的字符串到服务器.
     * 通过socket以ASCII编码发送字符串<str>，不期望响应。
     *
     * 指令
     *
     * @param str 字符串
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketSendLine(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * socketSendLine(str: string, socket_name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Socket.socketSendLine","params":["abcd","socket_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int socketSendLine(const std::string &str,
                       const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Sends a string to the server
     * Sends the string <str> through the socket in ASCII coding. Expects no
     * response.
     *
     * Instruction
     *
     * @param str
     * @param socket_name
     * @return
     *
     * @par Python function prototype
     * socketSendString(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua function prototype
     * socketSendString(str: string, socket_name: string) -> nil
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"Socket.socketSendString","params":["abcd","socket_0"],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endenglish
     * \chinese
     * 发送字符串到服务器
     * 通过socket以ASCII编码发送字符串<str>，不期望响应。
     *
     * 指令
     *
     * @param str 字符串
     * @param socket_name 套接字名称
     * @return 返回值
     *
     * @par Python函数原型
     * socketSendString(self: pyaubo_sdk.Socket, arg0: str, arg1: str) -> int
     *
     * @par Lua函数原型
     * socketSendString(str: string, socket_name: string) -> nil
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"Socket.socketSendString","params":["abcd","socket_0"],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":0}
     * \endchinese
     */
    int socketSendString(const std::string &str,
                         const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \english
     * Sends all data in the given vector of chars to the server.
     *
     * @param is_check Whether to check the sending status
     * @param str The data to send as a vector of chars
     * @param socket_name The name of the socket
     * @return Status code
     *
     * @par Python function prototype
     * socketSendAllString(self: pyaubo_sdk.Socket, arg0: bool, arg1: List[str], arg2: str) -> int
     *
     * @par Lua function prototype
     * socketSendAllString(is_check: boolean, str: table, socket_name: string) -> nil
     * \endenglish
     * \chinese
     * 发送给定char向量中的所有数据到服务器。
     *
     * @param is_check 是否检查发送状态
     * @param str 要发送的数据，char向量
     * @param socket_name 套接字名称
     * @return 状态码
     *
     * @par Python函数原型
     * socketSendAllString(self: pyaubo_sdk.Socket, arg0: bool, arg1: List[str], arg2: str) -> int
     *
     * @par Lua函数原型
     * socketSendAllString(is_check: boolean, str: table, socket_name: string) -> nil
     * \endchinese
     */
    int socketSendAllString(bool is_check, const std::vector<char> &str,
                            const std::string &socket_name = "socket_0");

    /**
     * @ingroup Socket
     * \~chinese 检测 socket 连接是否成功 \~english Check if the socket is connected
     * @brief socketHasConnected
     * @param socket_name
     *
     * @return
     *
     *  @par Python函数原型
     * socketHasConnected(self: pyaubo_sdk.Socket, arg0: str) -> bool
     *
     *  @par Lua函数原型
     * socketHasConnected(socket_name: string) -> boolean
     */
    bool socketHasConnected(const std::string &socket_name = "socket_0");

protected:
    void *d_;
};
using SocketPtr = std::shared_ptr<Socket>;

} // namespace common_interface
} // namespace arcs
#endif
