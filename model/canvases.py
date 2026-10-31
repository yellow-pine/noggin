"""Toggle the reference-photo canvases of the active Fusion document (the Stage builds save them hidden) and print
the new state. Runs INSIDE Fusion: `make model-canvases`."""
import adsk.core, adsk.fusion


def run(_context: str):
    root = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct).rootComponent
    canvases = list(root.canvases) + [c for o in root.allOccurrences for c in o.component.canvases]
    show = not any(c.isLightBulbOn for c in canvases)
    for c in canvases:
        c.isLightBulbOn = show
    print(f"{len(canvases)} canvases {'shown' if show else 'hidden'}")
