from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI
from fpg_core import BuildableSpaceConfig, FpgCoreConfig, validate_fpg_core_config
from fpg_core.candidate_scoring.config import EvaluatorRule as CandidateRule
from fpg_core.candidate_scoring.config import ScoringConfig as CandidateConfig
from fpg_core.candidate_scoring.types import EvaluatorCategory, EvaluatorKey
from fpg_core.candidate_search.config import CandidateSearchConfig
from fpg_core.floor_plan_openings.config import (
    DimensionConfig,
    FeaturePolicy,
    GeometryConfig,
    ObjectiveConfig,
)
from fpg_core.floor_plan_openings.config import (
    SolverConfig as OpeningSolverConfig,
)
from fpg_core.floor_plan_openings.profiles import OpeningGenerationProfile
from fpg_core.floor_plan_post_processing.config import (
    GridSnapConfig,
    HallwayMergeConfig,
    PlaceholderRemovalConfig,
    RectilinearSimplificationConfig,
    VerandaAdjustmentConfig,
    WallExtensionConfig,
    WallExtensionRule,
)
from fpg_core.floor_plan_post_processing.contracts import (
    NumericPolicy,
    PostProcessingProfile,
    ProcessorUse,
)
from fpg_core.floor_plan_preprocessing import (
    AspectRatioRule,
    ExcessAttachedBathroomPolicy,
    PreprocessingConfig,
    RoomCountRule,
    RoomRelationReference,
    RoomSizeReference,
    RoomSizeSelectionStrategy,
)
from fpg_core.floor_plan_scoring.config import (
    EvaluatorRule as FloorScoringRule,
)
from fpg_core.floor_plan_scoring.config import (
    ScoringGroupRule,
    ScoringProfile,
)
from fpg_core.floor_plan_scoring.evaluators import (
    BedroomQualitySettings,
    EnclosedVoidsSettings,
    GeometryIntegritySettings,
    InwardRecessSettings,
    KitchenDiningSettings,
    LivingRoomBalanceSettings,
    RequiredAdjacencySettings,
)
from fpg_core.floor_plan_scoring.types import EvaluatorKey as FloorEvaluatorKey
from fpg_core.floor_plan_scoring.types import GroupKey
from fpg_core.floor_plan_solver.config import (
    PreparationConfig,
    SeedPolicy,
    SeedSource,
    SolverConfig,
)
from fpg_core.floor_plan_solver.profiles import (
    GenerationProfile,
    HardConstraintUse,
    ProfileCatalog,
    SoftConstraintUse,
)
from fpg_core.types import ConstraintStrength, MatchPolicy, RoomType
from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

from app.pipeline.buildable_space.reference_data import (
    REFERENCE_DATA_PATH as BUILDABLE_CONFIG_PATH,
)
from app.pipeline.buildable_space.reference_data import (
    load_buildable_space_reference_data,
)

GENERATION_CONFIG_PATH = (
    Path(__file__).with_name("data") / "generation_reference_data.json"
)


class CoreConfigLoadError(RuntimeError):
    pass


class _GenerationDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: StrictInt
    preprocessing: dict[str, Any]
    candidate_search: dict[str, Any]
    candidate_scoring: dict[str, Any]
    floor_plan_solver: dict[str, Any]
    post_processing: dict[str, Any]
    openings: dict[str, Any]
    floor_plan_scoring: dict[str, Any]


