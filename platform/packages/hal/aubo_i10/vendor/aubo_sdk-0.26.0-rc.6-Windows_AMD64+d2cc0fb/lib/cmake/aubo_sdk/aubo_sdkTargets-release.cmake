#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "aubo_sdk::aubo_sdk" for configuration "Release"
set_property(TARGET aubo_sdk::aubo_sdk APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(aubo_sdk::aubo_sdk PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/aubo_sdk.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/aubo_sdk.dll"
  )

list(APPEND _cmake_import_check_targets aubo_sdk::aubo_sdk )
list(APPEND _cmake_import_check_files_for_aubo_sdk::aubo_sdk "${_IMPORT_PREFIX}/lib/aubo_sdk.lib" "${_IMPORT_PREFIX}/lib/aubo_sdk.dll" )

# Import target "aubo_sdk::robot_proxy" for configuration "Release"
set_property(TARGET aubo_sdk::robot_proxy APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(aubo_sdk::robot_proxy PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/robot_proxy.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/robot_proxy.dll"
  )

list(APPEND _cmake_import_check_targets aubo_sdk::robot_proxy )
list(APPEND _cmake_import_check_files_for_aubo_sdk::robot_proxy "${_IMPORT_PREFIX}/lib/robot_proxy.lib" "${_IMPORT_PREFIX}/lib/robot_proxy.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
