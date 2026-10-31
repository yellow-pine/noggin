"""Pure decision logic: Triggers (hook events) in, Core commands out. No I/O."""

TIERS = ((20, 1), (180, 2))  # (max seconds, intensity); longer -> 3
NOTIFICATIONS = {"permission_prompt": "attention", "idle_prompt": "bored"}
BUSY_SECONDS = {"eureka": 4.0, "attention": 5.0, "bored": 9.0, "wince": 3.0, "wink": 2.5}
STALE_TURN_SECONDS = 15 * 60


def tier(seconds):
    for limit, intensity in TIERS:
        if seconds <= limit:
            return intensity
    return 3


class Director:
    def __init__(self):
        self.turns = {}  # session_id -> prompt time
        self.busy_until = 0.0
        self.muted = False

    def _gesture(self, name, now):
        if now < self.busy_until:
            return []
        self.busy_until = now + BUSY_SECONDS[name.split()[0]]
        return [name]

    def _end_turn(self, sid):
        self.turns.pop(sid, None)
        return [] if self.turns else ["rest"]

    def handle(self, event, now):
        if self.muted:
            return []
        kind, sid = event.get("hook_event_name"), event.get("session_id")
        if kind == "UserPromptSubmit":
            was_thinking = bool(self.turns)
            self.turns[sid] = now
            return [] if was_thinking else ["thinking"]
        if kind == "Stop":
            started = self.turns.get(sid)
            intensity = tier(now - started) if started is not None else 2
            return self._gesture(f"eureka {intensity}", now) + self._end_turn(sid)
        if kind == "StopFailure":
            return self._gesture("wince 2", now) + self._end_turn(sid)
        if kind == "SessionEnd":
            return self._end_turn(sid) if sid in self.turns else []
        if kind == "Notification" and event.get("notification_type") in NOTIFICATIONS:
            return self._gesture(NOTIFICATIONS[event["notification_type"]] + " 2", now)
        return []

    def tick(self, now):
        if self.muted:
            return []
        stale = [sid for sid, t in self.turns.items() if now - t > STALE_TURN_SECONDS]
        for sid in stale:
            self.turns.pop(sid)
        return ["rest"] if stale and not self.turns else []

    def mode(self):
        """What the Core should be in right now; resent when the Link comes back."""
        return "thinking" if self.turns else "rest"

    def mute(self):
        """Drop every Trigger from now on; forget open turns so the Core can rest."""
        self.muted = True
        self.turns.clear()
        return ["rest"]