def _exact(
    raw: Mapping[str, Any], required: set[str], optional: set[str] = set()
) -> None:
    missing = required.difference(raw)
    extra = set(raw).difference(required | optional)
    if missing or extra:
        raise CoreConfigLoadError(
            f"configuration keys differ; missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _room(value: str) -> RoomType:
    return RoomType(value)


def _deep_setting(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_deep_setting(item) for item in value)
    if isinstance(value, dict):
        return {
            (_room(key) if key in {item.value for item in RoomType} else key): (
                _deep_setting(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, str) and value in {item.value for item in RoomType}:
        return _room(value)
    return value


def _preprocessing(raw: dict[str, Any]) -> PreprocessingConfig:
    _exact(
        raw,
        {
            "room_count_rules",
            "supported_aspect_ratios",
            "room_sizes",
            "room_relations",
            "mandatory_room_types",
            "floor_area_buffer",
            "hallway_area_buffer",
            "hallway_count",
            "hallway_min_width",
            "default_room_size",
            "min_aspect_ratio",
            "max_aspect_ratio",
            "room_size_strategy",
            "size_normalization_exclusions",
            "excess_attached_bathrooms",
        },
    )
    return PreprocessingConfig(
        room_count_rules=tuple(
            RoomCountRule(
                room_type=_room(item["room_type"]),
                minimum=item["minimum"],
                maximum=item["maximum"],
                client_selectable=item.get("client_selectable", True),
            )
            for item in raw["room_count_rules"]
        ),
        supported_aspect_ratios=tuple(
            AspectRatioRule(**item) for item in raw["supported_aspect_ratios"]
        ),
        room_sizes=tuple(
            RoomSizeReference(**{**item, "room_type": _room(item["room_type"])})
            for item in raw["room_sizes"]
        ),
        room_relations=tuple(
            RoomRelationReference(
                source_room_type=_room(item["source_room_type"]),
                target_room_types=tuple(
                    _room(value) for value in item["target_room_types"]
                ),
                match_policy=MatchPolicy(item["match_policy"]),
                strength=ConstraintStrength(item["strength"]),
                required=item["required"],
            )
            for item in raw["room_relations"]
        ),
        mandatory_room_types=tuple(
            _room(value) for value in raw["mandatory_room_types"]
        ),
        floor_area_buffer=raw["floor_area_buffer"],
        hallway_area_buffer=raw["hallway_area_buffer"],
        hallway_count=raw["hallway_count"],
        hallway_min_width=raw["hallway_min_width"],
        default_room_size=raw["default_room_size"],
        min_aspect_ratio=raw["min_aspect_ratio"],
        max_aspect_ratio=raw["max_aspect_ratio"],
        room_size_strategy=RoomSizeSelectionStrategy(raw["room_size_strategy"]),
        size_normalization_exclusions=tuple(
            _room(value) for value in raw["size_normalization_exclusions"]
        ),
        excess_attached_bathrooms=ExcessAttachedBathroomPolicy(
            raw["excess_attached_bathrooms"]
        ),
    )


def _candidate_scoring(raw: dict[str, Any]) -> CandidateConfig:
    _exact(
        raw,
        {
            "evaluator_rules",
            "fail_fast_on_critical_failure",
            "not_applicable_quality_contributes",
            "raise_on_evaluator_error",
        },
    )
    for item in raw["evaluator_rules"]:
        _exact(
            item,
            {
                "key",
                "category",
                "enabled",
                "order",
                "weight",
                "minimum_score",
                "settings",
            },
        )
    return CandidateConfig(
        evaluator_rules=tuple(
            CandidateRule(
                key=EvaluatorKey(item["key"]),
                category=EvaluatorCategory(item["category"]),
                enabled=item["enabled"],
                order=item["order"],
                weight=item["weight"],
                minimum_score=item["minimum_score"],
                settings=_deep_setting(item["settings"]),
            )
            for item in raw["evaluator_rules"]
        ),
        fail_fast_on_critical_failure=raw["fail_fast_on_critical_failure"],
        not_applicable_quality_contributes=raw["not_applicable_quality_contributes"],
        raise_on_evaluator_error=raw["raise_on_evaluator_error"],
    )


def _solver_profiles(raw: dict[str, Any]) -> ProfileCatalog:
    _exact(raw, {"hard_constraints", "profiles"})
    for item in raw["hard_constraints"]:
        _exact(item, {"key", "settings"})
    hard = tuple(
        HardConstraintUse(item["key"], _deep_setting(item["settings"]))
        for item in raw["hard_constraints"]
    )
    profiles: dict[str, GenerationProfile] = {}
    for item in raw["profiles"]:
        _exact(
            item,
            {
                "slot",
                "name",
                "soft_constraints",
                "solver",
                "preparation",
                "seed",
            },
        )
        for value in item["soft_constraints"]:
            _exact(value, {"key", "weight", "settings"})
        profiles[item["slot"]] = GenerationProfile(
            name=item["name"],
            hard_constraints=hard,
            soft_constraints=tuple(
                SoftConstraintUse(
                    value["key"], value["weight"], _deep_setting(value["settings"])
                )
                for value in item["soft_constraints"]
            ),
            solver=SolverConfig(**item["solver"]),
            preparation=PreparationConfig(**item["preparation"]),
            seed=SeedPolicy(
                **{**item["seed"], "source": SeedSource(item["seed"]["source"])}
            ),
        )
    if set(profiles) != {"initial", "refinement_a", "refinement_b"}:
        raise CoreConfigLoadError("solver profiles must define the three catalog slots")
    return ProfileCatalog(**profiles)


def _post_processing(raw: dict[str, Any]) -> PostProcessingProfile:
    _exact(raw, {"name", "processors", "numeric", "reject_existing_openings"})
    config_types = {
        "veranda_adjustment": lambda value: VerandaAdjustmentConfig(**value),
        "wall_extension": lambda value: WallExtensionConfig(
            rules=tuple(
                WallExtensionRule(**{**rule, "room_type": _room(rule["room_type"])})
                for rule in value["rules"]
            ),
            transformation_version=value["transformation_version"],
        ),
        "remove_placeholder_rooms": lambda value: PlaceholderRemovalConfig(),
        "hallway_merge": lambda value: HallwayMergeConfig(**value),
        "grid_snap": lambda value: GridSnapConfig(**value),
        "rectilinear_simplification": lambda value: RectilinearSimplificationConfig(),
    }
    for item in raw["processors"]:
        _exact(
            item,
            {"processor_id", "config"},
            {"required", "validate_after"},
        )
    return PostProcessingProfile(
        name=raw["name"],
        processors=tuple(
            ProcessorUse(
                processor_id=item["processor_id"],
                config=config_types[item["processor_id"]](item["config"]),
                required=item.get("required", False),
                validate_after=item.get("validate_after", False),
            )
            for item in raw["processors"]
        ),
        numeric=NumericPolicy(**raw["numeric"]),
        reject_existing_openings=raw["reject_existing_openings"],
    )


def _openings(raw: dict[str, Any]) -> OpeningGenerationProfile:
    _exact(
        raw,
        {
            "name",
            "enabled_features",
            "enabled_constraints",
            "geometry",
            "dimensions",
            "policy",
            "objective",
            "solver",
        },
    )
    policy = raw["policy"]
    return OpeningGenerationProfile(
        name=raw["name"],
        enabled_features=tuple(raw["enabled_features"]),
        enabled_constraints=tuple(raw["enabled_constraints"]),
        geometry=GeometryConfig(**raw["geometry"]),
        dimensions=DimensionConfig(**raw["dimensions"]),
        policy=FeaturePolicy(
            allowed_room_pairs=tuple(
                (_room(left), _room(right))
                for left, right in policy["allowed_room_pairs"]
            ),
            room_door_caps=tuple(
                (_room(room_type), cap) for room_type, cap in policy["room_door_caps"]
            ),
            secondary_room_priority=tuple(
                _room(value) for value in policy["secondary_room_priority"]
            ),
            window_room_types=tuple(
                _room(value) for value in policy["window_room_types"]
            ),
            main_side_priority=tuple(policy["main_side_priority"]),
            secondary_side_priority=tuple(policy["secondary_side_priority"]),
            window_side_priority=tuple(policy["window_side_priority"]),
        ),
        objective=ObjectiveConfig(**raw["objective"]),
        solver=OpeningSolverConfig(**raw["solver"]),
    )


def _floor_scoring(raw: dict[str, Any]) -> ScoringProfile:
    _exact(raw, {"groups", "evaluators"})
    for item in raw["groups"]:
        _exact(item, {"key", "enabled", "order", "weight"})
    for item in raw["evaluators"]:
        _exact(
            item,
            {
                "key",
                "group_key",
                "settings",
                "enabled",
                "order",
                "weight",
                "minimum_score",
            },
        )
    settings_types = {
        "geometry_integrity": GeometryIntegritySettings,
        "required_adjacency": RequiredAdjacencySettings,
        "enclosed_voids": EnclosedVoidsSettings,
        "inward_recess": InwardRecessSettings,
        "living_room_balance": LivingRoomBalanceSettings,
        "bedroom_quality": BedroomQualitySettings,
        "kitchen_dining_proximity": KitchenDiningSettings,
    }
    return ScoringProfile(
        groups=tuple(
            ScoringGroupRule(
                key=GroupKey(item["key"]),
                enabled=item["enabled"],
                order=item["order"],
                weight=item["weight"],
            )
            for item in raw["groups"]
        ),
        evaluators=tuple(
            FloorScoringRule(
                key=FloorEvaluatorKey(item["key"]),
                group_key=GroupKey(item["group_key"]),
                settings=settings_types[item["key"]](**item["settings"]),
                enabled=item["enabled"],
                order=item["order"],
                weight=item["weight"],
                minimum_score=item["minimum_score"],
            )
            for item in raw["evaluators"]
        ),
    )


def load_fpg_core_config(
    generation_path: Path = GENERATION_CONFIG_PATH,
    buildable_path: Path = BUILDABLE_CONFIG_PATH,
) -> FpgCoreConfig:
    try:
        document = _GenerationDocument.model_validate_json(
            generation_path.read_text(encoding="utf-8")
        )
        buildable = load_buildable_space_reference_data(buildable_path)
        if document.schema_version != buildable.schema_version:
            raise CoreConfigLoadError("configuration schema versions do not match")
        config = FpgCoreConfig(
            schema_version=document.schema_version,
            project_units_per_meter=buildable.project_units_per_meter,
            buildable_space=BuildableSpaceConfig(
                active_profile=buildable.active_profile,
                usable_land_constraints=buildable.usable_land_constraints,
                validation_limits=buildable.validation_limits,
            ),
            preprocessing=_preprocessing(document.preprocessing),
            candidate_search=CandidateSearchConfig(**document.candidate_search),
            candidate_scoring=_candidate_scoring(document.candidate_scoring),
            floor_plan_solver=_solver_profiles(document.floor_plan_solver),
            post_processing=_post_processing(document.post_processing),
            openings=_openings(document.openings),
            floor_plan_scoring=_floor_scoring(document.floor_plan_scoring),
        )
        validate_fpg_core_config(config)
        return config
    except (
        OSError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        if isinstance(exc, CoreConfigLoadError):
            raise
        raise CoreConfigLoadError(
            f"could not load FPG core configuration: {exc}"
        ) from exc


def get_fpg_core_config(app: FastAPI) -> FpgCoreConfig:
    config = getattr(app.state, "fpg_core_config", None)
    if not isinstance(config, FpgCoreConfig):
        raise CoreConfigLoadError("FPG core configuration is not initialized")
    return config


def reload_fpg_core_config(
    app: FastAPI,
    generation_path: Path = GENERATION_CONFIG_PATH,
    buildable_path: Path = BUILDABLE_CONFIG_PATH,
) -> FpgCoreConfig:
    replacement = load_fpg_core_config(generation_path, buildable_path)
    app.state.fpg_core_config = replacement
    return replacement


@asynccontextmanager
async def fpg_core_lifespan(app: FastAPI):
    reload_fpg_core_config(app)
    yield
