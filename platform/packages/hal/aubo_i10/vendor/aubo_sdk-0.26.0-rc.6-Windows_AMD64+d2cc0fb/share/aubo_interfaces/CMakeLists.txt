cmake_minimum_required(VERSION 3.5)
project(aubo_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

set(INTERFACE_LIST_FILE "${CMAKE_CURRENT_SOURCE_DIR}/generated_interfaces.txt")

if(EXISTS "${INTERFACE_LIST_FILE}")
  file(STRINGS "${INTERFACE_LIST_FILE}" INTERFACES)
else()
  message(FATAL_ERROR "generated_interfaces.txt not found: ${INTERFACE_LIST_FILE}")
endif()

list(FILTER INTERFACES EXCLUDE REGEX "^[ \t]*$")

rosidl_generate_interfaces(${PROJECT_NAME}
  ${INTERFACES}
  DEPENDENCIES builtin_interfaces
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()

