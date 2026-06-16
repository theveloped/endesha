/** @file  system_info.h
 *  @brief 获取系统信息接口，如接口板的版本号、示教器软件的版本号
 */
#ifndef AUBO_SDK_SYSTEM_INFO_INTERFACE_H
#define AUBO_SDK_SYSTEM_INFO_INTERFACE_H

#include <stdint.h>
#include <string>
#include <memory>

#include <aubo/global_config.h>

namespace arcs {
namespace common_interface {

/**
 * @defgroup SystemInfo SystemInfo (系统信息)
 * \~chinese 系统信息
 * \~english SystemInfo
 */
class ARCS_ABI_EXPORT SystemInfo
{
public:
    SystemInfo();
    virtual ~SystemInfo();

    /**
     * @ingroup SystemInfo
     * \chinese
     * 获取控制器软件版本号
     *
     * @return 返回控制器软件版本号
     *
     * @par Python函数原型
     * getControlSoftwareVersionCode(self: pyaubo_sdk.SystemInfo) -> int
     *
     * @par Lua函数原型
     * getControlSoftwareVersionCode() -> number
     *
     * @par C++示例
     * @code
     * int control_version =
     * rpc_cli->getSystemInfo()->getControlSoftwareVersionCode();
     * @endcode
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareVersionCode","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":28003}
     *
     * \endchinese
     * \english
     * Get the controller software version code
     *
     * @return Returns the controller software version code
     *
     * @par Python prototype
     * getControlSoftwareVersionCode(self: pyaubo_sdk.SystemInfo) -> int
     *
     * @par Lua prototype
     * getControlSoftwareVersionCode() -> number
     *
     * @par C++ example
     * @code
     * int control_version =
     * rpc_cli->getSystemInfo()->getControlSoftwareVersionCode();
     * @endcode
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareVersionCode","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":28003}
     *
     * \endenglish
     */
    int getControlSoftwareVersionCode();

    /**
     * @ingroup SystemInfo
     * \chinese
     * 获取完整控制器软件版本号
     *
     * @return 返回完整控制器软件版本号
     *
     * @par Python函数原型
     * getControlSoftwareFullVersion(self: pyaubo_sdk.SystemInfo) -> str
     *
     * @par Lua函数原型
     * getControlSoftwareFullVersion() -> string
     *
     * @par C++示例
     * @code
     * std::string control_version =
     * rpc_cli->getSystemInfo()->getControlSoftwareFullVersion();
     * @endcode
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareFullVersion","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"0.31.0-alpha.16+20alc76"}
     *
     * \endchinese
     * \english
     * Get the full controller software version
     *
     * @return Returns the full controller software version
     *
     * @par Python prototype
     * getControlSoftwareFullVersion(self: pyaubo_sdk.SystemInfo) -> str
     *
     * @par Lua prototype
     * getControlSoftwareFullVersion() -> string
     *
     * @par C++ example
     * @code
     * std::string control_version =
     * rpc_cli->getSystemInfo()->getControlSoftwareFullVersion();
     * @endcode
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareFullVersion","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"0.31.0-alpha.16+20alc76"}
     *
     * \endenglish
     */
    std::string getControlSoftwareFullVersion();

    /**
     * @ingroup SystemInfo
     * \chinese
     * 获取接口版本号
     *
     * @return 返回接口版本号
     *
     * @par Python函数原型
     * getInterfaceVersionCode(self: pyaubo_sdk.SystemInfo) -> int
     *
     * @par Lua函数原型
     * getInterfaceVersionCode() -> number
     *
     * @par C++示例
     * @code
     * int interface_version =
     * rpc_cli->getSystemInfo()->getInterfaceVersionCode();
     * @endcode
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"SystemInfo.getInterfaceVersionCode","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":22003}
     *
     * \endchinese
     * \english
     * Get the interface version code
     *
     * @return Returns the interface version code
     *
     * @par Python prototype
     * getInterfaceVersionCode(self: pyaubo_sdk.SystemInfo) -> int
     *
     * @par Lua prototype
     * getInterfaceVersionCode() -> number
     *
     * @par C++ example
     * @code
     * int interface_version =
     * rpc_cli->getSystemInfo()->getInterfaceVersionCode();
     * @endcode
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"SystemInfo.getInterfaceVersionCode","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":22003}
     *
     * \endenglish
     */
    int getInterfaceVersionCode();

