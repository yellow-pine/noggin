# How it works

Three closer looks behind [the README's overview](../README.md#how-it-works): the Link that carries each command to a
Core, how a Claude Code hook becomes a gesture, and how the model makes every picture. The words are the
[glossary's](../GLOSSARY.md).

## The Link

```mermaid
sequenceDiagram
    accTitle: The Link between the noggin service and one Core
    accDescr: The Core beacons every 2 s so the noggin service learns its address. Each command line goes as one signed UDP datagram; the Core acks it on receipt, before it plays it. A line gets four tries in all with the same seq, waiting 0.2, 0.4, 0.8, 1.6 s for each ack; still unacked, or with no fresh beacon, it goes over USB-C to the eyes Core, and a neck line is dropped.
    participant S as noggin service (Mac)
    participant C as Core (eyes or neck)
    loop every 2 s
        C-)S: beacon: tag, name, ip, uptime (UDP)
    end
    S->>C: tag, seq, line (UDP, HMAC-SHA256 tag)
    C--)S: tagged ack, on receipt
    Note over C: plays the gesture to its end
    opt no ack
        S->>C: the same seq again: four tries in all, waiting 0.2, 0.4, 0.8, 1.6 s for each ack
        S->>C: still unacked, or no fresh beacon: over USB-C to the eyes Core, a neck line dropped
    end
```

Every datagram both ways carries an HMAC tag under the shared token, and the seq never goes back, so a replayed or
forged line is dropped (ADR 0005).

## From a hook to a gesture

```mermaid
---
config:
  layout: dagre
  look: classic
---
stateDiagram-v2
    accTitle: From a Claude Code hook to a gesture
    accDescr: The Mech rests until a prompt starts a turn and it thinks. A Trigger that plays a gesture interrupts rest or thinking; while the gesture plays the noggin service is Busy and drops Triggers. When it ends the Mech thinks if a turn is still open, else rests. The last turn ending with no gesture (SessionEnd, or a Stop while Busy), or a last turn 15 min old returns it to rest.
    [*] --> Rest
    Rest --> Thinking: UserPromptSubmit
    Rest --> Gesture: a gesture's Trigger
    Thinking --> Gesture: a gesture's Trigger
    Gesture --> Thinking: played to its end, a turn still open
    Gesture --> Rest: played to its end, no turn open
    Thinking --> Rest: the last turn ends with no gesture, or is 15 min old
    note right of Gesture
        SessionStart: wink
        Stop: eureka, by the turn's Tier: under 20 s small, under 3 min normal, longer big
        StopFailure: wince
        Notification: attention (permission), bored (idle)
        Busy for 2.5-9 s: Triggers dropped
    end note
```

The noggin service decides (reactions/director.py); the Core plays (ADR 0001).

## The model's pipeline

```mermaid
---
config:
  layout: dagre
  look: classic
---
flowchart TB
    accTitle: The model's pipeline
    accDescr: Our CadQuery parts and hardware Envelopes become MuJoCo models, one per document. MuJoCo writes the sim reports and plays each gesture into Trajectories, from which Blender renders the pictures and the web viewer's GLB per Stage. The parts also export as STL and STEP files.
    P["Parts<br/>CadQuery: printed parts, Envelopes"] -- "meshes, CoACD pieces" --> M["MuJoCo<br/>one MJCF per document"]
    P -- "make stl step" --> F["STL, STEP<br/>to print, to open in CAD"]
    M -- "make sim" --> R["Sim reports<br/>the site's /reports"]
    M -- "make trajectories" --> T["Trajectories<br/>every part, every frame"]
    T --> B["Blender"]
    B -- "make render, make gifs" --> I["Pictures<br/>README and docs"]
    B -- "make web: glTF, a GLB per Stage" --> W["Web viewer<br/>the site's /viewer"]
```

MuJoCo simulates and Blender draws (ADR 0007, ADR 0008); CI builds the reports and the viewer and the site serves them
(ADR 0009).
