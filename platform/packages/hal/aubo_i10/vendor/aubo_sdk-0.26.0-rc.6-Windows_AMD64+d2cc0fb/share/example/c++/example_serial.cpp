#include "aubo_sdk/rpc.h"
#include "aubo/serial.h"
#include "aubo/register_control.h"
#include <iostream>
#include <thread>
#include <chrono>

#define MAX_RETRIES 10

#define LOCAL_IP "127.0.0.1"

#define SERIAL_PORT      "/dev/ttyS0"
#define SERIAL_BAUD      9600
#define SERIAL_STOP_BITS 1.0
#define SERIAL_EVEN      0
#define SERIAL_NAME      "test_com"

using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;

template <typename T>
void printVec(const std::vector<T> &param, const std::string &name)
{
    std::cout << "@:" << name << std::endl;
    for (size_t i = 0; i < param.size(); i++) {
        std::cout << param.at(i) << ",";
    }
    std::cout << std::endl;
}

//串口打开
bool testSerialOpen(RpcClientPtr rpc_cli)
{
    std::string device = SERIAL_PORT;
    int baud = SERIAL_BAUD;
    float stop_bits = SERIAL_STOP_BITS;
    int even = SERIAL_EVEN;
    int open_result = rpc_cli->getSerial()->serialOpen(device, baud, stop_bits,
                                                       even, SERIAL_NAME);
    if (open_result == 0) {
        std::cout << "Serial port opened successfully." << std::endl;
        return true;
    } else if (open_result == -13) {
        std::cout << "Serial port already exists." << std::endl;
        return true;
    } else {
        std::cout << "Failed to open serial port, ret: " << open_result
                  << std::endl;
        return false;
    }
}

//发送字节
void testSerialSendByte(RpcClientPtr rpc_cli)
{
    char send_byte = 'A';
    int send_byte_result =
        rpc_cli->getSerial()->serialSendByte(send_byte, SERIAL_NAME);
    if (send_byte_result == 0) {
        std::cout << "Byte sent successfully: " << send_byte << std::endl;
    } else {
        std::cout << "Failed to send byte, ret: " << send_byte_result
                  << std::endl;
    }
}

//发送整数
void testSerialSendInt(RpcClientPtr rpc_cli)
{
    int send_int = 9;
    int send_int_result =
        rpc_cli->getSerial()->serialSendInt(send_int, SERIAL_NAME);
    if (send_int_result == 0) {
        std::cout << "Integer sent successfully: " << send_int << std::endl;
    } else {
        std::cout << "Failed to send integer, ret: " << send_int_result
                  << std::endl;
    }
}

//发送字符串
void testSerialSendString(RpcClientPtr rpc_cli)
{
    std::string send_string = "Hello, Serial!";
    int send_string_result =
        rpc_cli->getSerial()->serialSendString(send_string, SERIAL_NAME);

    if (send_string_result == 0) {
        std::cout << "String sent successfully: " << send_string << std::endl;
    } else {
        std::cout << "Failed to send string, ret: " << send_string_result
                  << std::endl;
    }
}

// 发送所有字符串（字符数组）
void testSerialSendAllString(RpcClientPtr rpc_cli)
{
    // 如果需要校验，则设置为true,会自动计算CRC校验和并附加到数据末尾（大端序）
    bool is_check = false; // 是否校验

    // 对应组包后的完整字符数组:
    // ['H','e','l','l','o',' ','W','o','r','l','d','!']
    std::vector<char> send_data = { 'H', 'e', 'l', 'l', 'o', ' ',
                                    'W', 'o', 'r', 'l', 'd', '!' };

    int send_all_string_result = rpc_cli->getSerial()->serialSendAllString(
        is_check, send_data, SERIAL_NAME);

    if (send_all_string_result == 0) {
        std::cout << "All string sent successfully. Data: ";
        for (char c : send_data) {
            std::cout << c;
        }
        std::cout << std::endl;
    } else {
        std::cout << "Failed to send all string, ret: "
                  << send_all_string_result << std::endl;
    }
}

// 发送带换行符的字符串
void testSerialSendLine(RpcClientPtr rpc_cli)
{
    // 对应组包后的完整字符数组:
    // ['T','h','i','s',' ','i','s',' ','a',' ','l','i','n','e',' ',
    // 'w','i','t','h',' ','n','e','w','l','i','n','e','\r','\n']
    std::string send_line = "This is a line with newline";

    int send_line_result =
        rpc_cli->getSerial()->serialSendLine(send_line, SERIAL_NAME);

    if (send_line_result == 0) {
        std::cout << "Line sent successfully: " << send_line
                  << " (with newline)" << std::endl;
    } else {
        std::cout << "Failed to send line, ret: " << send_line_result
                  << std::endl;
    }
}

