/** @file  sync_move.h
 *  @brief 同步运行
 *
 * 1. Independent movements
 *   If the different task programs, and their robots, work independently, no
 *   synchronization or coordination is needed. Each task program is then
 *   written as if it was the program for a single robot system.
 *
 * 2. Semi coordinated movements
 *   Several robots can work with the same work object, without synchronized
 *   movements, as long as the work object is not moving.
 *   A positioner can move the work object when the robots are not coordinated
 *   to it, and the robots can be coordinated to the work object when it is not
 *   moving. Switching between moving the object and coordinating the robots is
 *   called semi coordinated movements.
 *
 * 3. Coordinated synchronized movements
 *   Several robots can work with the same moving work object.
 *   The positioner or robot that holds the work object and the robots that work
 *   with the work object must have synchronized movements. This means that the
 *   RAPID task programs, that handle one mechanical unit each, execute their
 *   move instructions simultaneously.
 */
#ifndef AUBO_SDK_SYNC_MOVE_INTERFACE_H
#define AUBO_SDK_SYNC_MOVE_INTERFACE_H

#include <vector>
#include <unordered_set>
#include <string>
#include <memory>
#include <aubo/global_config.h>

namespace arcs {
namespace common_interface {

typedef std::unordered_set<std::string> TaskSet;

/**
 * @defgroup SyncMove SyncMove (同步运动控制和轴组管理)
 * \~chinese 同步运动控制和轴组管理API接口
 */
class ARCS_ABI_EXPORT SyncMove
{
public:
    SyncMove();
    virtual ~SyncMove();

    /**
     * @ingroup SyncMove
     * \chinese
     * syncMoveOn 用于启动同步运动模式。
     *
     * syncMoveOn 指令会等待其他任务程序。当所有任务程序都到达 syncMoveOn 时，
     * 它们将继续以同步运动模式执行。不同任务程序中的移动指令将同时执行，
     * 直到执行 syncMoveOff 指令为止。在 syncMoveOn 指令之前必须编程一个停止点。
     *
     * @param syncident
     * @param taskset
     * @return
     *
     * @par Python函数原型
     * syncMoveOn(self: pyaubo_sdk.SyncMove, arg0: str, arg1: Set[str]) -> int
     *
     * @par Lua函数原型
     * syncMoveOn(syncident: string, taskset: table) -> nil
     * @endcoe
     * \endchinese
     * \english
     * syncMoveOn is used to start synchronized movement mode.
     *
     * A syncMoveOn instruction will wait for the other task programs. When
     * all task programs have reached the syncMoveOn, they will continue
     * their execution in synchronized movement mode. The move instructions
     * in the different task programs are executed simultaneously, until the
     * instruction syncMoveOff is executed.
     * A stop point must be programmed before the syncMoveOn instruction.
     *
     * @param syncident
     * @param taskset
     * @return
     *
     * @par Python function prototype
     * syncMoveOn(self: pyaubo_sdk.SyncMove, arg0: str, arg1: Set[str]) -> int
     *
     * @par Lua function prototype
     * syncMoveOn(syncident: string, taskset: table) -> nil
     * @endcoe
     * \endenglish
     */
    int syncMoveOn(const std::string &syncident, const TaskSet &taskset);

    /**
     * @ingroup SyncMove
     * \chinese
     * 设置同步路径段的ID
     * 在同步运动模式下，所有同时执行的移动指令必须全部编程为圆角区（corner zones）或全部为停止点（stop points）。
     * 这意味着具有相同ID的移动指令要么全部带有圆角区，要么全部带有停止点。
     * 如果在各自的任务程序中同步执行的移动指令中，一个带有圆角区而另一个带有停止点，则会发生错误。
     * 同步执行的移动指令可以有不同大小的圆角区（例如，一个使用z10，另一个使用z50）。
     *
     * @param id
     * @return
     *
     * @par Python函数原型
     * syncMoveSegment(self: pyaubo_sdk.SyncMove, arg0: int) -> bool
     *
     * @par Lua函数原型
     * syncMoveSegment(id: number) -> boolean
     * @endcoe
     * \endchinese
     * \english
     * Set the ID for the synchronized path segment.
     * In synchronized movements mode, all or none of the simultaneous move instructions must be programmed with corner zones.
     * This means that move instructions with the same ID must either all have corner zones, or all have stop points.
     * If a move instruction with a corner zone and a move instruction with a stop point are synchronously executed in their respective task program, an error will occur.
     * Synchronously executed move instructions can have corner zones of different sizes (e.g. one uses z10 and one uses z50).
     *
     * @param id
     * @return
     *
     * @par Python prototype
     * syncMoveSegment(self: pyaubo_sdk.SyncMove, arg0: int) -> bool
     *
     * @par Lua prototype
     * syncMoveSegment(id: number) -> boolean
     * @endcoe
     * \endenglish
     */
    bool syncMoveSegment(int id);

