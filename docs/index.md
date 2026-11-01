---
hide:
  - navigation
  - toc
---

# noggin

An animatronic Mech on the desk that reacts to Claude Code. It winks when a session starts, drifts while Claude
thinks, lights up when a response lands, scans the room when Claude needs you and gets bored when you walk away.
Claude Code hooks feed a small Mac service, the noggin service, which tells the Mech's two Cores what to play.

<figure>
<img src="https://yellowpine.com/noggin/images/hero.gif" alt="noggin: Stage 3 talking, turning and nodding" width="800" height="400">
<figcaption>Stage 3 talking, turning and nodding</figcaption>
</figure>

[Build one](build/parts.md){ .md-button .md-button--primary }
[Use it](use/noggin-service.md){ .md-button }
[Turn it in 3D](https://yellowpine.com/noggin/viewer/){ .md-button }
{ .center }

## Gestures

<div class="grid gestures">
<figure>
<img src="https://yellowpine.com/noggin/images/eureka.gif" alt="eureka">
<figcaption>eureka</figcaption>
</figure>
<figure>
<img src="https://yellowpine.com/noggin/images/attention.gif" alt="attention">
<figcaption>attention</figcaption>
</figure>
<figure>
<img src="https://yellowpine.com/noggin/images/bored.gif" alt="bored">
<figcaption>bored</figcaption>
</figure>
<figure>
<img src="https://yellowpine.com/noggin/images/wince.gif" alt="wince">
<figcaption>wince</figcaption>
</figure>
<figure>
<img src="https://yellowpine.com/noggin/images/wink.gif" alt="wink">
<figcaption>wink</figcaption>
</figure>
<figure>
<img src="https://yellowpine.com/noggin/images/thinking.gif" alt="thinking">
<figcaption>thinking</figcaption>
</figure>
</div>

## What it does

<!--{{ behaviour }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Which Claude Code event plays which gesture is in [the table on the site](https://yellowpine.com/noggin/#what-it-does),
built from the code.
<!-- #}-->

More in [Gestures and behaviour](use/gestures.md).

## The three Stages

<figure>
<img src="https://yellowpine.com/noggin/images/stages.jpg" alt="The three Stages: stage 1 front (base and eyes), stage 2 side (eyes on the neck), stage 3 side and front (with the mouth)">
<figcaption>Stage 1 front, Stage 2 side, Stage 3 side and front</figcaption>
</figure>

The Mech grows in three Stages, each a complete Mech on the desk.

<div class="grid cards" markdown>

-   **Stage 1: eyes**

    ---

    Two eyeballs with lids on the base plate: four servos on one Core. Built here.

    [Build Stage 1](build/stage-1.md){ .md-button }

-   **Stage 2: neck**

    ---

    The eyes on a pan-and-tilt neck: two more servos on a second Core.

    [Build Stage 2](build/stage-2.md){ .md-button }

-   **Stage 3: mouth**

    ---

    A jaw under the eyes: the seventh servo. The full Mech, as the hero above.

    [Build Stage 3](build/stage-3.md){ .md-button }

</div>

## Where next

<div class="grid cards pairs" markdown>

-   **Build**

    ---

    Parts to buy and print, the three Stages, wiring, flashing the Core and calibrating the servos.

    [Build guide](build/parts.md){ .md-button }

-   **Use**

    ---

    The noggin service, the Claude Code hooks, what each gesture means and how to tune them.

    [Use the Mech](use/noggin-service.md){ .md-button }

-   **Web viewer**

    ---

    Turn each Stage around and play its gestures in the browser.

    [Open the viewer](https://yellowpine.com/noggin/viewer/){ .md-button }

-   **How it works**

    ---

    The Link, a hook's way to a gesture and the model's pipeline, drawn.

    [How it works](how-it-works.md){ .md-button }

</div>
