"""Event-driven simulation of the common task 1 relay behavior."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Inputs:
    mcb: bool = True
    automatic: bool = False
    pb0: bool = False
    pb1: bool = False
    s1: bool = False
    s2: bool = False


class Conveyor:
    """Exercise the manual sensor sequence and the automatic PLC toggle offline."""

    def __init__(self, start_delay=2.0, stop_delay=0.5):
        if not 1 <= start_delay <= 3 or not 0 <= stop_delay <= 1:
            raise ValueError("Expected t1 within 1–3 s and t2 within 0–1 s")
        self.start_delay = start_delay
        self.stop_delay = stop_delay
        self.reset_motion()
        self.plc = False
        self.previous = Inputs(mcb=False)
        self.last_time = float("-inf")

    def reset_motion(self):
        self.phase = "idle"
        self.direction = 0
        self.deadline = None

    def step(self, now, signals):
        if now < self.last_time:
            raise ValueError("Simulation time must be monotonic")
        self.last_time = now

        if not signals.mcb or not signals.automatic:
            self.plc = False
        elif signals.pb1 and not self.previous.pb1:
            self.plc = not self.plc

        sensors = (signals.s1, signals.s2)
        previous_sensors = (self.previous.s1, self.previous.s2)
        manual = signals.mcb and not signals.automatic
        was_manual = self.previous.mcb and not self.previous.automatic
        if not manual or signals.pb0:
            self.reset_motion()
        elif self.phase == "idle":
            if sensors.count(True) == 1:
                sensor = sensors.index(True)
                if not was_manual or not previous_sensors[sensor]:
                    self.direction = 1 if sensor == 0 else -1
                    self.phase = "starting"
                    self.deadline = now + self.start_delay
        elif self.phase == "starting":
            if now >= self.deadline:
                self.phase = "running"

        if manual and not signals.pb0 and self.phase == "running":
            destination = signals.s2 if self.direction == 1 else signals.s1
            if destination:
                self.phase = "stopping"
                self.deadline = now + self.stop_delay
        if self.phase == "stopping" and now >= self.deadline:
            self.reset_motion()

        running = self.phase in ("running", "stopping")
        self.previous = signals
        return {
            "PLC": self.plc, "WL1": signals.mcb, "WL2": self.plc, "RL": manual,
            "GL": running and self.direction == 1, "YL": running and self.direction == -1,
        }


def demo():
    sim = Conveyor()
    timeline = [
        (0, Inputs(mcb=False)),
        (1, Inputs(automatic=True)),
        (2, Inputs(automatic=True, pb1=True)),
        (3, Inputs(automatic=True)),
        (4, Inputs(automatic=True, pb1=True)),
        (5, Inputs()),
        (6, Inputs(s1=True)),
        (8, Inputs(s1=True)),
        (20, Inputs()),  # The motor keeps running until it sees the destination sensor.
        (21, Inputs(s2=True)),
        (21.5, Inputs(s2=True)),
        (22, Inputs()),
        (23, Inputs(s2=True)),
        (25, Inputs(s2=True)),
        (26, Inputs(s1=True)),
        (26.5, Inputs(s1=True)),
        (27, Inputs()),
        (28, Inputs(s2=True)),
        (30, Inputs(s2=True)),
        (31, Inputs(pb0=True)),
    ]
    results = [{"second": time, **sim.step(time, signals)} for time, signals in timeline]
    expected_forward = {8, 20, 21}
    expected_reverse = {25, 26, 30}
    assert {row["second"] for row in results if row["GL"]} == expected_forward
    assert {row["second"] for row in results if row["YL"]} == expected_reverse
    assert {row["second"] for row in results if row["PLC"]} == {2, 3}
    return {"timeline": results}
