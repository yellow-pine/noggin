"""Contact set per sub-assembly (#20): the moving parts plus the bracket and the servos, so dragging a joint in Fusion
stops at contact instead of passing through. Inlined into a build script via `# include: model/contacts.py`
(after fusion_lib) and called before save(); eyes.py: contact_set(design, root, moving | {"eye bracket"} |
{o.name for o in root.occurrences if o.name.endswith("servo")})."""


def contact_set(design, root, names):
    """One contact set over the named root occurrences; contact analysis on, restricted to contact sets."""
    design.isContactAnalysisEnabled = True
    design.isContactSetAnalysis = True
    members = [o for o in root.occurrences if o.name in names]
    if len(members) != len(names):
        raise ValueError(f"contact set: missing {sorted(set(names) - {o.name for o in members})}")
    return design.contactSets.add(members)
