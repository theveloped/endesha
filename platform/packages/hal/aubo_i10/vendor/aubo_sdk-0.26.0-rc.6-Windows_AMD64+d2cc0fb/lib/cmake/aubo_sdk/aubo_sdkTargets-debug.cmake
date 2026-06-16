#----------------------------------------------------------------
# Generated CMake target import file for configuration "Debug".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "aubo_sdk::aubo_sdk" for configuration "Debug"
set_property(TARGET aubo_sdk::aubo_sdk APPEND PROPERTY IMPORTED_CONFIGURATIONS DEBUG)
set_target_properties(aubo_sdk::aubo_sdk PROPERTIES
  IMPORTED_IMPLIB_DEBUG "${_IMPORT_PREFIX}/lib/aubo_sdkd.lib"
  IMPORTED_LOCATION_DEBUG "${_IMPORT_PREFIX}/lib/aubo_sdkd.dll"
  )

list(APPEND _cmake_import_check_targets aubo_sdk::aubo_sdk )
list(APPEND _cmake_import_check_files_for_aubo_sdk::aubo_sdk "${_IMPORT_PREFIX}/lib/aubo_sdkd.lib" "${_IMPORT_PREFIX}/lib/aubo_sdkd.dll" )

# Import target "aubo_sdk::robot_proxy" for configuration "Debug"
set_property(TARGET aubo_sdk::robot_proxy APPEND PROPERTY IMPORTED_CONFIGURATIONS DEBUG)
set_target_properties(aubo_sdk::robot_proxy PROPERTIES
  IMPORTED_IMPLIB_DEBUG "${_IMPORT_PREFIX}/lib/robot_proxyd.lib"
  IMPORTED_LOCATION_DEBUG "${_IMPORT_PREFIX}/lib/robot_proxyd.dll"
  )

list(APPEND _cmake_import_check_targets aubo_sdk::robot_proxy )
list(APPEND _cmake_import_check_files_for_aubo_sdk::robot_proxy "${_IMPORT_PREFIX}/lib/robot_proxyd.lib" "${_IMPORT_PREFIX}/lib/robot_proxyd.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
