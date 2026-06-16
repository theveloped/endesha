#ifndef AUBO_SDK_FORCE_CONTROL_TYPE_CONVERT_C_H
#define AUBO_SDK_FORCE_CONTROL_TYPE_CONVERT_C_H

#include <skill_interface/force_control.h>
#include <skill_interface/force_control_c.h>

// 用于将SpiralTrajParams_C转化为SpiralTrajParams
inline arcs::aubo_sdk::ForceControl::SpiralTrajParams convertToSpiralTrajParams(
    const SpiralTrajParams_C &source)
{
    arcs::aubo_sdk::ForceControl::SpiralTrajParams result;

    result.step = source.step;
    result.direction = source.direction;
    result.plane = (arcs::aubo_sdk::ForceControl::SpiralPlane)source.plane;
    result.spiral = source.spiral;
    result.helix = source.helix;
    result.radius = source.radius;

    return result;
}

// 用于将WeaveTrajParams_C转化为WeaveTrajParams
inline arcs::aubo_sdk::ForceControl::WeaveTrajParams convertToWeaveTrajParams(
    const WeaveTrajParams_C &source)
{
    arcs::aubo_sdk::ForceControl::WeaveTrajParams result;

    result.step = source.step;
    result.amplitude = source.amplitude;
    result.direction =
        (arcs::aubo_sdk::ForceControl::WeaveSelect)source.direction;
    result.hold_distance = source.hold_distance;
    result.angle = source.angle;
    result.type = source.type;

    return result;
}

// 用于将TouchParams_C转化为TouchParams
inline arcs::aubo_sdk::ForceControl::TouchParams convertToTouchParams(
    const TouchParams_C &source)
{
    arcs::aubo_sdk::ForceControl::TouchParams result;

    result.frame_type =
        (arcs::common_interface::TaskFrameType)source.frame_type;

    for (int i = 0; i < 6; i++) {
        result.feature[i] = source.feature[i];
        result.compliance[i] = source.compliance[i];
        result.wrench[i] = source.wrench[i];
        result.env_stiff[i] = source.env_stiff[i];
        result.stiff_scale[i] = source.stiff_scale[i];
        result.speed[i] = source.speed[i];
    }
    result.distance = source.distance;
    result.touch_time = source.touch_time;

    return result;
}

inline arcs::aubo_sdk::ForceControl::ConstantParams convertToConstantParams(
    const ConstantParams_C &source)
{
    arcs::aubo_sdk::ForceControl::ConstantParams result;

    result.frame_type =
        (arcs::common_interface::TaskFrameType)source.frame_type;
    for (int i = 0; i < 6; i++) {
        result.feature[i] = source.feature[i];
        result.compliance[i] = source.compliance[i];
        result.wrench[i] = source.wrench[i];
        result.env_stiff[i] = source.env_stiff[i];
        result.damp_scale[i] = source.damp_scale[i];
        result.stiff_scale[i] = source.stiff_scale[i];
        result.contact_threshold[i] = source.contact_threshold[i];
    }                                            // 接触判断阈值
    result.constant_time = source.constant_time; // 默认5sams result;

    return result;
}

inline arcs::aubo_sdk::ForceControl::InsertParams convertToInsertParams(
    const InsertParams_C &source)
{
    arcs::aubo_sdk::ForceControl::InsertParams result;

    result.insert_select =
        (arcs::aubo_sdk::ForceControl::InsertSelect)source.insert_select;
    result.hole_diameter = source.hole_diameter;
    result.insert_max_speed = source.insert_max_speed;
    result.insert_time = source.insert_time;
    result.guide_traj_type =
        (arcs::aubo_sdk::ForceControl::GuideTrajType)source.guide_traj_type;
    result.insert_max_depth = source.insert_max_depth;
    result.insert_guide_force = source.insert_guide_force;
    for (int i = 0; i < 6; i++) {
        result.insert_max_force[i] = source.insert_max_force[i];
        result.insert_damp_scale[i] = source.insert_damp_scale[i];
        result.insert_stiff_scale[i] = source.insert_stiff_scale[i];
    }

    result.spiral_param = convertToSpiralTrajParams(source.spiral_param);
    result.weave_param = convertToWeaveTrajParams(source.weave_param);

    return result;
}

// 用于将SearchParams_C转化为SearchParams
inline arcs::aubo_sdk::ForceControl::SearchParams convertToSearchParams(
    const SearchParams_C &source)
{
    arcs::aubo_sdk::ForceControl::SearchParams result;

    result.search_plane =
        (arcs::aubo_sdk::ForceControl::SearchPlane)source.search_plane;
    result.hole_diameter = source.hole_diameter;
    result.search_range = source.search_range;
    result.search_time = source.search_time;
    result.guide_traj_type =
        (arcs::aubo_sdk::ForceControl::GuideTrajType)source.guide_traj_type;
    result.search_max_force = source.search_max_force;
    result.search_guide_force = source.search_guide_force;
    for (int i = 0; i < 6; i++) {
        result.search_damp_scale[i] = source.search_damp_scale[i];
        result.search_stiff_scale[i] = source.search_stiff_scale[i];
    }
    result.spiral_param = convertToSpiralTrajParams(source.spiral_param);
    result.weave_param = convertToWeaveTrajParams(source.weave_param);

    return result;
}

#endif
