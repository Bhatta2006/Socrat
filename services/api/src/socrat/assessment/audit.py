"""Publication inventory audit; independent content review remains an external gate."""


def coverage_audit(pack):
    cells = []
    for track in pack.tracks:
        for language in pack.languages or [""]:
            forms = [
                x
                for x in pack.assessment_forms
                if x.track == track.id and (not pack.languages or language in x.languages)
            ]
            kinds = {b.kind for b in pack.blueprints if b.id in {x.blueprint_id for x in forms}}
            missing = sorted({"baseline", "weekly", "final", "retention"} - kinds)
            representations = {
                x.retention_representation for x in forms if x.retention_representation
            }
            missing_representations = sorted(
                {"recall", "small_implementation", "mixed_problem", "retention_assessment"}
                - representations
            )
            cells.append(
                dict(
                    track=track.id,
                    language=language,
                    form_count=len(forms),
                    missing_kinds=missing,
                    missing_representations=missing_representations,
                    ready=not missing and not missing_representations,
                )
            )
    return dict(
        schema_version=1,
        ready=bool(cells) and all(x["ready"] for x in cells),
        cells=cells,
        note="Inventory/parallel-structure checks are not human calibration or launch acceptance.",
    )