    /**
     * @ingroup SystemInfo
     * \chinese
     * 获取控制器软件构建时间
     *
     * @return 返回控制器软件构建时间
     *
     * @par Python函数原型
     * getControlSoftwareBuildDate(self: pyaubo_sdk.SystemInfo) -> str
     *
     * @par Lua函数原型
     * getControlSoftwareBuildDate() -> string
     *
     * @par C++示例
     * @code
     * std::string build_date =
     * rpc_cli->getSystemInfo()->getControlSoftwareBuildDate();
     * @endcode
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareBuildDate","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"2024-3-5 07:03:20"}
     *
     * \endchinese
     * \english
     * Get the controller software build date
     *
     * @return Returns the controller software build date
     *
     * @par Python prototype
     * getControlSoftwareBuildDate(self: pyaubo_sdk.SystemInfo) -> str
     *
     * @par Lua prototype
     * getControlSoftwareBuildDate() -> string
     *
     * @par C++ example
     * @code
     * std::string build_date =
     * rpc_cli->getSystemInfo()->getControlSoftwareBuildDate();
     * @endcode
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareBuildDate","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"2024-3-5 07:03:20"}
     *
     * \endenglish
     */
    std::string getControlSoftwareBuildDate();

    /**
     * @ingroup SystemInfo
     * \chinese
     * 获取控制器软件git版本
     *
     * @return 返回控制器软件git版本
     *
     * @par Python函数原型
     * getControlSoftwareVersionHash(self: pyaubo_sdk.SystemInfo) -> str
     *
     * @par Lua函数原型
     * getControlSoftwareVersionHash() -> string
     *
     * @par C++示例
     * @code
     * std::string git_version =
     * rpc_cli->getSystemInfo()->getControlSoftwareVersionHash();
     * @endcode
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareVersionHash","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":"fa4f64a"}
     *
     * \endchinese
     * \english
     * Get the controller software git version
     *
     * @return Returns the controller software git version
     *
     * @par Python prototype
     * getControlSoftwareVersionHash(self: pyaubo_sdk.SystemInfo) -> str
     *
     * @par Lua prototype
     * getControlSoftwareVersionHash() -> string
     *
     * @par C++ example
     * @code
     * std::string git_version =
     * rpc_cli->getSystemInfo()->getControlSoftwareVersionHash();
     * @endcode
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSoftwareVersionHash","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":"fa4f64a"}
     *
     * \endenglish
     */
    std::string getControlSoftwareVersionHash();

    /**
     * @ingroup SystemInfo
     * \chinese
     * 获取系统时间(软件启动时间 ns 纳秒)
     *
     * @return 返回系统时间(软件启动时间 ns 纳秒)
     *
     * @par Python函数原型
     * getControlSystemTime(self: pyaubo_sdk.SystemInfo) -> int
     *
     * @par Lua函数原型
     * getControlSystemTime() -> number
     *
     * @par C++示例
     * @code
     * std::string system_time =
     * rpc_cli->getSystemInfo()->getControlSystemTime();
     * @endcode
     *
     * @par JSON-RPC请求示例
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSystemTime","params":[],"id":1}
     *
     * @par JSON-RPC响应示例
     * {"id":1,"jsonrpc":"2.0","result":9287799079682}
     *
     * \endchinese
     * \english
     * Get the system time (software start time in nanoseconds)
     *
     * @return Returns the system time (software start time in nanoseconds)
     *
     * @par Python prototype
     * getControlSystemTime(self: pyaubo_sdk.SystemInfo) -> int
     *
     * @par Lua prototype
     * getControlSystemTime() -> number
     *
     * @par C++ example
     * @code
     * std::string system_time =
     * rpc_cli->getSystemInfo()->getControlSystemTime();
     * @endcode
     *
     * @par JSON-RPC request example
     * {"jsonrpc":"2.0","method":"SystemInfo.getControlSystemTime","params":[],"id":1}
     *
     * @par JSON-RPC response example
     * {"id":1,"jsonrpc":"2.0","result":9287799079682}
     *
     * \endenglish
     */
    uint64_t getControlSystemTime();

protected:
    void *d_;
};

using SystemInfoPtr = std::shared_ptr<SystemInfo>;

} // namespace common_interface
} // namespace arcs
#endif
