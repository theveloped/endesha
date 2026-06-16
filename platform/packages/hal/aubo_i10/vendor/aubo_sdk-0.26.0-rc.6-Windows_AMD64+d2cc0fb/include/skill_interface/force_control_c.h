#ifndef AUBO_SDK_ForceControl_C_H
#define AUBO_SDK_ForceControl_C_H
#include <aubo_sdk/type_def_c.h>

enum ForceStage_C
{
    TOUCH = 1,    // 接近
    SEARCH = 2,   // 搜孔
    INSERT = 3,   // 插孔
    CONSTANT = 4, // 恒力

}; // enum ForceStage

enum StateCode_C
{
    // 失败状态码
    TimeOut = -100,         // 超时
    Search_MaxForce = -4,   // 搜孔达到最大力
    Insert_MaxForce = -3,   // 插入达到最大力
    Constant_NotTouch = -2, // 恒力过程中未接触
    Touch_Distance = -1,    // 超出探寻距离

    Running = 0, // 力控执行中

    // 成功状态码
    Touch_Succeed = 1,    // 接触成功
    Insert_Succeed = 2,   // 插孔成功
    Search_Succeed = 3,   // 搜孔成功
    Constant_Succeed = 4, // 接触成功

}; // StateCode

// 轨迹类型
enum GuideTrajType_C
{
    NONE = 0,   // 无参考轨迹
    LINE1 = 1,  // 直线 speedLine
    LINE2 = 2,  // 直线 moveLine
    SPIRAL = 3, // 螺旋线
    WEAVE = 4,  // 摆线
};

// 螺旋线平面
enum class SpiralPlane_C
{
    xy = 0,
    yz = 1,
    zx = 2
};

// 螺旋线轨迹参数
struct SpiralTrajParams_C
{
    double step = 0.0;     // 圈数
    double direction = -1; // 旋转方向 -1顺时针旋转，1逆时针旋转
    SpiralPlane_C plane = SpiralPlane_C::xy; // 参考平面选择
    double spiral = 0.0;                     // 螺旋线外扩
    double helix = 0.0;                      // 螺旋上升 m
    double radius = 0.0;                     // 第一圈半径 m
};

// 摆线方向
enum class WeaveSelect_C
{
    x = 1,
    y = 2,
    z = 3,
    rx = 4,
    ry = 5,
    rz = 6
};

// 摆线轨迹参数
struct WeaveTrajParams_C
{
    double step = 0.0;                          // 周期
    double amplitude = 0.0;                     // 幅度
    WeaveSelect_C direction = WeaveSelect_C::x; // 方向
    double hold_distance = 0.0;                 // 保持距离 m
    double angle = 0.0;                         // 角度
    double type;                                // 类型
};

// 插孔方向
enum class InsertSelect_C
{
    x = 1,
    y = 2,
    z = 3,
};

// 插孔参数
struct InsertParams_C
{
    InsertSelect_C insert_select = InsertSelect_C::z; // 插入方向,可选x\y\z
    double hole_diameter = 0.0;                       // 轴孔直径  m
    double insert_max_speed = 0.01;                   // 插入速度限制 m/s
    double insert_time = 1000;                        // 插入时间限制 ms
    GuideTrajType_C guide_traj_type = NONE;           // 主动轨迹类型
    double insert_max_force[6] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 }; // 最大力限制
    double insert_max_depth = 0.01; // 插入距离限制 m
    double insert_guide_force = 10; // 插入引导力
    // 力控调节参数
    double insert_damp_scale[6] = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };
    double insert_stiff_scale[6] = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };

    SpiralTrajParams_C spiral_param; // 螺旋轨迹参数
    WeaveTrajParams_C weave_param;   // 摆动轨迹参数
};

// 搜孔平面
enum class SearchPlane_C
{
    yz = 1,
    xz = 2,
    xy = 3
};

// 搜孔参数
struct SearchParams_C
{
    SearchPlane_C search_plane = SearchPlane_C::xy; // 搜孔平面
    double hole_diameter = 0.0;                     // 轴孔直径 m
    double search_range = 0.1;                      // 搜孔范围
    double search_time = 1000;                      // 搜孔时间限制 ms
    GuideTrajType_C guide_traj_type = NONE; // 搜孔过程主动轨迹类型
    double search_max_force = 10;           // 最大力限制
    double search_guide_force = 1;          // 搜孔引导力
    // 力控调节参数
    double search_damp_scale[6] = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };
    double search_stiff_scale[6] = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };

    SpiralTrajParams_C spiral_param;
    WeaveTrajParams_C weave_param;
};

struct ConstantParams_C
{
    TaskFrameType_C frame_type = TaskFrameType_MOTION_FORCE;
    double feature[6] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    bool compliance[6] = { true, true, true, true, true, true };
    double wrench[6] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };

    // 力控调节参数
    double env_stiff[6] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    double damp_scale[6] = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };
    double stiff_scale[6] = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };

    double contact_threshold[6] = {
        1.0, 1.0, 1.0, 0.2, 0.2, 0.2
    };                           // 接触判断阈值
    double constant_time = 5000; // 默认5s
};

struct TouchParams_C
{
    TaskFrameType_C frame_type = TaskFrameType_TOOL_FORCE;
    double feature[6] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    bool compliance[6] = { true, true, true, true, true, true };
    double wrench[6] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    double env_stiff[6] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    //        std::vector<double> damp_scale = { 0.5, 0.5, 0.5, 0.5, 0.5,
    //        0.5 };
    double stiff_scale[6] = { 0.5, 0.5, 0.5, 0.5, 0.5, 0.5 };
    double speed[6] = { 0.1, 0.1, 0.1, 0.1, 0.1, 0.1 };
    double distance = 0.0;
    double touch_time = 1000; // 默认5s
};

#ifdef __cplusplus
extern "C" {
#endif
ARCS_ABI int getTaskForce(FORCE_CONTROL_HANDLER h, TaskFrameType_C type,
                          const double *feature, double *result);

ARCS_ABI int fcTouch(FORCE_CONTROL_HANDLER h, const TouchParams_C &param);

ARCS_ABI int fcConstant(FORCE_CONTROL_HANDLER h, const ConstantParams_C &param);

ARCS_ABI int fcInsert(FORCE_CONTROL_HANDLER h, const InsertParams_C &param);

ARCS_ABI int fcSearch(FORCE_CONTROL_HANDLER h, const SearchParams_C &param);

ARCS_ABI int fcWaitCondition(FORCE_CONTROL_HANDLER h);

ARCS_ABI int fcExit(FORCE_CONTROL_HANDLER h);

// ARCS_ABI void registerStateCallBack(std::function<void(int state)> func);

#ifdef __cplusplus
}
#endif

#endif
