cmake_minimum_required(VERSION 3.16)

set(CMAKE_CXX_STANDARD 17)

file(GLOB _src "*.h" "*.cpp")

add_executable(example_aubope ${_src})

set(THREADS_PREFER_PTHREAD_FLAG ON)

find_package(Threads REQUIRED)

target_link_libraries(example_aubope ${SDK_LIB} eigen Threads::Threads)
