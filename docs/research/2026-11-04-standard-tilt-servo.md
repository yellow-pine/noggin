# Standard tilt servo at 5 V

The [manufacturer's specification](https://towerpro.com.tw/product/mg996r/)
lists 55 g, 40.7 × 19.7 × 42.9 mm, stall torque 9.4 kgf·cm at 4.8 V
and 11 kgf·cm at 6 V, a 32 cm lead and 1.4 A stall current. The current's
test voltage is unspecified, so the model retains the full 1.4 A on the 5 V rail.
This servo, the thrust bearing and the balance spring are **to order**.

The speed table gives 0.19 s/60° at 4.8 V and 0.15 s/60° at 6 V;
another table on that page says 0.17 at 4.8 V. The model uses the slower 0.19.
Linear interpolation to the regulated 5 V supply is inferred: 9.67 kgf·cm
stall and 0.183 s/60°. Stall torque is not a continuous rating. No continuous
rating is published: the model's one-third-of-stall continuous design limit
(3.22 kgf·cm) is explicitly inferred and remains subject to physical observation.

The rotor/gear armature is unknown. The model scales the unfitted micro-servo
inference by the documented mass ratio; the filmed micro-servo fit is never
applied to the standard servo. Its lead resistance uses the same inferred
26 AWG copper as the other servo leads, with the published 320 mm length.
The actual finished anatomical head and Skin loads must be included before
the spring, torque and stability acceptance for #902 can close.

The manufacturer specifies operating voltage without identifying its measurement
node. The supply report conservatively keeps the 4.8 V minimum after the stock
lead; it does not move that boundary to make a result pass. With the earlier
inferred 24 AWG neck run, simultaneous stalls leave 4.792 V there. The neck run
therefore uses four 22 AWG conductors, still one pack and the same four power
conductors. Resistance is modelled as 0.0535 Ω/m per conductor, consistent with
[Belden's 22 AWG stranded-copper example](https://catalog.belden.com/index.cfm?event=pd&p=PF_6545UE).
Insulation OD 1.6 mm and the 250 mm run remain inferred; the flexing spans keep
the ten-diameter minimum bend radius. This is a wiring design, not a claim of
stock servo lead gauge or a hardware measurement.

The manufacturer's comment describes 159° travel, while a robot variant has
180°. Travel and pulse endpoints remain calibration assumptions: the tilt uses
only ±20° about its fitted centre, within the conservative ±79.5° envelope.