//读取字节
void testSerialReadByte(RpcClientPtr rpc_cli)
{
    std::string read_byte_var = "read_byte_var";
    int read_byte_result = -1;
    int i = MAX_RETRIES;
    while (i--) {
        read_byte_result =
            rpc_cli->getSerial()->serialReadByte(read_byte_var, SERIAL_NAME);

        if (read_byte_result == 0) {
            auto value =
                rpc_cli->getRegisterControl()->getInt32(read_byte_var, 0);

            std::cout << "serialReadByte --> value: " << value << std::endl;
            std::cout << "Byte read successfully. " << std::endl;

            break;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }

    if (read_byte_result < 0) {
        std::cout << "Failed to read byte, ret: " << read_byte_result
                  << std::endl;
    }
}

//读取字节列表
void testSerialReadByteList(RpcClientPtr rpc_cli)
{
    int number = 5;
    std::string read_byte_list_var = "read_byte_list_var";

    std::vector<char> default_value(0);
    int read_byte_list_result = -1;
    int i = MAX_RETRIES;
    while (i--) {
        read_byte_list_result = rpc_cli->getSerial()->serialReadByteList(
            number, read_byte_list_var, SERIAL_NAME);

        if (read_byte_list_result == 0) {
            auto value = rpc_cli->getRegisterControl()->getVecChar(
                read_byte_list_var, default_value);

            std::cout << "serialReadByteList --> value: " << std::endl;
            printVec(value, "value");
            std::cout << "Byte list read successfully." << std::endl;
            break;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }

    if (read_byte_list_result < 0) {
        std::cout << "Failed to read byte list, ret: " << read_byte_list_result
                  << std::endl;
    }
}

//读取字符串
void testSerialReadString(RpcClientPtr rpc_cli)
{
    std::string read_string_var = "read_string_var";

    std::string prefix = "";   // 定义要读取数据的开始标识
    std::string suffix = "\n"; // 定义要读取数据的结束标识
    bool interpret_escape = false;

    std::string default_value = "";
    int read_string_result = -1;
    int i = MAX_RETRIES;
    while (i--) {
        read_string_result = rpc_cli->getSerial()->serialReadString(
            read_string_var, SERIAL_NAME, prefix, suffix, interpret_escape);

        if (read_string_result == 0) {
            auto value = rpc_cli->getRegisterControl()->getString(
                read_string_var, default_value);

            std::cout << "testSerialReadString --> value: " << value
                      << std::endl;

            std::cout << "String read successfully." << std::endl;
            break;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }

    if (read_string_result < 0) {
        std::cout << "Failed to read string, ret: " << read_string_result
                  << std::endl;
    }
}

//串口关闭
void testSerialClose(RpcClientPtr rpc_cli)
{
    int close_result = rpc_cli->getSerial()->serialClose(SERIAL_NAME);
    if (close_result == 0) {
        std::cout << "Serial port closed successfully." << std::endl;
    } else {
        std::cout << "Failed to close serial port, ret: " << close_result
                  << std::endl;
    }
}

int main(int argc, char **argv)
{
    auto rpc_cli = std::make_shared<RpcClient>();
    // 接口调用: 设置 RPC 超时
    rpc_cli->setRequestTimeout(3000);
    // 接口调用: 连接到 RPC 服务
    rpc_cli->connect(LOCAL_IP, 30004);
    // 接口调用: 登录
    rpc_cli->login("aubo", "123456");

    // 打开串口
    if (!testSerialOpen(rpc_cli)) {
        return 1;
    }

    testSerialSendByte(rpc_cli);
    // testSerialSendInt(rpc_cli);
    // testSerialSendString(rpc_cli);
    // testSerialSendAllString(rpc_cli);
    // testSerialSendLine(rpc_cli);

    // testSerialReadByte(rpc_cli);
    // testSerialReadByteList(rpc_cli);
    // testSerialReadString(rpc_cli);

    //关闭串口
    testSerialClose(rpc_cli);

    // 接口调用: 退出登录
    rpc_cli->logout();
    // 接口调用: 断开连接
    rpc_cli->disconnect();

    return 0;
}
