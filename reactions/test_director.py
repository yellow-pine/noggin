from reactions.director import Director

def prompt(sid="s1"):
    return {"hook_event_name": "UserPromptSubmit", "session_id": sid}

def stop(sid="s1"):
    return {"hook_event_name": "Stop", "session_id": sid}

def test_quick_turn_plays_small_eureka():
    d = Director()
    d.handle(prompt(), now=100.0)
    assert "eureka 1" in d.handle(stop(), now=105.0)

def test_normal_turn_plays_normal_eureka():
    d = Director()
    d.handle(prompt(), now=100.0)
    assert "eureka 2" in d.handle(stop(), now=160.0)

def test_long_turn_plays_big_eureka():
    d = Director()
    d.handle(prompt(), now=100.0)
    assert "eureka 3" in d.handle(stop(), now=100.0 + 4 * 60)

def test_stop_without_known_prompt_plays_normal_eureka():
    assert "eureka 2" in Director().handle(stop(), now=5.0)

def test_prompt_starts_thinking():
    assert Director().handle(prompt(), now=1.0) == ["thinking"]

def test_second_session_prompt_does_not_repeat_thinking():
    d = Director()
    d.handle(prompt("a"), now=1.0)
    assert d.handle(prompt("b"), now=2.0) == []

def test_stop_rests_when_no_session_is_mid_turn():
    d = Director()
    d.handle(prompt(), now=1.0)
    assert d.handle(stop(), now=5.0) == ["eureka 1", "rest"]

def test_stop_keeps_thinking_while_another_session_is_mid_turn():
    d = Director()
    d.handle(prompt("a"), now=1.0)
    d.handle(prompt("b"), now=2.0)
    assert d.handle(stop("a"), now=5.0) == ["eureka 1"]

def notification(kind, sid="s1"):
    return {"hook_event_name": "Notification", "session_id": sid, "notification_type": kind}

def test_permission_prompt_plays_attention():
    d = Director()
    d.handle(prompt(), now=1.0)
    assert d.handle(notification("permission_prompt"), now=10.0) == ["attention 2"]

def test_idle_prompt_plays_bored():
    assert Director().handle(notification("idle_prompt"), now=70.0) == ["bored 2"]

def test_other_notifications_are_ignored():
    assert Director().handle(notification("auth_success"), now=1.0) == []

def test_stop_failure_plays_wince_and_ends_the_turn():
    d = Director()
    d.handle(prompt(), now=1.0)
    assert d.handle({"hook_event_name": "StopFailure", "session_id": "s1"}, now=9.0) == ["wince 2", "rest"]

def test_unknown_events_are_ignored():
    assert Director().handle({"hook_event_name": "PreToolUse", "session_id": "s1"}, now=1.0) == []

def test_gesture_during_busy_window_is_dropped():
    d = Director()
    d.handle(prompt("a"), now=1.0); d.handle(prompt("b"), now=1.0)
    assert d.handle(stop("a"), now=5.0) == ["eureka 1"]
    assert d.handle(stop("b"), now=6.0) == ["rest"]      # gesture dropped, mode change kept

def test_gesture_after_busy_window_plays():
    d = Director()
    d.handle(stop("a"), now=5.0)
    assert d.handle(stop("b"), now=15.0) == ["eureka 2", "rest"]

def test_session_end_ends_the_turn_silently():
    d = Director()
    d.handle(prompt(), now=1.0)
    assert d.handle({"hook_event_name": "SessionEnd", "session_id": "s1"}, now=2.0) == ["rest"]

def test_stale_turn_times_out_to_rest():
    d = Director()
    d.handle(prompt(), now=0.0)
    assert d.tick(now=14 * 60) == []
    assert d.tick(now=16 * 60) == ["rest"]
    assert d.tick(now=17 * 60) == []

def test_muted_director_sends_nothing():
    d = Director()
    d.muted = True
    assert d.handle(prompt(), now=1.0) == []
    assert d.handle(stop(), now=5.0) == []
    assert d.tick(now=9999.0) == []

def test_two_stale_turns_time_out_together():
    d = Director()
    d.handle(prompt("a"), now=0.0); d.handle(prompt("b"), now=1.0)
    assert d.tick(now=16 * 60) == ["rest"]
    assert d.turns == {}

def test_mute_mid_turn_ends_turns_and_rests():
    d = Director()
    d.handle(prompt(), now=1.0)
    assert d.mute() == ["rest"]
    assert d.turns == {}
    assert d.handle(stop(), now=5.0) == []

def test_exactly_three_minutes_is_still_normal_tier():
    d = Director()
    d.handle(prompt(), now=0.0)
    assert "eureka 2" in d.handle(stop(), now=180.0)

def test_reconnect_resends_mode():
    d = Director()
    assert d.mode() == "rest"
    d.handle(prompt(), now=1.0)
    assert d.mode() == "thinking"