    /**
     * @ingroup SyncMove
     * \chinese
     * syncMoveOff 用于结束同步运动模式。
     *
     * syncMoveOff 指令会等待其他任务程序。当所有任务程序都到达 syncMoveOff 时，
     * 它们将继续以非同步模式执行。在 syncMoveOff 指令之前必须编程一个停止点。
     *
     * @param syncident
     * @return
     *
     * @par Python函数原型
     * syncMoveOff(self: pyaubo_sdk.SyncMove, arg0: str) -> int
     *
     * @par Lua函数原型
     * syncMoveOff(syncident: string) -> nil
     * @endcoe
     * \endchinese
     * \english
     * syncMoveOff is used to end synchronized movement mode.
     *
     * A syncMoveOff instruction will wait for the other task programs. When
     * all task programs have reached the syncMoveOff, they will continue
     * their execution in unsynchronized mode.
     * A stop point must be programmed before the syncMoveOff instruction.
     *
     * @param syncident
     * @return
     *
     * @par Python prototype
     * syncMoveOff(self: pyaubo_sdk.SyncMove, arg0: str) -> int
     *
     * @par Lua prototype
     * syncMoveOff(syncident: string) -> nil
     * @endcoe
     * \endenglish
     */
    int syncMoveOff(const std::string &syncident);

    /**
     * @ingroup SyncMove
     * \chinese
     * syncMoveUndo 用于关闭同步运动，即使不是所有其他任务程序都执行了 syncMoveUndo 指令。
     *
     * syncMoveUndo 主要用于 UNDO 处理程序。当程序指针从过程移动时，syncMoveUndo 用于关闭同步。
     *
     * @return
     *
     * @par Python函数原型
     * syncMoveUndo(self: pyaubo_sdk.SyncMove) -> int
     *
     * @par Lua函数原型
     * syncMoveUndo() -> nil
     * @endcoe
     * \endchinese
     * \english
     * syncMoveUndo is used to turn off synchronized movements, even if not
     * all the other task programs execute the syncMoveUndo instruction.
     *
     * syncMoveUndo is intended for UNDO handlers. When the program
     * pointer is moved from the procedure, syncMoveUndo is used to turn off
     * the synchronization.
     *
     * @return
     *
     * @par Python prototype
     * syncMoveUndo(self: pyaubo_sdk.SyncMove) -> int
     *
     * @par Lua prototype
     * syncMoveUndo() -> nil
     * @endcoe
     * \endenglish
     */
    int syncMoveUndo();

    /**
     * @ingroup SyncMove
     * \chinese
     * waitSyncTasks 用于在程序中的特定点同步多个任务程序。
     *
     * waitSyncTasks 指令会等待其他任务程序。当所有任务程序都到达 waitSyncTasks 指令时，
     * 它们将继续执行。
     *
     * @param syncident
     * @param taskset
     * @return
     *
     * @par Python函数原型
     * waitSyncTasks(self: pyaubo_sdk.SyncMove, arg0: str, arg1: Set[str]) -> int
     *
     * @par Lua函数原型
     * waitSyncTasks(syncident: string, taskset: table) -> nil
     * @endcoe
     * \endchinese
     * \english
     * waitSyncTasks is used to synchronize several task programs at a specific
     * point in the program.
     *
     * A waitSyncTasks instruction will wait for the other task programs. When all
     * task programs have reached the waitSyncTasks instruction, they will continue
     * their execution.
     *
     * @param syncident
     * @param taskset
     * @return
     *
     * @par Python prototype
     * waitSyncTasks(self: pyaubo_sdk.SyncMove, arg0: str, arg1: Set[str]) -> int
     *
     * @par Lua prototype
     * waitSyncTasks(syncident: string, taskset: table) -> nil
     * @endcoe
     * \endenglish
     */
    int waitSyncTasks(const std::string &syncident, const TaskSet &taskset);

    /**
     * @ingroup SyncMove
     * \chinese
     * isSyncMoveOn 用于判断机械单元组是否处于同步运动模式。
     *
     * 不控制任何机械单元的任务可以通过该函数判断参数“使用机械单元组”中定义的机械单元是否处于同步运动模式。
     *
     * @return
     *
     * @par Python函数原型
     * isSyncMoveOn(self: pyaubo_sdk.SyncMove) -> bool
     *
     * @par Lua函数原型
     * isSyncMoveOn() -> boolean
     * \endchinese
     * \english
     * isSyncMoveOn is used to tell if the mechanical unit group is in synchronized movement mode.
     *
     * A task that does not control any mechanical unit can find out if the mechanical units defined in the parameter Use Mechanical Unit Group are in synchronized movement mode.
     *
     * @return
     *
     * @par Python prototype
     * isSyncMoveOn(self: pyaubo_sdk.SyncMove) -> bool
     *
     * @par Lua prototype
     * isSyncMoveOn() -> boolean
     * \endenglish
     */
    bool isSyncMoveOn();

