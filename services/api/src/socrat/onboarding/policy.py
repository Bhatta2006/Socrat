import hashlib
import json
from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from socrat.skillpacks.schema import Contract, SkillPack

POLICY_VERSION = "1.0.0"
TEMPLATE_VERSION = "1.0.0"
OUTCOMES = {
    "foundations": {"programming_readiness", "foundational_dsa", "interview_entry_readiness"},
    "interview": {"screen_readiness", "interview_loop_readiness", "topic_repair"},
    "competitive": {"rating_band", "division_readiness", "topic_repair", "contest_consistency"},
}


class GoalInput(Contract):
    goal_template_id: Literal["foundations", "interview", "competitive"]
    language: str = Field(min_length=1, max_length=32)
    target_outcome: str = Field(min_length=1, max_length=64)
    target_date: str = Field(min_length=1, max_length=32)
    days_per_week: int = Field(ge=0, le=7)
    minutes_per_session: Literal[10, 20, 30, 45, 60, 90]
    timezone: str = Field(min_length=1, max_length=64)
    language_experience: Literal["none", "syntax_only", "solved_problems", "professional"]
    dsa_experience: Literal["never", "studied", "inconsistent_practice", "comfortable"]
    role_level: Literal["intern", "new_grad", "early_career", "experienced_hire"] | None = None
    platform_or_format: Literal["codeforces", "atcoder", "codechef", "other"] | None = None
    target_value: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Use an IANA timezone") from exc
        return value

    @field_validator("target_date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        if value != "no_fixed_date" and date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use an ISO date or no_fixed_date")
        return value

    @model_validator(mode="after")
    def goal_fields(self):
        if self.target_outcome not in OUTCOMES[self.goal_template_id]:
            raise ValueError("Choose a supported goal outcome")
        if self.goal_template_id == "interview":
            if self.role_level is None or self.platform_or_format or self.target_value:
                raise ValueError("Interview requires a role and no competitive fields")
        elif self.goal_template_id == "competitive":
            if self.platform_or_format is None or self.target_value is None or self.role_level:
                raise ValueError("Competitive requires platform and target value")
        elif self.role_level or self.platform_or_format or self.target_value:
            raise ValueError("Foundations does not use role or competitive fields")
        return self


def digest(value: dict | list) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def matching_pack(goal: GoalInput, packs: list[SkillPack], track: str) -> SkillPack | None:
    for pack in packs:
        if (
            pack.purpose != "launch"
            or pack.domain != "data_structures_and_algorithms"
            or goal.language not in pack.languages
        ):
            continue
        for template in pack.goals:
            if template.id != track:
                continue
            targets = template.released_targets
            matches = track != goal.goal_template_id or any(
                target.outcome == goal.target_outcome
                and target.value == goal.target_value
                and target.role_level == goal.role_level
                and target.platform_or_format == goal.platform_or_format
                for target in targets
            )
            if not matches or not targets:
                continue
            policy = next(item for item in pack.tracks if item.id == template.track_id)
            for concept_id in policy.concept_ids:
                exercises = [item for item in pack.exercises if concept_id in item.concept_ids]
                if not exercises or any(
                    item.modality == "code"
                    and not any(variant.language == goal.language for variant in item.variants)
                    for item in exercises
                ):
                    break
            else:
                return pack
    return None


def route(goal: GoalInput, adult: bool, packs: list[SkillPack], today: date) -> dict:
    """Only explicit released targets route to diagnosis. Self-report never assigns mastery."""
    packs = sorted(packs, key=lambda pack: (pack.key, pack.version))
    coverage = [{"key": p.key, "version": p.version, "digest": p.digest()} for p in packs]
    outcome, reasons, active = "waitlist", [], None
    warnings = []
    pins = []
    target = matching_pack(goal, packs, goal.goal_template_id)
    bridge = goal.goal_template_id != "foundations" and goal.language_experience in {
        "none",
        "syntax_only",
    }
    foundation = matching_pack(goal, packs, "foundations") if bridge else None
    if not adult:
        outcome, reasons = "ineligible", ["adult_confirmation_required"]
    elif goal.language not in {"python", "cpp", "java"}:
        reasons = ["unsupported_language"]
    elif goal.days_per_week < 3 or goal.minutes_per_session < 20:
        outcome, reasons = "ineligible", ["minimum_practice_commitment_not_met"]
    elif target is None:
        reasons = [
            "competitive_target_not_released"
            if goal.goal_template_id == "competitive"
            else "goal_coverage_not_released"
        ]
    elif bridge and foundation is None:
        reasons = ["foundations_bridge_not_released"]
    else:
        active = "foundations" if bridge else goal.goal_template_id
        outcome = (
            "accept_with_foundations_bridge"
            if bridge
            else {
                "foundations": "accept_foundations",
                "interview": "accept_interview_diagnostic",
                "competitive": "accept_competitive_diagnostic",
            }[goal.goal_template_id]
        )
        reasons = [
            "foundation_prerequisites_required"
            if bridge
            else f"{goal.goal_template_id}_goal_selected"
        ]
        pins = [
            {"key": p.key, "version": p.version, "digest": p.digest()}
            for p in [target, foundation]
            if p
        ]
        if goal.target_date != "no_fixed_date":
            remaining = (date.fromisoformat(goal.target_date) - today).days
            required = {}
            for content, track_id in [(target, goal.goal_template_id), (foundation, "foundations")]:
                if content is None:
                    continue
                template = next(t for t in content.goals if t.id == track_id)
                track = next(t for t in content.tracks if t.id == template.track_id)
                required.update(
                    {
                        (content.key, c.id): c.estimated_minutes
                        for c in content.concepts
                        if c.id in track.concept_ids
                    }
                )
            minimum = sum(required.values())
            if (
                remaining <= 0
                or remaining * goal.days_per_week / 7 * goal.minutes_per_session < minimum
            ):
                warnings.append("target_date_feasibility_warning")
    stage = (
        "no_code_trace_and_reasoning"
        if goal.language_experience in {"none", "syntax_only"}
        else "dsa_trace_and_reasoning"
        if goal.dsa_experience in {"never", "studied"}
        else "implementation_diagnostic"
    )
    return {
        "goal": goal.model_dump(),
        "declared_track": goal.goal_template_id,
        "active_track": active,
        "routing_outcome": outcome,
        "reason_codes": reasons,
        "warnings": warnings,
        "first_diagnostic_stage": stage if active else None,
        "policy_version": POLICY_VERSION,
        "template_version": TEMPLATE_VERSION,
        "coverage_version": digest(coverage),
        "coverage_packs": coverage,
        "pack_versions": pins,
        "as_of_date": today.isoformat(),
        "normalized_statement": f"Work toward {goal.target_outcome.replace('_', ' ')}"
        f"{(' for ' + goal.role_level.replace('_', ' ')) if goal.role_level else ''}"
        f"{(' on ' + goal.platform_or_format + ': ' + str(goal.target_value)) if goal.platform_or_format else ''}"
        f" using {goal.language}; {goal.minutes_per_session} minutes on {goal.days_per_week} days each week"
        f" in {goal.timezone}; target: {goal.target_date.replace('_', ' ')}.",
    }
