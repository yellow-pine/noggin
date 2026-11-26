"""Hand strength marks (no FEA on the personal license): the servo's stall force at its horn pin and the safety factor a
printed link must keep on it, in its material across its layers (geometry.MATERIALS, #626): SF >= 2 on the brief stall
(#20). The Mech's links are held to it (model/printed/test_gimbal.py)."""

STALL_KGF_CM, HORN_PIN_MM = 1.2, 12.75  # the 9 g servo at 6 V (#20); bar pin radius on the horn
G, MIN_SF = 9.81, 2.0


def stall_force_n():
    return STALL_KGF_CM * G * 10 / HORN_PIN_MM  # kgf.cm -> N.mm over the pin radius