    /**
     * @ingroup SyncMove
     * \chinese
     * 暂停同步运动模式。
     *
     * @return
     *
     * @par Python函数原型
     * syncMoveSuspend(self: pyaubo_sdk.SyncMove) -> int
     *
     * @par Lua函数原型
     * syncMoveSuspend() -> nil
     * \endchinese
     * \english
     * Suspend synchronized movement mode.
     *
     * @return
     *
     * @par Python prototype
     * syncMoveSuspend(self: pyaubo_sdk.SyncMove) -> int
     *
     * @par Lua prototype
     * syncMoveSuspend() -> nil
     * \endenglish
     */
    int syncMoveSuspend();

    /**
     * @ingroup SyncMove
     * \chinese
     * 恢复同步运动模式。
     *
     * @return
     *
     * @par Python函数原型
     * syncMoveResume(self: pyaubo_sdk.SyncMove) -> int
     *
     * @par Lua函数原型
     * syncMoveResume() -> nil
     * \endchinese
     * \english
     * Resume synchronized movement mode.
     *
     * @return
     *
     * @par Python prototype
     * syncMoveResume(self: pyaubo_sdk.SyncMove) -> int
     *
     * @par Lua prototype
     * syncMoveResume() -> nil
     * \endenglish
     */
    int syncMoveResume();

