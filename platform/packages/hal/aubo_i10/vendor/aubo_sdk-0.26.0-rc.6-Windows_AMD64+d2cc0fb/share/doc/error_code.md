<div align='center'>
<h1 align='center'>Aubo Sdk Error Code </h1>
</div>

## 缩写说明
* JNT: joint
* PDL: pedstral
* TP: teach pendant
* COMM: communication
* ENC: encoder
* CURR: current
* POS: position
* PKG: package
* PROG: program
## 错误码
| 错误名称 | 错误码 | 说明 | 建议 |
| :----:| :----: | :----: | :----: |
|DEBUG|0|Debug message {}|suggest...|
|POPUP|1|Popup title: {}, msg: {}, mode: {}|suggest...|
|POPUP_DISMISS|2|{}|suggest...|
|SYSTEM_HALT|3|{}|suggest...|
|INV_ARGUMENTS|4|Invalid arguments.|suggest...|
|USER_NOTIFY|5|{}|suggest...|
|POPUP_DISMISS_BY_ID|6|{}|suggest...|
|MODBUS_SIGNAL_CREATED|10|Modbus signal {} created.|suggest...|
|MODBUS_SIGNAL_REMOVED|11|Modbus signal {} removed.|suggest...|
|MODBUS_SIGNAL_VALUE_CHANGED|12|Modbus signal {} value changed to {}|suggest...|
|RUNTIME_CONTEXT|13|tid: {} lineno: {} index: {} comment: {}|suggest...|
|INTERP_CONTEXT|14|tid: {} lineno: {} index: {} comment: {}|suggest...|
|PROGRAM_LOADED|15|program loaded: {}|suggest...|
|TASK_DELETED|16|tid: {}| was deleted|
|MODBUS_SLAVE_BIT|20|Modbus slave address: {} value {}|suggest...|
|MODBUS_SLAVE_REG|21|Modbus slave address: {} value {}|suggest...|
|PNIO_SLAVE_SLOT_VALUE|30|PNIO slot: {} subslot {} index {} value {}|suggest...|
|PNIO_CONNECT_STATUS|31|PNIO connection status changed to {}|suggest...|
|PNIO_DEVICE_NAME|32|PNIO device name changed to {}|suggest...|
|PNIO_IP|33|PNIO ip {} mask {} gateway {}|suggest...|
|ICM_SERVER_STATUS|40| ICM server status changed to {}|suggest...|
|EIP_SLAVE_VALUE|50|EIP slave: trans_type {} index {} value {}|suggest...|
|EIP_SLAVE_CONNECT_STATUS|51|EIP slave connection status changed to {}|suggest...|
|LOG_PROGRAM_SUCCESS|100|[{}] Load program {} successful|suggest...|
|LOG_PROGRAM_FAILED|101|[{}] Load program {} failed, file not found|suggest...|
|LOG_PROGRAM_FAILED2|102|[{}] Load program {} failed, configuration file (.ins) does not match|suggest...|
|JOINT_ERR_OVER_CURRENET|10001|joint{} error: over current|(a) Check for short circuit. (b) Do a Complete rebooting sequence. (c) If this happens more than two times in a row, replace joint|
|JOINT_ERR_OVER_VOLTAGE|10002|joint{} error: over voltage|(a) Do a Complete rebooting sequence. (b) Check 48 V Power supply, current distributer, energy eater and Control Board for issues|
|JOINT_ERR_LOW_VOLTAGE|10003|joint{} error: low voltage|(a) Do a Complete rebooting sequence. (b) Check for short circuit in robot arm. (c) Check 48 V Power supply, current distributer, energy eater and Control Board for issues|
|JOINT_ERR_OVER_TEMP|10004|joint{} error: over temperature|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_HALL|10005|joint{} error: hall|suggest...|
|JOINT_ERR_ENCODER|10006|joint{} error: encoder|Check encoder connections|
|JOINT_ERR_ABS_ENCODER|10007|joint{} error: abs encoder|suggest...|
|JOINT_ERR_Q_CURRENT|10008|joint{} error: detect current|suggest...|
|JOINT_ERR_ENC_POLL|10009|joint{} error: encoder pollustion|suggest...|
|JOINT_ERR_ENC_Z_SIGNAL|10010|joint{} error: enocder z signal|suggest...|
|JOINT_ERR_ENC_CAL|10011|joint{} error: encoder calibrate|suggest...|
|JOINT_ERR_IMU_SENS|10012|joint{} error: IMU sensor|suggest...|
|JOINT_ERR_TEMP_SENS|10013|joint{} error: TEMP sensor|suggest...|
|JOINT_ERR_CAN_BUS|10014|joint{} error: CAN bus error|suggest...|
|JOINT_ERR_SYS_CUR|10015|joint{} error: system current error|suggest...|
|JOINT_ERR_SYS_POS|10016|joint{} error: system position error|suggest...|
|JOINT_ERR_OVER_SP|10017|joint{} error: over speed|suggest...|
|JOINT_ERR_OVER_ACC|10018|joint{} error: over accelerate|suggest...|
|JOINT_ERR_TRACE|10019|joint{} error: trace accuracy|suggest...|
|JOINT_ERR_TAG_POS_OVER|10020|joint{} error: target position out of range|suggest...|
|JOINT_ERR_TAG_SP_OVER|10021|joint{} error: target speed out of range|suggest...|
|JOINT_ERR_COLLISION|10022|joint{} error: collision|suggest...|
|JOINT_ERR_COMMON|10023|joint{} error: unkown error. Check communication with joint.|suggest...|
|JOINT_ERR_SWITCH_SERVO_MODE|10024|joint{} error: switch servo mode timeout.|suggest...|
|JOINT_ERR_MOTOR_STUCK|10025|joint{} error: motor stucked.|suggest...|
|JOINT_ERR_REDUCER_OVER_TEMP|10026|joint{} error: reducer over temperature|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_REDUCER_NTC|10027|joint{} error: reducer TEMP sensor failure|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_ABS_MULTITURN|10028|joint{} error: absolute encoder multiturn error|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_ADC_ZERO_OFFSET|10029|joint{} error: ADC zero offset failure|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_SHORT_CIRCUIT|10030|joint{} error: short circuit|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_PHASE_LOST|10031|joint{} error: motor phase lost|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_BRAKE|10032|joint{} error: brake failure|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_FIRMWARE_UPDATE|10033|joint{} error: firmware update failure|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_BATTERY_LOW|10034|joint{} error: battery low|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_PHASE_ALIGN|10035|joint{} error: phase align|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_CAN_HW_FAULT|10036|joint{} error: CAN bus hw fault|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_POS_DISCONTINUOUS|10037|joint{} error: target position discontinuous|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_POS_INIT|10038|joint{} error: position initiallization failure|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_TORQUE_SENSOR|10039|joint{} error: torqure sensor failure|(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence|
|JOINT_ERR_OFFLINE|10040|joint{} error: joint may be offline|(a) Check joint's hardware. (b) Check joint's id.|
|JOINT_ERR_BOOTLOADER|10041|joint{} error: The joint is in bootloader mode. Retry firmware update. |suggest...|
|JOINT_ERR_SLAVE_OFFLINE|10042|slave joint{} error: slave joint may be offline|(a) Check slave joint's hardware. (b) Check slave joint's id.|
|JOINT_ERR_SLAVE_BOOTLOADER|10043|slave joint{} error: The slave joint is in bootloader mode. Retry firmware update. |suggest...|
|JOINT_ERR_ETHERCAT_BUS|10044|joint{} error: ETHERCAT bus error|suggest...|
|EXT_AXIS_ERR_COMMON|11001|ext axis{} error: common|Check communication with ext axis drive.|
|EXT_AXIS_ERR_OVER_CURRENT|11002|ext axis{} error: over current|Check wiring/short circuit; reboot; if repeated replace drive/motor.|
|EXT_AXIS_ERR_OVER_VOLTAGE|11003|ext axis{} error: over voltage|Check DC supply, regen, energy eater; reboot.|
|EXT_AXIS_ERR_LOW_VOLTAGE|11004|ext axis{} error: low voltage|Check DC supply and cabling; reboot.|
|EXT_AXIS_ERR_OVER_TEMP|11005|ext axis{} error: over temperature|Check environment/cooling; reboot.|
|EXT_AXIS_ERR_HALL|11006|ext axis{} error: hall fault|Check hall sensor and motor cabling.|
|EXT_AXIS_ERR_ENCODER|11007|ext axis{} error: encoder fault|Check encoder connection/cable/noise.|
|EXT_AXIS_ERR_ABS_ENCODER|11008|ext axis{} error: absolute encoder fault|Check abs encoder power/cable; reboot.|
|EXT_AXIS_ERR_CUR_CALIB|11009|ext axis{} error: current calibration fault|Reboot; check current sensing circuit.|
|EXT_AXIS_ERR_Q_CURRENT|11010|ext axis{} error: current detect fault|Reboot; check current sensing circuit.|
|EXT_AXIS_ERR_ENC_POLL|11011|ext axis{} error: encoder pollution|Check encoder contamination/noise; improve shielding.|
|EXT_AXIS_ERR_ENC_Z_SIGNAL|11012|ext axis{} error: encoder Z signal fault|Check encoder Z channel and wiring.|
|EXT_AXIS_ERR_ENC_CAL|11013|ext axis{} error: encoder calibrate invalid|Redo calibration; check encoder.|
|EXT_AXIS_ERR_IMU|11014|ext axis{} error: IMU fault|Check IMU sensor and connection.|
|EXT_AXIS_ERR_TEMP_SENSOR|11015|ext axis{} error: temperature sensor fault|Check temp sensor wiring; reboot.|
|EXT_AXIS_ERR_ECAT_BUS|11016|ext axis{} error: EtherCAT bus error|Check EtherCAT cabling/topology/sync; reboot master/drive.|
|EXT_AXIS_ERR_ECAT_CONFIG|11017|ext axis{} error: EtherCAT config/ESI/SM/PDO fault|Check ESI, Mailbox/SM/PDO mapping, vendor/product/revision match.|
|EXT_AXIS_ERR_ECAT_SYNC|11018|ext axis{} error: EtherCAT sync/frame/period fault|Check DC sync, cycle time, frame loss; verify NIC/IRQ affinity.|
|EXT_AXIS_ERR_SYS_CUR|11019|ext axis{} error: system current fault|Check current loop and load; reboot.|
|EXT_AXIS_ERR_SYS_POS|11020|ext axis{} error: position out of range|Check encoder/scale/limits; reboot.|
|EXT_AXIS_ERR_OVER_SPEED|11021|ext axis{} error: over speed|Check command limits and tuning parameters.|
|EXT_AXIS_ERR_OVER_ACC|11022|ext axis{} error: over acceleration|Reduce acceleration/jerk; check tuning.|
|EXT_AXIS_ERR_FOLLOW_ERROR|11023|ext axis{} error: following error|Check gains, load, saturation; verify feedback.|
|EXT_AXIS_ERR_TAG_POS_OVER|11024|ext axis{} error: target position out of range|Check target limits and homing.|
|EXT_AXIS_ERR_TAG_SPEED_OVER|11025|ext axis{} error: target speed out of range|Clamp speed; check profile settings.|
|EXT_AXIS_ERR_TAG_CURRENT_OVER|11026|ext axis{} error: target current out of range|Clamp current/torque; check load.|
|EXT_AXIS_ERR_COLLISION|11027|ext axis{} error: collision|Remove obstruction; check torque/force limits.|
|EXT_AXIS_ERR_ADC_ZERO_OFFSET|11028|ext axis{} error: ADC zero offset|Reboot; check ADC/current sensor offset.|
|EXT_AXIS_ERR_IPM_NTC|11029|ext axis{} error: IPM NTC fault|Check power module temperature sensing.|
|EXT_AXIS_ERR_SHORT_CIRCUIT|11030|ext axis{} error: short circuit|Check motor phase wiring; insulation test.|
|EXT_AXIS_ERR_MOTOR_STALL|11031|ext axis{} error: motor stall|Check mechanical jam/load; reduce accel; reboot.|
|EXT_AXIS_ERR_ABS_MULTITURN|11032|ext axis{} error: abs encoder multiturn fault|Check abs encoder battery/params; reboot.|
|EXT_AXIS_ERR_PHASE_LOST|11033|ext axis{} error: motor phase lost|Check phase wiring/connector; measure continuity.|
|EXT_AXIS_ERR_BRAKE|11034|ext axis{} error: brake fault|Check brake wiring/power; verify brake release.|
|EXT_AXIS_ERR_REDUCER_OVER_TEMP|11035|ext axis{} error: reducer over temperature|Check reducer temperature/cooling.|
|EXT_AXIS_ERR_REDUCER_NTC|11036|ext axis{} error: reducer NTC fault|Check reducer temperature sensor.|
|EXT_AXIS_ERR_FIRMWARE_UPDATE|11037|ext axis{} error: firmware update fault|Retry update; check power stability.|
|EXT_AXIS_ERR_FLASH_OP|11038|ext axis{} error: flash operation fault|Retry; if persistent replace drive.|
|EXT_AXIS_ERR_EXT_ABS_ENC|11039|ext axis{} error: motor-side abs encoder comm fault|Check external abs encoder link/power.|
|EXT_AXIS_ERR_DRIVE_FAULT|11040|ext axis{} error: drive fault|Check drive alarm code; reboot; replace if repeated.|
|EXT_AXIS_ERR_OVERLOAD|11041|ext axis{} error: overload|Reduce load; check mechanics and tuning.|
|EXT_AXIS_ERR_HARDWARE_LIMIT|11042|ext axis{} error: hardware limit triggered|Move away from limit; check limit switch.|
|EXT_AXIS_ERR_SERVO_MODE_TIMEOUT|11043|ext axis{} error: switch servo mode timeout|Check mode transition and comm; reboot.|
|EXT_AXIS_ERR_UVW_ABZ|11044|ext axis{} error: UVW/ABZ fault|Check phase/encoder signals wiring.|
|EXT_AXIS_ERR_BATTERY_LOW|11045|ext axis{} error: battery low|Replace encoder battery; reboot.|
|EXT_AXIS_ERR_PHASE_ALIGN|11046|ext axis{} error: phase align fail|Redo phase alignment; check motor params.|
|EXT_AXIS_ERR_POS_DISCONTINUOUS|11047|ext axis{} error: position command discontinuous|Check trajectory generation and limits.|
|EXT_AXIS_ERR_POS_INIT|11048|ext axis{} error: position initialization failure|Check encoder init/homing procedure.|
|EXT_AXIS_ERR_TORQUE_SENSOR|11049|ext axis{} error: torque sensor fault|Check torque sensor wiring/calibration.|
|EXT_AXIS_ERR_ABS_ENC_LOW_VOLT|11050|ext axis{} error: abs encoder low voltage|Check encoder supply voltage and cable.|
|EXT_AXIS_ERR_OFFLINE|11051|ext axis{} error: ext axis offline|Check hardware and axis id; check EtherCAT state.|
|EXT_AXIS_ERR_BOOTLOADER|11052|ext axis{} error: ext axis in bootloader|Retry firmware update.|
|EXT_AXIS_ERR_SLAVE_OFFLINE|11053|ext axis slave{} error: slave offline|Check slave hardware and id.|
|EXT_AXIS_ERR_SLAVE_BOOTLOADER|11054|ext axis slave{} error: slave in bootloader|Retry firmware update.|
|EXT_AXIS_ERR_EEPROM|11055|ext axis{} error: EEPROM/param store fault|Check EEPROM/parameter storage; power cycle.|
|EXT_AXIS_ERR_PARAM_CONFIG|11056|ext axis{} error: parameter/config fault|Verify parameter set; restore defaults if needed.|
|EXT_AXIS_ERR_STO|11057|ext axis{} error: STO safety fault|Check STO wiring/safety chain; reset safety.|
|EXT_AXIS_ERR_ENCRYPT_CHIP|11058|ext axis{} error: encrypt chip/key fault|Check encryption chip/keys/firmware compatibility.|
|EXT_AXIS_ERR_BRAKE_RES_OVERLOAD|11059|ext axis{} error: brake resistor overload|Check brake resistor/regen circuit; duty cycle.|
|EXT_AXIS_ERR_POWER_LINE_OPEN|11060|ext axis{} error: motor power line open|Check motor power cable continuity/connector.|
|EXT_AXIS_ERR_HOMING|11061|ext axis{} error: homing fault|Check homing sensor/origin procedure; retry.|
|EXT_AXIS_ERR_TUNING_FAIL|11062|ext axis{} error: tuning fail|Redo tuning; reduce resonance; check mechanics.|
|EXT_AXIS_ERR_INERTIA_ID_FAIL|11063|ext axis{} error: inertia identification fail|Check load; redo inertia ID; adjust conditions.|
|EXT_AXIS_ERR_FLYAWAY|11064|ext axis{} error: flyaway|Emergency stop; check feedback polarity/scale; inspect drive params.|
|EXT_AXIS_ERR_SPEED_PULSE_OVER|11065|ext axis{} error: feedback pulse overspeed|Check encoder feedback and scaling; reduce speed.|
|EXT_AXIS_ERR_CTRL_LOOP|11066|ext axis{} error: control loop/timeout fault|Check sampling/current loop/comm timeout; reboot.|
|IFB_ERR_ROBOTTYPE|20001|Robot error type!|suggest...|
|IFB_ERR_ADXL_SENS|20002|Base Acceleration sensor error!|suggest...|
|IFB_ERR_EN_LINE|20003|Encoder line error!|suggest...|
|IFB_ERR_ENTER_HDG_MODE|20004|Robot enter handguide mode!|suggest...|
|IFB_ERR_EXIT_HDG_MODE|20005|Robot exit handguide mode!|suggest...|
|IFB_ERR_MAC_DATA_BREAK|20006|MAC data break!|suggest...|
|IFB_ERR_DRV_FIRMWARE_VERSION|20007|Motor driver firmware version error!|suggest...|
|INIT_ERR_EN_DRV|20008|Motor driver enable failed!|suggest...|
|INIT_ERR_EN_AUTO_BACK|20009|Motor driver enable auto back failed!|suggest...|
|INIT_ERR_EN_CUR_LOOP|20010|Motor driver enable current loop failed!|suggest...|
|INIT_ERR_SET_TAG_CUR|20011|Motor driver set target current failed!|suggest...|
|INIT_ERR_RELEASE_BRAKE|20012|Motor driver release brake failed!|suggest...|
|INIT_ERR_EN_POS_LOOP|20013|Motor driver enable postion loop failed!|suggest...|
|INIT_ERR_SET_MAX_ACC|20014|Motor set max accelerate failed!|suggest...|
|SAFETY_ERR_PROTECTION_STOP_TIMEOUT|20015|Protective stop timeout!|suggest...|
|SAFETY_ERR_REDUCED_MODE_TIMEOUT|20016|Reduced mode timeout!|suggest...|
|SYS_ERR_MCU_COM|20017|Robot system error: mcu communication error!|suggest...|
|SYS_ERR_RS485_COM|20018|Robot system error: RS485 communication error!|suggest...|
|IFB_ERR_DISCONNECTED|20019|Interface board may be disconnected. Please check connection between IPC and Interface board.|suggest...|
|IFB_ERR_PAYLOAD_ERROR|20020|Payload error.|suggest...|
|IFB_OFFLINE|20021|ifaceboard error: ifaceboard may be offline|(a) Check ifaceboard's hardware. (b) Check ifaceboard's id.|
|IFB_ERR_BOOTLOADER|20022|ifaceboard error: The ifaceboard is in bootloader mode. Retry firmware update. |suggest...|
|IFB_SLAVE_OFFLINE|20023|interface slave board error: interface slave board may be offline|(a) Check interface slave board's hardware. (b) Check interface slave board's id.|
|IFB_SLAVE_ERR_BOOTLOADER|20024|interface slave board error: The interface slave board is in bootloader mode. Retry firmware update. |suggest...|
|IFB_TOOL_ERR_ADXL_SENS|20025|Tool Acceleration sensor error!|suggest...|
|ROBOT_BE_PULLING|30001|Something is pulling the robot.|Please check TCP configuration,payload and mounting settings|
|PSTOP_ELBOW_POS|30002|Protective Stop: Elbow position close to safety plane limits.|Please move robot Elbow joint away from the safety plane|
|PSTOP_STOP_TIME|30003|Protective Stop: Exceeding user safety settings for stopping time.|(a) Check speeds and accelerations in the program (b) Check usage of TCP,payload and CoG correctly (c) Check external equipmentactivation if correctly set|
|PSTOP_STOP_DISTANCE|30004|Protective Stop: Exceeding user safety settings for stopping distance.|(a) Check speeds and accelerations in the program (b) Check usage of TCP,payload and CoG correctly (c) Check external equipmentactivation if correctly set|
|PSTOP_CLAMP|30005|Protective Stop: Danger of clamping between the Robot’s lower arm and tool.|(a) Check speeds and accelerations in the program (b) Check usage of TCP,payload and CoG correctly (c) Check external equipmentactivation if correctly set|
|PSTOP_POS_LIMIT|30006|Protective Stop: Position close to joint limits|suggest...|
|PSTOP_ORI_LIMIT|30007|Protective Stop: Tool orientation close to limits|suggest...|
|PSTOP_PLANE_LIMIT|30008|Protective Stop: Position close to safety plane limits|suggest...|
|PSTOP_POS_DEVIATE|30009|Protective Stop: Position deviates from path|Check payload, center of gravity and acceleration settings.|
|JOINT_CHK_PAYLOAD|30010|Joint {}: Check payload, center of gravity and acceleration settings. Log screen may contain additional information.|suggest...|
|PSTOP_SINGULARITY|30011|Protective Stop: Position in singularity.|Please use MoveJ or change the motion|
|PSTOP_CANNOT_MAINTAIN|30012|Protective Stop: Robot cannot maintain its position, check if payload is correct|suggest...|
|PSTOP_WRONG_PAYLOAD|30013|Protective Stop: Wrong payload or mounting detected, or something is pushing the robot when entering Freedrive mode|Verify that the TCP configuration and mounting in the used installation is correct|
|PSTOP_JOINT_COLLISION|30014|Protective Stop: Collision detected by joint {}|Make sure no objects are in the path of the robot and resume the program|
|PSTOP_POS_DISAGREE|30015|Protective stop: The robot was powered off last time due to a joint position disagreement.| (a) Verify that the robot position in the 3D graphics matches the real robot, to ensure that the encoders function before releasing the brakes. Stand back and monitor the robot performing its first program cycle as expected. (b) If the position is not correct, the robot must be repaired. In this case, click Power Off Robot. (c) If the position is correct, please tick the check box below the 3D graphics and click Robot Position Verified|
|TARGET_JOINT_SPEED_EXCEED|30016|Target joint speed exceed limits|suggest...|
|TARGET_POS_SUDDEN_CHG|30017|Sudden change in target position|suggest...|
|SUDDEN_STOP|30018|Sudden stop.| To abort a motion, use "stopj" or "stopl" script commands to generate a smooth deceleration before using "wait". Avoid aborting motions between waypoints with blend”|
|ROBOT_STOP_ABNORMAL|30019|Robot has not stopped in the allowed reaction and braking time|suggest...|
|PROG_INVALID_SETP|30020|Robot program resulted in invalid setpoint.|Please review waypoints in the program|
|BLEND_INVALID_SETP|30021|Blending failed and resulted in an invalid setpoint.|Try changing the blend radius or contact technical support|
|APPROACH_SINGULARITY|30022|Robot approaching singularity – Acceleration threshold failed.|Review waypoints in the program, try using MoveJ instead of MoveL in the position close to singularity|
|TSPEED_UNMATCH_POS|30023|Target speed does not match target position|suggest...|
|INCONSIS_TPOS_SPD|30024|Inconsistency between target position and speed|suggest...|
|JOINT_TSPD_UNMATCH_POS|30025|Target joint speed does not match target joint position change – Joint {}|suggest...|
|FIELDBUS_INPUT_DISCONN|30026|Fieldbus input disconnected.|Please check fieldbus connections (RTDE, ModBus, EtherNet/IP and Profinet) or disable the fieldbus in the installation. Check RTDE watchdog feature. Check if a URCap is using this feature.|
|OPMODE_CHANGED|30027|Operational mode changed: {}|suggest...|
|NO_KIN_CALIB|30028|No Kinematic Calibration found (calibration.conf file is either corrupt or missing).|A new kinematics calibration may be needed if the robot needs to improve its kinematics, otherwise, ignore this message)|
|KIN_CALIB_UNMATCH_JOINT|30029|Kinematic Calibration for the robot does not match the joint(s).|If moving a program from a different robot to this one, rekinematic calibrate the second robot to improve kinematics, otherwise ignore this message.|
|KIN_CALIB_UNMATCH_ROBOT|30030|Kinematic Calibration does not match the robot.|Please check if the serial number of the robot arm matches the Control Box|
|JOINT_OFFSET_CHANGED|30031|Large movement of the robot detected while it was powered off. The joints were moved while it was powered off, or the encoders do not function|suggest...|
|OFFSET_CHANGE_HIGH|30032|Change in offset is too high|suggest...|
|JOINT_SPEED_LIMIT|30033|Close to joint speed safety limit.|Review program speed and acceleration|
|TOOL_SPEED_LIMIT|30034|Close to tool speed safety limit.|Review program speed and acceleration|
|MOMENTUM_LIMIT|30035|Close to momentum safety limit.|Review program speed and acceleration|
|ROBOT_MV_STOP|30036|Robot is moving when in Stop Mode|suggest...|
|HAND_PROTECTION|30037|Hand protection: Tool is too close to the lower arm: {} meter.|(a) Check wrist position. (b) Verify mounting (c) Do a Complete rebooting sequence (d) Update software (e) Contact your local AUBO Robots service provider for assistance|
|WRONG_SAFETYMODE|30038|Wrong safety mode: {}|suggest...|
|SAFETYMODE_CHANGED|30039|Safety mode changed: {}|suggest...|
|JOINT_ACC_LIMIT|30040|Close to joint acceleration safety limit|suggest...|
|TOOL_ACC_LIMIT|30041|Close to tool acceleration safety limit|suggest...|
|JOINT_TEMPERATURE_LIMIT|30042|Joint {} temperature too high(>{}℃)|suggest...|
|CONTROL_BOX_TEMPERATURE_LIMIT|30043|Control box temperature too high(>{}℃)|suggest...|
|ROBOT_EMERGENCY_STOP|30044|Robot emergency stop|suggest...|
|ROBOTMODE_CHANGED|30045|Robot mode changed: {}|suggest...|
|ROBOTMODE_ERROR|30046|Wrong robot mode: {}|suggest...|
|POSE_OUT_OF_REACH|30047|Target pose [{}] out of reach|suggest...|
|TP_PLAN_FAILED|30048|Trajectory plan FAILED.|suggest...|
|START_FORCE_FAILED|30049|Start force control failed, because force sensor does not exist.|suggest...|
|OVER_SAFE_PLANE_LIMIT|30050|{} axis exceeds the safety plane limit (Move_type:{} id:{}).|Please move the robot to the safety plane range.|
|POWERON_FAIL_VIOLATION|30051|Failed to power on because the robot safety mode is in violation|suggest...|
|POWERON_FAIL_SYSTEMEMERGENCYSTOP|30052|Failed to power on because the robot safety mode is in system emergency stop|suggest...|
|POWERON_FAIL_ROBOTEMERGENCYSTOP|30053|Failed to power on because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|POWERON_FAIL_FAULT|30054|Failed to power on because the robot safety mode is in fault|suggest...|
|STARTUP_FAIL_VIOLATION|30055|Failed to startup because the robot safety mode is in violation|suggest...|
|STARTUP_FAIL_SYSTEMEMERGENCYSTOP|30056|Failed to startup because the robot safety mode is in system emergency stop|suggest...|
|STARTUP_FAIL_ROBOTEMERGENCYSTOP|30057|Failed to startup because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|STARTUP_FAIL_FAULT|30058|Failed to startup because the robot safety mode is in fault|suggest...|
|BACKDRIVE_FAIL_VIOLATION|30059|Failed to backdrive because the robot safety mode is in violation|suggest...|
|BACKDRIVE_FAIL_SYSTEMEMERGENCYSTOP|30060|Failed to backdrive because the robot safety mode is in system emergency stop|suggest...|
|BACKDRIVE_FAIL_ROBOTEMERGENCYSTOP|30061|Failed to backdrive because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|BACKDRIVE_FAIL_FAULT|30062|Failed to backdrive because the robot safety mode is in fault|suggest...|
|SETSIM_FAIL_VIOLATION|30063|Switch sim mode failed because the robot safety mode is in violation|suggest...|
|SETSIM_FAIL_SYSTEMEMERGENCYSTOP|30064|Switch sim mode failed because the robot safety mode is in system emergency stop|suggest...|
|SETSIM_FAIL_ROBOTEMERGENCYSTOP|30065|Switch sim mode failed because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|SETSIM_FAIL_FAULT|30066|Switch sim mode failed because the robot safety mode is in fault|suggest...|
|FREEDRIVE_FAIL_VIOLATION|30067|Enable handguide mode failed because the robot safety mode is in violation|suggest...|
|FREEDRIVE_FAIL_SYSTEMEMERGENCYSTOP|30068|Enable handguide mode failed because the robot safety mode is in system emergency stop|suggest...|
|FREEDRIVE_FAIL_ROBOTEMERGENCYSTOP|30069|Enable handguide mode failed because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|FREEDRIVE_FAIL_FAULT|30070|Enable handguide mode failed because the robot safety mode is in fault|suggest...|
|UPFIRMWARE_FAIL_VIOLATION|30071|Firmware update failed because the robot safety mode is in violation|suggest...|
|UPFIRMWARE_FAIL_SYSTEMEMERGENCYSTOP|30072|Firmware update failed because the robot safety mode is in system emergency stop|suggest...|
|UPFIRMWARE_FAIL_ROBOTEMERGENCYSTOP|30073|Firmware update failed because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|UPFIRMWARE_FAIL_FAULT|30074|Firmware update failed because the robot safety mode is in fault|suggest...|
|SETPERSOSTENT_FAIL_VIOLATION|30075|Set persistent parameter failed because the robot safety mode is in violation|suggest...|
|SETPERSOSTENT_FAIL_SYSTEMEMERGENCYSTOP|30076|Set persistent parameter failed because the robot safety mode is in system emergency stop|suggest...|
|SETPERSOSTENT_FAIL_ROBOTEMERGENCYSTOP|30077|Set persistent parameter failed because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|SETPERSOSTENT_FAIL_FAULT|30078|Set persistent parameter failed because the robot safety mode is in fault|suggest...|
|SETPERSOSTENT_FAIL_PARAM_ERR|30079|Set persistent parameter failed|(a) Check the parameter format, whether all are floating point numbers|
|ROBOT_CABLE_DISCONN|30080|Robot cable not connected|(a) Make sure the cable between Control Box and Robot Arm is correctly connected and it has no damage. (b) Check for loose connections (c) Do a Complete rebooting sequence (d) Update software (e) Contact your local AUBO Robots service provider for assistance Contact your local AUBO Robots service provider for assistance.|
|TP_TOO_SHORT|30081|The generated trajectory is ignored because it is too short|(a) Please check if the added waypoints are coincident (b) If it is an arc movement, please check whether the three points are collinear|
|INV_KIN_FAIL|30082|Inverse kinematics solution failed. The target pose may be in a singular position or exceed the joint limits|(a) Change the target pose and try moving again|
|FREEDRIVE_ENABLED|30083|Freedrive status changed to {}|suggest...|
|TP_INV_FAIL_REFERENCE_JOINT_OUT_OF_LIMIT|30084|Inverse kinematics solution failed. Reference angle [{}] exceeds joint limit [{}].|suggest...|
|TP_INV_FAIL_NO_SOLUTION|30085|Inverse kinematics solution failed. The reference angle [{}] and the target angle [{}] are used as parameters. there is no solution in the calculation of the inverse solution process.|suggest...|
|SERVO_FAIL_VIOLATION|30086|Switch servo mode failed because the robot safety mode is in violation|suggest...|
|SERVO_FAIL_SYSTEMEMERGENCYSTOP|30087|Switch servo mode failed because the robot safety mode is in system emergency stop|suggest...|
|SERVO_FAIL_ROBOTEMERGENCYSTOP|30088|Switch servo mode failed because the robot safety mode is in robot emergency stop|Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion|
|SERVO_FAIL_FAULT|30089|Switch servo mode failed because the robot safety mode is in fault|suggest...|
|FREEDRIVE_FAIL_NO_RUNNING|30090|Enable handguide mode failed because the robot mode type is {}(not running)|suggest...|
|RUNTIME_MACHINE_ERROR|30091|The state of the running machine is {}, not {}. {} function execution failed because the state is wrong.|suggest...|
|RESUME_FAR_PAUSE_PT|30092|Cannot resume from joint position [{}].\nToo far away from paused point [{}].|suggest...|
|PAYLOAD_LIGHTER_ERROR|30093|The payload setting is too small!|suggest...|
|PAYLOAD_OVERLOAD_ERROR|30094|The payload setting is too large!|suggest...|
|PAUSE_FAIL_NOT_POSITION_PLAN_MODE|30095|This motion does not support the pause function. The motion is stopping.|suggest...|
|TP_PLAN_FAILED_CIRCULAR_WAYPOINTS_COINCIDE|30096|The planning failed because the three waypoints of the arc were determined to coincide.|Check the circular waypoints to make sure they are different.|
|SERVO_WRONG_SAFETYMODE|30097|Switch servo mode failed because the robot safety mode is in {}.|Check the circular waypoints to make sure they are different.|
|SET_PERSTPARAM_WRONG_SAFETYMODE|30098|Set persistent parameter failed because the robot safety mode is in {}|suggest...|
|SET_KINPARAM_WRONG_SAFETYMODE|30099|Set Kinematics Compensate parameters failed because the robot safety mode is in {}|suggest...|
|SET_ROBOT_ZERO_WRONG_SAFETYMODE|30100|Set current joint angles to zero failed because the robot safety mode is in {}|suggest...|
|UPFIRMWARE_WRONG_SAFETYMODE|30101|Firmware update failed because the robot safety mode is in {}|suggest...|
|POWERON_WRONG_SAFETYMODE|30102|Failed to power on because the robot safety mode is in {}|suggest...|
|STARTUP_WRONG_SAFETYMODE|30103|Failed to startup because the robot safety mode is in {}|suggest...|
|BACKDRIVE_WRONG_SAFETYMODE|30104|Failed to backdrive because the robot safety mode is in system emergency stop|suggest...|
|SETSIM_WRONG_SAFETYMODE|30105|Switch sim mode failed because the robot safety mode is in violation|suggest...|
|FREEDRIVE_WRONG_SAFETYMODE|30106|Enable handguide mode failed because the robot safety mode is in wrong safety mode: {}|suggest...|
|TP_PLAN_FAILED_JOINT_JUMP_BIGGER|30107|Inverse kinematics solution failed. The target point and the current point are in different robot configuration spaces.|Add a few more points between the target point and the current point.|
|RUN_PROGRAM_FAILED|30108|Run program {} failed.|suggset...|
|FREEDRIVE_FAIL_WRONG_RTMSTATE|30109|Unable to enter the HandGuide mode as the robot is not currently in a stopped or paused state.|suggset...|
|SAFEGUARDSTOP_CONFIGURABLE_INPUT|30110|Configurable safety input is triggered.|suggset...|
|SAFEGUARDSTOP_3PE|30111|3PE is triggered.|suggset...|
|SAFEGUARDSTOP_SI|30112|SI0/SI1 is triggered.|suggset...|
|ROBOT_TYPE_CHANGED|30200|Robot type changed to '{}', and robot subtype changed to '{}'|suggest...|
|LINKMODE_CHANGED|30201|Link mode changed to {}|suggest...|
|ROBOT_SELF_COLLISION|30301|Detect risk of robot self collision|suggest...|
|CONSTANT_INVALID|30302|Joint torque constants are invalid. HandGuide will be disabled, and the collision protection may be triggered by mistake.|suggest...|
|GRAVITY_INVALID|30303|Abnormal value of gravity acceleration sensor. HandGuide will be disabled, and the collision protection may be triggered by mistake.|suggest...|
|DYNAMICS_INVALID|30304|Robot dynamics parameters are invalid. HandGuide will be disabled, and the collision protection may be triggered by mistake.|suggest...|
|FRICTION_INVALID|30305|Joint friction parameters are invalid. HandGuide will be disabled, and the collision protection may be triggered by mistake.|suggest...|
|HANDGUIDE_UNDER_DEVELOP|30306|Robot type of {} function under development. HandGuide will be disabled, and the collision protection may be triggered by mistake.|suggest...|
|SLOW_DOWN_INFO|30307|Slow down level changed to {}({}%)|suggest...|
|WRONG_JOINT_DESIGNED_LIMIT|30308|Joint designed ranges exceeds ranges read from hardware interface.|suggest...|
|FREEDRIVE_IN_SIMULATION|30309|Enable handguide mode failed because the robot is in simulation mode.|suggest...|
|ROBOT_STOPPING_TIMEOUT|30310|Robot stopping timeout.|suggest...|
|PSTOP_INCORRECT_FORCE_OFFSET|30311|Protective Stop: Sudden change in force control target position. Force sensor offset may be incorrect or force sensor fault.|suggest...|
|WRONG_JOINT_SAFETY_LIMIT|30312|Joint safety ranges exceeds designed ranges.|suggest...|
|PSTOP_TCP_PLANE_VIOLATION|30401|Protective Stop: TCP position close to safety plane limits.|suggest...|
|PSTOP_ELBOW_PLANE_VIOLATION|30402|Protective Stop: elbow position close to safety plane limits.|suggest...|
|PSTOP_JOINT_TORQUE_VIOLATION|30403|Protective Stop: joint{} exceeds torque limit.|suggest...|
|PSTOP_JOINT_POSITION_VIOLATION|30404|Protective Stop: joint{} exceeds position limit.|suggest...|
|PSTOP_JOINT_SPEED_VIOLATION|30405|Protective Stop: joint{} exceeds speed limit.|suggest...|
|PSTOP_TCP_SPEED_VIOLATION|30406|Protective Stop: TCP speed close to safety limits.|suggest...|
|PSTOP_ELBOW_SPEED_VIOLATION|30407|Protective Stop: elbow speed close to safety limits.|suggest...|
|PSTOP_TCP_FORCE_VIOLATION|30408|Protective Stop: TCP foece close to safety limits.|suggest...|
|PSTOP_ELBOW_TORQUE_VIOLATION|30409|Protective Stop: elbow torque close to safety limits.|suggest...|
|PSTOP_POWER_VIOLATION|30410|Protective Stop: robot power close to safety limits.|suggest...|
|PSTOP_MOMENTUM_VIOLATION|30411|Protective Stop: robot momentum close to safety limits.|suggest...|
|PSTOP_TCP_CUBE_VIOLATION|30412|Protective Stop: TCP position close to safety cube.|suggest...|
|PSTOP_ELBOW_CUBE_VIOLATION|30413|Protective Stop: TCP position close to safety cube.|suggest...|
|REDUCE_ELBOW_PLANE_TRIGGER|30414|Reduce mode: elbow close to safety plane triggers reduction mode.|suggest...|
|REDUCE_TCP_PLANE_TRIGGER|30415|Reduce mode: TCP close to safety plane triggers reduction mode.|suggest...|
|PSTOP_MOVE_OUT_RANGE|30416|Joint {} has exceeded the limit, please do not continue to move out of the range|suggest...|
|RESUME_PAUSE_FAILED|30417|Resume Failed: Safety mode type is {}|suggest...|
|FIRMWARE_UPDATE_FAIL_EMERGENCYSTOP|30418|Failed to firmware update because the robot safety mode is in {}|Release emergency stop when the robot is in a safe range of motion|
|TOOL_SENSOR_CHANGED|30419|Tool sensor type changed to {}|suggest...|
|TOOL_SENSOR_REMOVED|30420|Tool sensor is removed.|suggest...|
|CAL_TARGET_CURRENT_ERR|30421|The calculation of the target current failed. Please try again later.|suggest...|
|CONVEYOR_MODE_CHANGED|30422|Conveyor{}: track mode changed to {}, track item id is {}|suggest...|
|CONVEYOR_ENQUEUE|30423|Conveyor{}: the queue has been changed, item{} is enqueue|suggest...|
|CONVEYOR_DEQUEUE_FINISH|30424|Conveyor{}: the queue has been changed, item{} dequeue due to track finished|suggest...|
|CONVEYOR_DEQUEUE_STARTWINDOW|30425|Conveyor{}: the queue has been changed, item{} dequeue due to exceeds startwindow|suggest...|
|CONVEYOR_DEQUEUE_LIMIT|30426|Conveyor{}: the queue has been changed, item{} dequeue due to exceed limit area|suggest...|
|CONVEYOR_DEQUEUE_CLEAR|30427|Conveyor{}: item queue is cleared|suggest...|
|CONVEYOR_NEXT_TRACK|30428|Conveyor{}: item{} inside the start window that can be tracked |suggest...|
|CONVEYOR_EXCEED_LIMIT|30429|Conveyor{}: item{} exceeds the limit area during tracking|suggest...|
|WRONG_POWER_SAFETY_LIMIT|30430|Robot power safety value exceeds designed value.|suggest...|
|WRONG_POWER_DESIGNED_LIMIT|30431|Power designed value exceeds value read from hardware interface.|suggest...|
|TOOL_SENSOR_STATUS_CHANGED|30432|Tool sensor status changed to {}|suggest...|
|COLLISION_THRESHOLD_INVALID|30433|Robot collision threshold parameters are invalid.Please reidentify the threshold or modify the configuration to ensure that it does not cause accidental collisions.|suggest...|
|GRIPPER_DISCONNECT|30434|The gripper {} is disconnected.|suggest...|
|GRIPPER_UNKNOWN_FAULT|30435|There is an unknown fault with the gripper {}|suggest...|
|GRIPPER_CURRENT_ANOMALY_FAULT|30436|There is an abnormal current fault with the gripper {}|suggest...|
|GRIPPER_VOLTAGE_ANOMALY_FAULT|30437|There is an abnormal voltage fault with the gripper {}|suggest...|
|GRIPPER_OVER_TEMPERATURE_FAULT|30438|There is an over-temperature fault with the gripper {}|suggest...|
|GRIPPER_INTERNAL_FAULT|30439|There is an internal fault with the gripper {}|suggest...|
|GRIPPER_COMMUNICATION_FAULT|30440|There is an communication fault with the gripper {}|suggest...|
|GRIPPER_CONTROL_COMMAND_FAULT|30441|There is an control command fault with the gripper {}|suggest...|
|GRIPPER_ENABLE_FAULT|30442|There is an enable fault with the gripper {}|suggest...|
|WRIST_SINGULARITY_RISK|30443|Wrist singularity detected. Linear motion may cause excessive joint speed.Adjust robot posture to avoid J5 near 0° or 180°, or use joint motion instead of linear motion.|suggest...|
|TOOL_FLASH_VERIFY_FAILED|40001|Flash write verify failed|suggest...|
|TOOL_PROGRAM_CRC_FAILED|40002|Program flash checksum failed during bootloading|suggest...|
|TOOL_PROGRAM_CRC_FAILED2|40003|Program flash checksum failed at runtime|suggest...|
|TOOL_ID_UNDIFINED|40004|Tool ID is undefined|suggest...|
|TOOL_ILLEGAL_BL_CMD|40005|Illegal bootloader command|suggest...|
|TOOL_FW_WRONG|40006|Wrong firmware at the joint|suggest...|
|TOOL_HW_INVALID|40007|Invalid hardware revision|suggest...|
|TOOL_SHORT_CURCUIT_H|40011|Short circuit detected on Digital Output: {} high side|suggest...|
|TOOL_SHORT_CURCUIT_L|40012|Short circuit detected on Digital Output: {} low side|suggest...|
|TOOL_AVERAGE_CURR_HIGH|40013|10 second Average tool IO Current of {} A is outside of the allowed range.|suggest...|
|TOOL_POWER_PIN_OVER_CURR|40014|Current of {} A on the POWER pin is outside of the allowed range.|suggest...|
|TOOL_DOUT_PIN_OVER_CURR|40015|Current of {} A on the Digital Output pins is outside of the allowed range.|suggest...|
|TOOL_GROUND_PIN_OVER_CURR|40016|Current of {} A on the ground pin is outside of the allowed range.|suggest...|
|TOOL_RX_FRAMING|40021|RX framing error|suggest...|
|TOOL_RX_PARITY|40022|RX Parity error|suggest...|
|TOOL_48V_LOW|40031|48V input is too low|suggest...|
|TOOL_48V_HIGH|40032|48V input is too high|suggest...|
|TOOL_ERR_OFFLINE|40033|tool error: tool may be offline|(a) Check tool's hardware. (b) Check joint's id.|
|TOOL_ERR_BOOTLOADER|40034|tool error: The tool is in bootloader mode. Retry firmware update. |suggest...|
|PKG_LOST|50001|Lost package from pedestal|suggest...|
|PEDSTRAL_OFFLINE|50002|pedestal error: pedestal may be offline|(a) Check pedestal's hardware. (b) Check pedestal's id.|
|PEDESTAL_ERR_BOOTLOADER|50003|pedestal error: The pedestal is in bootloader mode. Retry firmware update. |suggest...|
|HW_SCB_SETUP_FAILED|60001|Setup of Interface Board failed|suggest...|
|HW_PKG_CNT_DISAGEE|60002|Packet counter disagreements|suggest...|
|HW_SCB_DISCONNECT|60003|Connection to Interface Board lost|suggest...|
|HW_SCB_PKG_LOST|60004|Package lost from Interface Board|suggest...|
|HW_SCB_CONN_INIT_FAILED|60005|Ethernet connection initialization with Interface Board failed|suggest...|
|HW_LOST_JOINT_PKG|60006|Lost package from joint  {}|suggest...|
|HW_LOST_TOOL_PKG|60007|Lost package from tool|suggest...|
|HW_JOINT_PKG_CNT_DISAGREE|60008|Packet counter disagreement in packet from joint {}|suggest...|
|HW_TOOL_PKG_CNT_DISAGREE|60009|Packet counter disagreement in packet from tool|suggest...|
|HW_JOINTS_FAULT|60011|{} joint entered the Fault State|suggest...|
|HW_JOINTS_VIOLATION|60012|{} joint entered the Violation State|suggest...|
|HW_TP_FAULT|60013|Teach Pendant entered the Fault State|suggest...|
|HW_TP_VIOLATION|60014|Teach Pendant entered the Violation State|suggest...|
|HW_JOINT_MV_TOO_FAR|60021|{} joint moved too far before robot entered RUNNING State|suggest...|
|HW_JOINT_STOP_NOT_FAST|60022|Joint Not stopping fast enough|suggest...|
|HW_JOINT_MV_LIMIT|60023|Joint moved more than allowable limit|suggest...|
|HW_FT_SENSOR_DATA_INVALID|60024|Force-Torque Sensor data invalid|suggest...|
|HW_NO_FT_SENSOR|60025|Force-Torque sensor is expected, but it cannot be detected|suggest...|
|HW_FT_SENSOR_NOT_CALIB|60026|Force-Torque sensor is detected but not calibrated|suggest...|
|HW_RELEASE_BRAKE_FAILED|60030|Robot was not able to brake release, see log for details|suggest...|
|HW_OVERCURR_SHUTDOWN|60040|Overcurrent shutdown|suggest...|
|HW_ENERGEY_SURPLUS|60050|Energy surplus shutdown|suggest...|
|HW_IDLE_POWER_HIGH|60060|Idle power consumption to high|suggest...|
|HW_ENTER_COLLISION_TIMEOUT|60071|Enter collision stop procedure timeout|suggest...|
|HW_POWERON_TIMEOUT|60072|Poweron robot timeout|suggest...|
|HW_NO_NIC_FOUND|60073|No network cards found.|suggest...|
|HW_IFB_NOT_FOUND|60074|No Interface Board found.|suggest...|
|HW_IFB_BOOTLOAD|60075|The Interface Board is in bootloader mode. Update firmware firstly.|suggest...|
|HW_TOOL_NOT_FOUND|60076|No Tool Board found.|suggest...|
|HW_BASE_NOT_FOUND|60077|No Base Board found.|suggest...|
|HW_BRINGUP_TIMEOUT|60078|Poweron robot timeout|suggest...|
|HW_COLLISION_RECOVERY_FAILED|60079|Collision recovery failed|suggest...|
|HW_TP_ENABLED|60080|Teach pendant enabled status changed to {}|suggest...|
|ARCS_MAX_ERROR_CODE|-1|Max error code|suggest...|
