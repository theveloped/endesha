from wf.contracts.washer import keys
from wf.contracts.washer.messages import (
    ParamSpec,
    Recipe,
    RecipeReply,
    RecipeSchema,
    RecipeStep,
    SetRecipe,
    WasherStatus,
)


def test_keys():
    assert keys.state_status("cell", "w0") == "cell/washer/w0/state/status"
    assert keys.action_prefix("cell", "w0") == "cell/washer/w0/action"
    assert keys.cmd_set_recipe("replay/abc", "w0") == "replay/abc/washer/w0/cmd/set_recipe"


def test_status_round_trip():
    st = WasherStatus(t=1, phase="washing", door="closed", connected=True, auto=True, washing=True,
                      program="Standard", program_no=3, sequence=None, detail="cycle running")
    assert WasherStatus.from_wire(st.to_wire()) == st
    # tolerant of a minimal payload
    assert WasherStatus.from_wire({"t": 5}).phase == "initializing"


def test_recipe_round_trip_and_validation():
    schema = RecipeSchema(
        steps=2,
        step_fields={"cleaning": ParamSpec("Cleaning", choices=[0, 1]), "time_s": ParamSpec("Time", 10, 600),
                     "movement": ParamSpec("Move", choices=[0, 1, 2]), "additional": ParamSpec("Add", choices=[0]),
                     "pump_off": ParamSpec("Pump off")},
        params={"rpm": ParamSpec("Speed", 1, 9)},
    )
    r = Recipe(name="A", steps=[RecipeStep(1, 120, 2, 0, False)], params={"rpm": 4})
    assert Recipe.from_wire(r.to_wire()) == r
    assert schema.validate(r) is None
    assert schema.validate(Recipe(steps=[RecipeStep(1, 5)])) == "bad_recipe:steps[0].time_s < 10"
    assert schema.validate(Recipe(params={"foo": 1})) == "bad_recipe:unknown param foo"
    assert schema.validate(Recipe(params={"rpm": 10})) == "bad_recipe:rpm > 9"
    assert schema.validate(Recipe(steps=[RecipeStep(), RecipeStep(), RecipeStep()])) == "bad_recipe:at most 2 steps"
    reply = RecipeReply.from_wire(RecipeReply(recipe=r, schema=schema).to_wire())
    assert reply.recipe == r and reply.schema.params["rpm"].max == 9
    assert SetRecipe.from_wire(SetRecipe(r).to_wire()).recipe == r