    /**
     * @ingroup SyncMove
     * \chinese
     * 添加一个名为 name 的坐标系，其初始位姿为 pose，位姿以 ref_frame 坐标系表达。
     * 此命令仅向世界模型添加一个坐标系，并不会将其附加到 ref_frame 坐标系。
     * 如需将新添加的坐标系附加到 ref_frame，请使用 frameAttach()。
     *
     * @param name: 要添加的坐标系名称。名称不能与任何已存在的世界模型对象（坐标系、轴或轴组）重复，否则会抛出异常。
     * @param pose: 新对象的初始位姿。
     * @param ref_frame: 位姿所表达的参考坐标系对象名称。若未指定，默认使用机器人“base”坐标系。
     *
     * @return
     * \endchinese
     * \english
     * Add a frame with the name "name" initialized at the specified pose
     * expressed in the ref_frame coordinate frame. This command only adds a
     * frame to the world, it does not attach it to the ref_frame coordinate
     * frame. Use frameAttach() to attach the newly added frame to ref_frame if
     * desired.
     *
     * @param name: name of the frame to be added. The name must not be the same
     * as any existing world model object (frame, axis, or axis group),
     * otherwise an exception is thrown
     * @param pose: initial pose of the new object
     * @param ref_frame: name of the world model object whose coordinate frame
     * the pose is expressed in. If nothing is provided here, the default is the
     * robot “base” frame.
     *
     * @return
     * \endenglish
     */
    int frameAdd(const std::string &name, const std::vector<double> &pose,
                 const std::string &ref_name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 将子坐标系附加到父世界模型对象。附加时会设置父子之间的相对变换，使得子坐标系在世界中不会移动。
     *
     * 子坐标系不能为“world”、“flange”、“tcp”，也不能与父坐标系同名。
     *
     * 如果子或父不是已存在的坐标系，或导致形成闭环，则操作会失败。
     *
     * 如果用于 MotionPlus，parent 参数可以是外部轴或轴组的名称。
     *
     * @param child: 要附加的子坐标系名称，不能为“world”、“flange”或“tcp”。
     * @param parent: 子坐标系将要附加到的父对象名称。
     *
     * @return
     * \endchinese
     * \english
     * Attaches the child frame to the parent world model object. The relative
     * transform between the parent and child will be set such that the child
     * does not move in the world when the attachment occurs.
     *
     * The child cannot be “world”, “flange”, “tcp”, or the same as parent.
     *
     * This will fail if child or parent is not an existing frame, or this makes
     * the attachments form a closed chain.
     *
     * If being used with the MotionPlus, the parent argument can be the name of
     * an external axis or axis group.
     *
     * @param child: name of the frame to be attached. The name must not be
     * “world”, “flange”, or “tcp”.
     * @param parent: name of the object that the child frame will be attached
     * to.
     *
     * @return
     * \endenglish
     */
    int frameAttach(const std::string &child, const std::string &parent);

    /**
     * @ingroup SyncMove
     * \chinese
     * 删除所有已添加到世界模型的坐标系。
     *
     * “world”、“base”、“flange”和“tcp”坐标系不能被删除。
     *
     * 任何附加到被删除坐标系的坐标系将会被附加到“world”坐标系，并设置新的偏移，使得被分离的坐标系在世界中不会移动。
     *
     * @return
     * \endchinese
     * \english
     * Delete all frames that have been added to the world model.
     *
     * The “world”, “base”, “flange”, and “tcp” frames cannot be deleted.
     *
     * Any frames that are attached to the deleted frames will be attached to
     * the “world” frame with new frame offsets set such that the detached
     * frames do not move in the world.
     *
     * @return
     * \endenglish
     */
    int frameDeleteAll();

    /**
     * @ingroup SyncMove
     * \chinese
     * 删除指定名称的坐标系。
     *
     * “world”、“base”、“flange”和“tcp”坐标系不能被删除。
     *
     * 任何附加到被删除坐标系的坐标系将会被附加到“world”坐标系，并设置新的偏移，使得被分离的坐标系在世界中不会移动。
     *
     * 如果指定的坐标系不存在，则操作会失败。
     *
     * @param name: 要删除的坐标系名称
     *
     * @return
     * \endchinese
     * \english
     * Delete the frame with name from the world model.
     *
     * The “world”, “base”, “flange”, and “tcp” frames cannot be deleted.
     *
     * Any frames that are attached to the deleted frame will be attached to the
     * “world” frame with new frame offsets set such that the detached frame
     * does not move in the world.
     *
     * This command will fail if the frame does not exist.
     *
     * @param name: name of the frame to be deleted
     *
     * @return
     * \endenglish
     */
    int frameDelete(const std::string &name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 更改名为 name 的坐标系的位置，将其移动到由 pose 指定的新位置，pose 以 ref_name 坐标系表达。
     *
     * 如果 name 为 “world”、“flange”、“tcp”，或该坐标系不存在，则操作会失败。注意：如需移动 “tcp” 坐标系，请使用 set_tcp() 命令。
     *
     * 如果用于 MotionPlus，ref_name 参数可以是外部轴或轴组的名称。
     *
     * @param name: 要移动的坐标系名称
     * @param pose: 新的位置
     * @param ref_name: pose 所表达的参考坐标系，默认值为机器人的 “base” 坐标系。
     *
     * @return
     * \endchinese
     * \english
     * Changes the placement of the coordinate frame named name to the new
     * placement given by pose that is defined in the ref_name coordinate frame.
     *
     * This will fail if name is “world”, “flange”, “tcp”, or if the frame does
     * not exist. Note: to move the “tcp” frame, use the set_tcp() command
     * instead.
     *
     * If being used with the MotionPlus, the ref_name argument can be the name
     * of an external axis or axis group.
     *
     * @param name: the name of the frame to move
     * @param pose: the new placement
     * @param ref_name: the coordinate frame that pose is expressed in. The
     * default value is the robot’s “base” frame.
     *
     * @return
     * \endenglish
     */
    int frameMove(const std::string &name, const std::vector<double> &pose,
                  const std::string &ref_name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 获取名为 name 的坐标系相对于 rel_frame 坐标系的位姿，并以 ref_frame 坐标系表达。
     * 如果未提供 ref_frame，则返回 name 坐标系相对于 rel_frame 坐标系的位姿，并以 rel_frame 坐标系表达。
     *
     * 如果任一参数不是已存在的坐标系，则操作会失败。
     *
     * 如果用于 MotionPlus，所有三个参数也可以是外部轴或轴组的名称。
     *
     * @param name: 要查询的坐标系名称。
     * @param rel_frame: “相对坐标系”，用于计算相对位姿的坐标系。
     * @param ref_frame: “参考坐标系”，用于表达结果相对位姿的坐标系。如果未提供，则默认为 rel_frame。
     *
     * @return 以 ref_frame 坐标系表达的 name 坐标系的位姿。
     * \endchinese
     * \english
     * Get the pose of the name frame relative to the rel_frame frame but
     * expressed in the coordinates of the ref_frame frame. If ref_frame is not
     * provided, then this returns the pose of the name frame relative to and
     * expressed in the same frame as rel_frame.
     *
     * This will fail if any arguments are not an existing frame.
     *
     * If being used with MotionPlus, all three arguments can also be the names
     * of external axes or axis groups.
     *
     * @param name: name of the frame to query.
     * @param rel_frame: short for “relative frame” is the frame where the pose
     * is computed relative to
     * @param ref_frame: short for “reference frame” is the frame to express the
     * coordinates of resulting relative pose in. If this is not provided, then
     * it will default to match the value of rel_frame.
     *
     * @return The pose of the frame expressed in the ref_frame coordinates.
     * \endenglish
     */
    std::vector<double> frameGetPose(const std::string &name,
                                     const std::string &rel_frame,
                                     const std::string &ref_frame);

    /**
     * @ingroup SyncMove
     * \chinese
     * 将位姿从 from_frame 坐标系转换到 to_frame 坐标系。
     *
     * 如果任一坐标系参数不是已存在的坐标系，则操作会失败。
     *
     * 如果用于 MotionPlus，所有三个参数也可以是外部轴或轴组的名称。
     *
     * @param pose: 要转换的位姿
     * @param from_frame: 原始坐标系的参考坐标系名称
     * @param to_frame: 新坐标系的参考坐标系名称
     *
     * @return 以 to_frame 坐标系表达的 pose 值。
     * \endchinese
     * \english
     * Convert pose from from_frame to to_frame.
     *
     * This will fail if either coordinate system argument is not an existing
     * frame.
     *
     * If being used with MotionPlus, all three arguments can also be the names
     * of external axes or axis groups.
     *
     * @param pose: pose to be converted
     * @param from_frame: name of reference frame at origin of old coordinate
     * system
     * @param to_frame: name of reference frame at origin of new coordinate
     * system
     *
     * @return Value of pose expressed in the coordinates of to_frame.
     * \endenglish
     */
    std::vector<double> frameConvertPose(const std::vector<double> &pose,
                                         const std::string &from_frame,
                                         const std::string &to_frame);

    /**
     * @ingroup SyncMove
     * \chinese
     * 查询指定名称的坐标系是否存在。
     *
     * @param name: 要查询的坐标系名称。
     *
     * @return 如果存在该名称的坐标系则返回 true，否则返回 false。
     * \endchinese
     * \english
     * Queries for the existence of a frame by the given name.
     *
     * @param name: name of the frame to be queried.
     *
     * @return Returns true if there is a frame by the given name, false if not.
     * \endenglish
     */
    bool frameExist(const std::string &name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 获取名为 name 的坐标系在世界模型中的父坐标系名称。
     *
     * 如果该坐标系没有附加到其他坐标系，则其父坐标系为 "world"。
     *
     * @param name: 要查询的坐标系名称
     *
     * @return 父坐标系的名称，字符串类型
     * \endchinese
     * \english
     * Get the parent of the frame named name in the world model.
     *
     * If the frame is not attached to another frame, then “world” is the
     * parent.
     *
     * @param name: the frame being queried
     *
     * @return name of the parent as a string
     * \endenglish
     */
    std::string frameGetParent(const std::string &name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 返回指定父对象的直接子对象坐标系名称列表。父子关系由世界模型的附加关系定义。
     * 如果用于 MotionPlus，子对象也可以是轴组或轴。
     *
     * @param name: 父对象的名称。
     *
     * @return 直接子对象坐标系名称列表
     * \endchinese
     * \english
     * Returns a list of immediate child object frame names. Parent-child
     * relationships are defined by world model attachments. If being used with
     * MotionPlus, the child objects may also be an axis group or an axis.
     *
     * @param name: the name of the parent object.
     *
     * @return a list of immediate child object frame names
     * \endenglish
     */
    std::vector<std::string> frameGetChildren(const std::string &name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 向世界模型添加一个新的轴组，名称为 name。轴组基座放置在 ref_frame 坐标系下的 pose 位置。
     *
     * 轴组只能附加到世界坐标系。
     *
     * 每个轴组的基座都附加有一个坐标系，可以通过轴组名称作为参数传递给其他世界模型函数。
     *
     * 世界模型最多可添加 6 个轴组。
     *
     * @param name: 要添加的轴组名称，不能为空字符串。世界模型对象（如坐标系、轴组、轴等）的名称必须唯一。
     * @param pose: 轴组基座在参考坐标系下的位姿。
     * @param ref_frame (可选): pose 所在的参考坐标系名称，可以是任何带有坐标系的世界模型实体（如坐标系、轴组、轴等）。默认值 "base" 表示机器人基座坐标系。
     *
     * @return
     * \endchinese
     * \english
     * Adds a new axis group with the given name to the world model. It is
     * placed at the given pose in the reference coordinate frame defined by
     * ref_frame.
     *
     * An axis group can only be attached to the world coordinate frame.
     *
     * Each axis group has a coordinate frame attached to its base, which can be
     * used as an argument to other world model functions by referring the name
     * of the group.
     *
     * At most 6 axis groups can be added to the world model.
     *
     * @param name: (string) Name of the axis group to add. The name cannot be
     * an empty string. Names used by world model objects (e.g., frame, axis
     * group, axis, etc.) must be unique.
     *
     * @param pose: (pose) Pose of the axis group’s base, in the reference
     * coordinate frame.
     *
     * @param ref_frame (optional): (string) Name of the reference coordinate
     * frame that pose is defined in. This can be any world model entity with a
     * coordinate system (e.g., frame, axis group, axis, etc.). The default
     * value "base" refers to the robot’s base frame.
     *
     * @return
     * \endenglish
     */
    int axisGroupAdd(const std::string &name, const std::vector<double> &pose,
                     const std::string &ref_frame);

    /**
     * @ingroup SyncMove
     * \chinese
     * 删除具有给定名称的轴组。
     *
     * 所有附加的轴也会被禁用（如果处于活动状态）并删除。
     *
     * 如果该轴组正被其他函数控制，则操作会失败。
     *
     * @param name: 要删除的轴组名称。该名称的轴组必须存在。
     *
     * @return
     * \endchinese
     * \english
     * Deletes the axis group with the given name from the world model.
     *
     * All attached axes are also disabled (if live) and deleted.
     *
     * This function will fail, if this axis group is under control by another function.
     *
     * @param name: (string) Name of the axis group to delete. Axis group with
     * such name must exist.
     *
     * @return
     * \endenglish
     */
    int axisGroupDelete(const std::string &name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 向名为 group_name 的轴组添加一个名为 name 的外部轴。该轴在 parent 坐标系下的 pose 位置附加，pose 表示轴位置为 0 时的位姿。
     * 轴的类型、最大速度、最大加速度、位置限制和索引分别由 type、v_limit、a_limit、q_limits 和 axis_index 定义。
     * pose 参数通常通过外部轴调试标定流程获得。
     * 如果该轴组正被其他函数控制，或附加关系形成闭环，则操作会失败。
     *
     * @param group_name: 要添加轴的轴组名称，需已通过 axis_group_add() 创建且存在。
     * @param name: 新轴的名称，不能为空且需唯一。
     * @param parent: 父轴名称，若为空或与 group_name 相同，则附加到轴组基座。父轴需已存在于该轴组。
     * @param pose: 轴在父坐标系下的零位姿。type 为 0（旋转轴）时，z 轴为旋转轴；type 为 1（直线轴）时，z 轴为移动方向。
     * @param type: 轴类型，0 表示旋转轴，1 表示直线轴。
     * @param v_limit: 最大速度。
     * @param a_limit: 最大加速度。
     * @param q_limits: 位置限制。
     * @param axis_index: 轴索引。
     * \endchinese
     * \english
     * Adds an external axis with the given name to the axis group named group_name.
     * The axis is attached at the given pose in the reference coordinate frame defined by parent when its axis position is 0.
     * The type, max velocity, max acceleration, position limits, and index of this axis are defined by type, v_limit, a_limit, q_limits, and axis_index, respectively.
     * The pose parameter is typically obtained from a calibration process when the external axis is commissioned.
     * This function will fail if this axis group is under control of another function, or if the kinematic chain created by the attachment forms a closed chain.
     *
     * @param group_name: Name of the axis group this new axis is added to. The axis group would have been created using axis_group_add(). Axis group with such name must exist.
     * @param name: Name of the new axis. The name cannot be an empty string. Names used by world model objects (e.g., frame, axis group, axis, etc.) must be unique.
     * @param parent: Name of the parent axis. If it’s empty or the same as group_name, the new axis will be attached to the base of the axis group. Axis with such name must exist in the axis group.
     * @param pose: The zero-position pose, in the parent coordinate frame, this axis will be placed and attached to. This is the pose the axis will be (relative to its parent) when its axis position is 0. If type is 0 (rotary), then the z axis of the frame corresponds to the axis of rotation. If type is 1 (linear), then the z axis is the axis of translation.
     * @param type: Axis type, 0 for rotary, 1 for linear.
     * @param v_limit: Maximum velocity.
     * @param a_limit: Maximum acceleration.
     * @param q_limits: Position limits.
     * @param axis_index: Axis index.
     * \endenglish
     */
    int axisGroupAddAxis(const std::string &group_name, const std::string &name,
                         const std::string &parent,
                         const std::vector<double> &pose);

    /**
     * @ingroup SyncMove
     * \chinese
     * 更新指定名称的轴的相关属性。pose 参数通常通过外部轴调试标定流程获得。
     * 如果该轴所属的轴组正被其他命令控制，则操作会失败。
     * 如果该轴组中任何已附加的轴处于激活和使能状态，则操作会失败。
     *
     * @param name: 要更新的轴的名称，需已存在。
     * @param pose (可选): 轴在父轴（或轴组）坐标系下的零位姿。即轴位置为 0 时的位姿。
     * \endchinese
     * \english
     * Updates the corresponding properties of axis with name. The pose
     * parameter is typically obtained from a calibration process when the
     * external axis is commissioned. See here for a guide on a basic routine
     * for calibrating a single rotary axis.
     *
     * This function will fail, if the axis group the axis attached to is
     * already being controlled by another command.
     * This function will fail, if any attached axis of the axis group is live
     * and enabled.
     *
     * @param name: (string) Name of the axis to update. Axis with such name
     * must exist.
     *
     * @param pose (optional): (pose) New zero-position pose, in the coordinate
     * frame of the parent axis (or axis group), of the axis. This is the pose
     * of the axis when its axis position is 0.
     * \endenglish
     */
    int axisGroupUpdateAxis(const std::string &name,
                            const std::vector<double> &pose);

    /**
     * @ingroup SyncMove
     * \chinese
     * 返回指定轴名称在 RTDE 目标位置和实际位置数组中的索引。
     *
     * @param axis_name: (string) 要查询的轴名称。该名称的轴必须存在。
     *
     * @return integer: 该轴在 RTDE 目标位置和实际位置数组中的索引。
     * \endchinese
     * \english
     * Returns the index of the axis with given axis_name in the RTDE target
     * positions and actual positions arrays.
     *
     * @param axis_name: (string) Name of the axis in query.
     * Axis with such name must exist.
     *
     * @return integer: Index of the axis in the RTDE target positions and
     * actual positions arrays.
     * \endenglish
     */
    int axisGroupGetAxisIndex(const std::string &name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 返回指定轴索引对应的轴名称。
     *
     * @param axis_index: (整数) 要查询的轴索引。该索引的轴必须存在。
     *
     * @return 字符串: 轴的名称。
     * \endchinese
     * \english
     * Returns the name of the axis with the given axis_index.
     *
     * @param axis_index: (integer) Index of the axis in query.
     * Axis with such index must exist.
     *
     * @return string: Name of the axis.
     * \endenglish
     */
    std::string axisGroupGetAxisName(int index);

    /**
     * @ingroup SyncMove
     * \chinese
     * 返回指定轴组的当前目标位置。
     * 如果未指定 group_name，则返回所有外部轴的目标位置。
     *
     * 如果外部轴总线被禁用，则该函数会失败。
     *
     * @param group_name (可选): (string) 要查询的轴组名称。该名称的轴组必须真实存在。
     *
     * @return Double[]: 涉及轴的目标位置，顺序为其外部轴索引顺序。
     * \endchinese
     * \english
     * Returns the current target positions of the axis group with group_name.
     * If group_name is not provided, the target positions of all external axes
     * will be returned.
     *
     * This function will fail, if the external axis bus is disabled.
     *
     * @param group_name (optional): (string) Name of the axis group in query.
     * Axis group with such name must REALLY exist.
     *
     * @return Double[]: Target positions of the involved axes, in the order of
     * their external axis indices.
     * \endenglish
     */
    std::vector<double> axisGroupGetTargetPositions(
        const std::string &group_name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 返回指定轴组的当前实际位置。
     * 如果未指定 group_name，则返回所有外部轴的实际位置。
     *
     * 如果外部轴总线被禁用，则该函数会失败。
     *
     * @param group_name (可选): (string) 要查询的轴组名称。该名称的轴组必须真实存在。
     *
     * @return Double[]: 涉及轴的实际位置，顺序为其外部轴索引顺序。
     * \endchinese
     * \english
     * Returns the current actual positions of the axis group with group_name.
     * If group_name is not provided, the actual positions of all external axes
     * will be returned.
     *
     * This function will fail, if the external axis bus is disabled.
     *
     * @param group_name (optional): (string) Name of the axis group in query.
     * Axis group with such name must exist.
     *
     * @return Double[]: Actual positions of the involved axes, in the order of
     * their external axis indices.
     * \endenglish
     */
    std::vector<double> axisGroupGetActualPositions(
        const std::string &group_name);

    /**
     * @ingroup SyncMove
     * \chinese
     * 通过给定的 offset，将轴组 group_name 的目标位置和实际位置整体偏移。
     *
     * 这是一个仅在控制器内部进行的软件偏移，不会影响外部轴驱动器。该偏移也会应用于通过 RTDE 发布的任何目标和实际位置流。
     *
     * @param group_name: (string) 要应用偏移的轴组名称。该名称的轴组必须存在。
     *
     * @param offset: (float[]) 目标和实际位置需要整体偏移的量。offset 的大小必须与该轴组所包含的轴数量一致。
     *
     * @return
     * \endchinese
     * \english
     * Shifts the target and actual positions of the axis group group_name by
     * the given offset.
     *
     * This is a software shift that happens in the controller only, it does not
     * affect external axis drives. The shift is also applied to any streamed
     * target and actual positions published on RTDE.
     *
     * @param group_name: (string) Name of the axis group to apply the offset
     * positions to. Axis group with such name must exist.
     *
     * @param offset: (float[]) Offsets that the target and actual positions
     * should be shifted by. The size of offset must match the number of axes
     * attached to the given group.
     *
     * @return
     * \endenglish
     */
    int axisGroupOffsetPositions(const std::string &group_name,
                                 const std::vector<double> &offset);

    /**
     * @ingroup SyncMove
     * \chinese
     * 以梯形速度曲线将名为 group_name 的轴组移动到新的位置 q。
     * 参数 a 指定本次运动的最大加速度占各轴加速度极限的百分比。
     * 参数 v 指定本次运动的最大速度占各轴速度极限的百分比。
     *
     * 实际的加速度和速度由最受限制的轴决定，以确保所有轴在加速、匀速和减速阶段同时完成。
     *
     * @param group_name: (string) 要移动的轴组名称。该名称的轴组必须存在。
     * @param q: (float[]) 目标位置，旋转轴为弧度，直线轴为米。如果目标超出位置极限，则会被限制在最近的极限值。涉及的轴按其索引递增排序。q 的大小必须与该轴组包含的轴数量一致。
     * @param a: (float) 本次运动的最大加速度因子，取值范围 (0,1]，表示占加速度极限的百分比。
     * @param v: (float) 本次运动的最大速度因子，取值范围 (0,1]，表示占速度极限的百分比。
     *
     * 返回值: 无
     * \endchinese
     * \english
     * Moves the axes of axis group named group_name to new positions q, using a
     * trapezoidal velocity profile. Factor a specifying the percentage of the
     * max profile accelerations out of the acceleration limits of each axes.
     * Factor v specifying the percentage of the max profile velocities out of
     * the velocity limits of each axes.
     *
     * The actual accelerations and velocities are determined by the most
     * constraining axis, so that all the axes complete the acceleration,
     * cruise, and deceleration phases at the same time.
     *
     * @param group_name: (string) Name of the axis group to move.
     * Axis group with such name must exist.
     *
     * @param q: (float[]) Target positions in rad (rotary) or in m (linear). If
     * the target exceeds the position limits, then it is set to the nearest
     * limit. The involved axes are ordered increasingly by their axis indices.
     * The size of q must match the number of axes attached to the given group.
     *
     * @param a: (float) Factor specifying the max accelerations of this move
     * out of the acceleration limits. a must be in range of (0,1].
     *
     * @param v: (float) Factor specifying the max velocities of this move out
     * of the velocity limits. v must be in range of (0,1].
     *
     * Return: n/a
     * \endenglish
     */
    int axisGroupMoveJoint(const std::string &group_name,
                           const std::vector<double> &q, double a, double v);

    /**
     * @ingroup SyncMove
     * \chinese
     * 以指定的加速度因子 a，将名为 group_name 的轴组加速到目标速度 qd。该函数会运行 t 秒。
     * @param group_name: (string) 要控制的外部轴组名称，必须已存在。
     * @param qd: (float[]) 轴组各轴的目标速度。如果目标速度超过速度极限，则会被限制在极限值。涉及的轴按其索引递增排序。qd 的大小必须与该轴组包含的轴数量一致。
     * @param a: (float) 本次运动的最大加速度因子，取值范围 (0,1]，表示占加速度极限的百分比。
     * @param t (可选): (float) 函数运行的持续时间（秒）。若 t < 0，则函数将在目标速度达到时返回；若 t ≥ 0，则函数将在该持续时间后返回，无论实际速度是否达到目标值。
     * \endchinese
     * \english
     * Accelerates the axes of axis group named group_name up to the target
     * velocities qd. Factor a specifying the percentage of the max
     * accelerations out of the acceleration limits of each axes. The function
     * will run for a period of t seconds.
     *
     * @param group_name: (string) Name of the external axis group to control.
     * Axis group with such name must exist.
     *
     * @param qd: (float[]) Target velocities for the axes in the axis group. If
     * the target exceeds the velocity limits, then it is set to the limit. The
     * involved axes are ordered increasingly by their axis indices. The size of
     * qd must match the number of axes attached to the given group.
     *
     * @param a: (float) Factor specifying the max accelerations of this move
     * out of the acceleration limits. a must be in range of (0,1].
     *
     * @param t (optional): (float) Duration in seconds before the function
     * returns. If t < 0, then the function will return when the target
     * velocities are reached. if t ≥ 0, then the function will return after
     * this duration, regardless of what the achieved axes velocities are.
     * \endenglish
     */
    int axisGroupSpeedJoint(const std::string &group_name,
                            const std::vector<double> &qd, double a, double t);

protected:
    void *d_;
};

using SyncMovePtr = std::shared_ptr<SyncMove>;
} // namespace common_interface
} // namespace arcs
#endif // AUBO_SDK_SYNC_MOVE_INTERFACE_H
