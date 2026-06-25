"""Tests for app.core.action_maps — Quick Action to Route/Module Binding."""

from app.core.action_maps import (
    ALL_ACTION_MAPS,
    DASHBOARD_QUICK_ACTIONS,
    ActionType,
    QuickAction,
    filter_actions_by_role,
    get_action,
    get_page_actions,
    render_action_button,
)


# ---------------------------------------------------------------------------
# ActionType enum
# ---------------------------------------------------------------------------
class TestActionType:
    def test_members(self):
        expected = {"NAVIGATE", "TRIGGER", "OPEN", "DOWNLOAD", "SHARE", "EXTERNAL"}
        assert {m.name for m in ActionType} == expected


# ---------------------------------------------------------------------------
# QuickAction dataclass
# ---------------------------------------------------------------------------
class TestQuickAction:
    def test_defaults(self):
        qa = QuickAction(action_id="x", label="X")
        assert qa.action_type is ActionType.NAVIGATE
        assert qa.icon is None
        assert qa.target is None
        assert qa.target_params is None
        assert qa.telemetry_event is None
        assert qa.required_roles is None
        assert qa.confirmation_prompt is None
        assert qa.disabled_states is None

    def test_full_construction(self):
        qa = QuickAction(
            action_id="a",
            label="A",
            icon="star",
            action_type=ActionType.TRIGGER,
            target="/go",
            target_params={"k": "v"},
            telemetry_event="ev",
            required_roles=["admin"],
            confirmation_prompt="Sure?",
            disabled_states=["locked"],
        )
        assert qa.action_id == "a"
        assert qa.target_params == {"k": "v"}
        assert qa.confirmation_prompt == "Sure?"


# ---------------------------------------------------------------------------
# Registry dicts
# ---------------------------------------------------------------------------
class TestRegistryCompleteness:
    def test_all_action_maps_keys(self):
        expected_keys = {
            "dashboard",
            "vault",
            "documents",
            "court_packet",
            "eviction_answer",
            "hearing_prep",
            "storage_setup",
            "crisis_intake",
        }
        assert set(ALL_ACTION_MAPS.keys()) == expected_keys

    def test_dashboard_actions_not_empty(self):
        assert len(DASHBOARD_QUICK_ACTIONS) > 0

    def test_vault_and_documents_share_same_dict(self):
        assert ALL_ACTION_MAPS["vault"] is ALL_ACTION_MAPS["documents"]

    def test_every_action_has_label(self):
        for page_id, actions in ALL_ACTION_MAPS.items():
            for action_id, action in actions.items():
                assert action.label, f"{page_id}/{action_id} missing label"

    def test_every_action_id_matches_key(self):
        for page_id, actions in ALL_ACTION_MAPS.items():
            for key, action in actions.items():
                assert action.action_id == key, (
                    f"{page_id}: key={key} but action_id={action.action_id}"
                )


# ---------------------------------------------------------------------------
# get_page_actions
# ---------------------------------------------------------------------------
class TestGetPageActions:
    def test_returns_dict_for_known_page(self):
        result = get_page_actions("dashboard")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_returns_empty_for_unknown_page(self):
        assert get_page_actions("nonexistent_page") == {}


# ---------------------------------------------------------------------------
# get_action
# ---------------------------------------------------------------------------
class TestGetAction:
    def test_returns_action_for_known_pair(self):
        action = get_action("dashboard", "view_deadlines")
        assert action is not None
        assert action.action_id == "view_deadlines"

    def test_returns_none_for_unknown_action(self):
        assert get_action("dashboard", "does_not_exist") is None

    def test_returns_none_for_unknown_page(self):
        assert get_action("no_such_page", "view_deadlines") is None


# ---------------------------------------------------------------------------
# filter_actions_by_role
# ---------------------------------------------------------------------------
class TestFilterActionsByRole:
    def test_no_role_restriction_passes_all(self):
        actions = {
            "a": QuickAction(action_id="a", label="A"),
        }
        result = filter_actions_by_role(actions, ["user"])
        assert "a" in result

    def test_matching_role_included(self):
        actions = {
            "a": QuickAction(
                action_id="a", label="A", required_roles=["admin", "user"]
            ),
        }
        result = filter_actions_by_role(actions, ["user"])
        assert "a" in result

    def test_non_matching_role_excluded(self):
        actions = {
            "a": QuickAction(
                action_id="a", label="A", required_roles=["admin"]
            ),
        }
        result = filter_actions_by_role(actions, ["user"])
        assert "a" not in result

    def test_mixed_filter(self):
        actions = {
            "pub": QuickAction(action_id="pub", label="Public"),
            "adm": QuickAction(
                action_id="adm", label="Admin", required_roles=["admin"]
            ),
            "usr": QuickAction(
                action_id="usr", label="User", required_roles=["user"]
            ),
        }
        result = filter_actions_by_role(actions, ["user"])
        assert set(result.keys()) == {"pub", "usr"}

    def test_dashboard_role_filter(self):
        result = filter_actions_by_role(DASHBOARD_QUICK_ACTIONS, ["user"])
        assert "view_deadlines" in result
        assert "prepare_answer" in result

    def test_dashboard_role_filter_visitor(self):
        result = filter_actions_by_role(DASHBOARD_QUICK_ACTIONS, ["visitor"])
        assert "view_deadlines" in result
        assert "prepare_answer" not in result


# ---------------------------------------------------------------------------
# render_action_button
# ---------------------------------------------------------------------------
class TestRenderActionButton:
    def test_basic_render(self):
        action = QuickAction(
            action_id="dl",
            label="Download",
            icon="download",
            action_type=ActionType.DOWNLOAD,
            target="/file",
        )
        rendered = render_action_button(action)
        assert rendered["id"] == "dl"
        assert rendered["label"] == "Download"
        assert rendered["icon"] == "download"
        assert rendered["type"] == "download"
        assert rendered["target"] == "/file"
        assert rendered["params"] == {}
        assert rendered["confirmation"] is None

    def test_render_with_params_and_confirmation(self):
        action = QuickAction(
            action_id="x",
            label="X",
            action_type=ActionType.TRIGGER,
            target_params={"a": 1},
            confirmation_prompt="Are you sure?",
        )
        rendered = render_action_button(action)
        assert rendered["params"] == {"a": 1}
        assert rendered["confirmation"] == "Are you sure?"

    def test_action_type_lowercased(self):
        for at in ActionType:
            action = QuickAction(action_id="t", label="T", action_type=at)
            rendered = render_action_button(action)
            assert rendered["type"] == at.name.lower()
