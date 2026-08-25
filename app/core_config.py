from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, AsyncIterator, Mapping

from fastapi import FastAPI
from fpg_core import BuildableSpaceConfig, FpgCoreConfig, validate_fpg_core_config
from fpg_core.candidate_circulation import (
    CandidateCirculationConfig,
    HallwayConsolidationConfig,
    RoutingCostProfile,
)
from fpg_core.candidate_scoring import (
    RELATIONSHIP_QUALITY_KEY,
    EvaluatorCategory,
    EvaluatorKey,
    EvaluatorRule as CandidateRule,
    RelationshipQualityConfig,
    ScoringConfig as CandidateConfig,
    create_default_config as create_default_candidate_scoring_config,
)
from fpg_core.candidate_search import CandidateSearchConfig
from fpg_core.domain import (
    CirculationRouteRule,
    CirculationTrafficClass,
    ConstraintStrength,
    DestinationSelection,
    GridRoutingCostProfile,
    LandSide,
    MatchPolicy,
    RoadType,
    RoomType,
    SetbackCalculationMode,
    SetbackProfile,
    UsableLandConstraints,
    ValidationLimits,
)
from fpg_core.floor_plan_openings import (
    DimensionConfig,
    FeaturePolicy,
    FloorPlanOpeningsConfig,
    GeometryConfig,
    ObjectiveConfig,
    SolverConfig as OpeningSolverConfig,
)
from fpg_core.floor_plan_post_processing import (
    FloorPlanPostProcessingConfig,
    GridSnapConfig,
    HallwayMergeConfig,
    NumericPolicy,
    PlaceholderRemovalConfig,
    ProcessorUse,
    RectilinearSimplificationConfig,
    VerandaAdjustmentConfig,
    WallExtensionConfig,
    WallExtensionRule,
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
from fpg_core.floor_plan_scoring import (
    EnclosedVoidsSettings,
    EvaluatorKey as FloorEvaluatorKey,
    EvaluatorRule as FloorScoringRule,
    FloorPlanScoringConfig,
    GeometryIntegritySettings,
    GroupKey,
    InwardRecessSettings,
    KitchenDiningSettings,
    RequiredAdjacencySettings,
    RoomAreaAggregation,
    RoomSizeConsistencySettings,
    RoomSizeRelationRule,
    RoomTypeConsistencyRule,
    ScoringGroupRule,
)
from fpg_core.floor_plan_solver import (
    FloorPlanSolverConfig,
    HardConstraintUse,
    PreparationConfig,
    ProfileCatalog,
    SeedPolicy,
    SeedSource,
    SoftConstraintUse,
    SolverConfig,
)
from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

SERVER_CONFIG_PATH = Path(
    os.environ.get(
        "FPG_SERVER_CONFIG_PATH",
        str(Path(__file__).with_name("data") / "server_config.json"),
    )
)


class CoreConfigLoadError(RuntimeError):
    pass


class _ServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    api_prefix: str
    cors_origins: tuple[str, ...]
    output_root: Path
    log_level: str
    max_concurrent_jobs: StrictInt
    max_queued_jobs: StrictInt
    job_retention_seconds: StrictInt
    request_timeout_seconds: float
    cancellation_grace_seconds: float
    sse_heartbeat_seconds: float


class _UnitsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_units_per_meter: StrictInt
    front_axis: str


class _GenerationRuntimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_score_threshold: float
    usable_floor_plan_score: float
    presentable_floor_plan_score: float
    solver_runs_per_candidate: StrictInt
    require_final_critical_pass: bool


class _GenerationDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: StrictInt
    server: _ServerSettings
    units: _UnitsSettings
    buildable_space: dict[str, Any]
    generation_runtime: _GenerationRuntimeSettings
    preprocessing: dict[str, Any]
    candidate_search: dict[str, Any]
    candidate_circulation: dict[str, Any]
    candidate_scoring: dict[str, Any]
    floor_plan_solver: dict[str, Any]
    post_processing: dict[str, Any]
    openings: dict[str, Any]
    floor_plan_scoring: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FloorSizeProfile:
    name: str
    max_floor_area: int | None
    circulation_ratio: float
    max_hallway_room_count: int


@dataclass(frozen=True, slots=True)
class ResolvedFloorSizeProfile:
    name: str
    floor_area: int
    circulation_ratio: float
    circulation_allowance_area: float
    max_hallway_room_count: int


@dataclass(frozen=True, slots=True)
class FloorSizePolicy:
    minimum_circulation_area: float
    profiles: tuple[FloorSizeProfile, ...]

    def resolve(self, floor_area: int) -> ResolvedFloorSizeProfile:
        if floor_area <= 0:
            raise ValueError("floor_area must be positive")
        for profile in self.profiles:
            if profile.max_floor_area is None or floor_area <= profile.max_floor_area:
                percentage_area = (
                    Decimal(floor_area)
                    * Decimal(str(profile.circulation_ratio))
                ).to_integral_value(rounding=ROUND_CEILING)
                circulation_area = max(
                    self.minimum_circulation_area,
                    float(percentage_area),
                )
                return ResolvedFloorSizeProfile(
                    name=profile.name,
                    floor_area=floor_area,
                    circulation_ratio=profile.circulation_ratio,
                    circulation_allowance_area=circulation_area,
                    max_hallway_room_count=profile.max_hallway_room_count,
                )
        raise CoreConfigLoadError(
            f"No floor-size profile covers floor area {floor_area}."
        )


@dataclass(frozen=True, slots=True)
class ServerConfig:
    server: _ServerSettings
    generation: _GenerationRuntimeSettings
    core: FpgCoreConfig
    candidate_circulation: CandidateCirculationConfig
    floor_size_policy: FloorSizePolicy

    def preprocessing_for_floor_limits(
        self, max_width: int, max_length: int
    ) -> tuple[PreprocessingConfig, ResolvedFloorSizeProfile]:
        floor_area = max_width * max_length
        profile = self.floor_size_policy.resolve(floor_area)
        preprocessing = replace(
            self.core.preprocessing,
            hallway_area_buffer=profile.circulation_allowance_area,
            max_hallway_room_count=profile.max_hallway_room_count,
        )
        return preprocessing, profile

    def circulation_for(
        self, room_types: set[RoomType]
    ) -> CandidateCirculationConfig:
        rules = tuple(
            rule
            for rule in self.candidate_circulation.route_rules
            if rule.source_room_type in room_types
            and rule.destination_room_type in room_types
        )
        if not rules:
            raise CoreConfigLoadError(
                "No candidate-circulation routes apply to the requested rooms."
            )
        return replace(self.candidate_circulation, route_rules=rules)

    def candidate_scoring_for(
        self, circulation: CandidateCirculationConfig
    ) -> CandidateConfig:
        relationship = RelationshipQualityConfig(
            costs=GridRoutingCostProfile(
                empty_node_cost=circulation.costs.empty_node_cost,
                traversable_hint_node_cost=(
                    circulation.costs.traversable_hint_node_cost
                ),
                turn_cost=circulation.costs.turn_cost,
                perimeter_bias_max_cost=(
                    circulation.costs.perimeter_bias_max_cost
                ),
            ),
            route_rules=circulation.route_rules,
            always_traversable_room_types=(RoomType.HALLWAY,),
        )
        rules = tuple(
            replace(rule, settings={"routing_config": relationship})
            if rule.key == RELATIONSHIP_QUALITY_KEY
            else rule
            for rule in self.core.candidate_scoring.evaluator_rules
        )
        return replace(self.core.candidate_scoring, evaluator_rules=rules)


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


def _floor_size_policy(raw: Mapping[str, Any]) -> FloorSizePolicy:
    minimum_area = raw["minimum_circulation_area"]
    if not isinstance(minimum_area, (int, float)) or isinstance(minimum_area, bool):
        raise CoreConfigLoadError("minimum_circulation_area must be numeric.")
    if minimum_area <= 0:
        raise CoreConfigLoadError("minimum_circulation_area must be positive.")

    raw_profiles = raw["floor_size_profiles"]
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raise CoreConfigLoadError("floor_size_profiles must be a non-empty list.")

    profiles: list[FloorSizeProfile] = []
    seen_names: set[str] = set()
    previous_max_area = 0
    for index, item in enumerate(raw_profiles):
        if not isinstance(item, dict):
            raise CoreConfigLoadError("Each floor_size_profiles item must be an object.")
        _exact(
            item,
            {
                "name",
                "max_floor_area",
                "circulation_ratio",
                "max_hallway_room_count",
            },
        )
        name = item["name"]
        max_area = item["max_floor_area"]
        ratio = item["circulation_ratio"]
        hallway_count = item["max_hallway_room_count"]

        if not isinstance(name, str) or not name.strip():
            raise CoreConfigLoadError("Floor-size profile names must be non-empty strings.")
        if name in seen_names:
            raise CoreConfigLoadError(f"Duplicate floor-size profile name: {name}")
        seen_names.add(name)

        if max_area is None:
            if index != len(raw_profiles) - 1:
                raise CoreConfigLoadError(
                    "Only the final floor-size profile may have max_floor_area=null."
                )
        else:
            if not isinstance(max_area, int) or isinstance(max_area, bool) or max_area <= 0:
                raise CoreConfigLoadError(
                    "floor_size_profiles.max_floor_area must be a positive integer or null."
                )
            if max_area <= previous_max_area:
                raise CoreConfigLoadError(
                    "floor_size_profiles max_floor_area values must increase."
                )
            previous_max_area = max_area

        if not isinstance(ratio, (int, float)) or isinstance(ratio, bool):
            raise CoreConfigLoadError(
                "floor_size_profiles.circulation_ratio must be numeric."
            )
        if not 0 < float(ratio) <= 1:
            raise CoreConfigLoadError(
                "floor_size_profiles.circulation_ratio must be in (0, 1]."
            )
        if (
            not isinstance(hallway_count, int)
            or isinstance(hallway_count, bool)
            or hallway_count < 1
        ):
            raise CoreConfigLoadError(
                "floor_size_profiles.max_hallway_room_count must be a positive integer."
            )

        profiles.append(
            FloorSizeProfile(
                name=name,
                max_floor_area=max_area,
                circulation_ratio=float(ratio),
                max_hallway_room_count=hallway_count,
            )
        )

    if profiles[-1].max_floor_area is not None:
        raise CoreConfigLoadError(
            "The final floor-size profile must have max_floor_area=null to cover larger floors."
        )

    return FloorSizePolicy(
        minimum_circulation_area=float(minimum_area),
        profiles=tuple(profiles),
    )


def _preprocessing(
    raw: dict[str, Any], floor_size_policy: FloorSizePolicy
) -> PreprocessingConfig:
    _exact(
        raw,
        {
            "room_count_rules",
            "supported_aspect_ratios",
            "room_sizes",
            "room_relations",
            "mandatory_room_types",
            "floor_area_buffer",
            "minimum_circulation_area",
            "floor_size_profiles",
            "hallway_min_width",
            "candidate_search_grid_spacing",
            "max_aspect_residual_units",
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
        hallway_area_buffer=floor_size_policy.minimum_circulation_area,
        max_hallway_room_count=max(
            profile.max_hallway_room_count for profile in floor_size_policy.profiles
        ),
        hallway_min_width=raw["hallway_min_width"],
        candidate_search_grid_spacing=raw["candidate_search_grid_spacing"],
        max_aspect_residual_units=raw["max_aspect_residual_units"],
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
    defaults = {
        rule.key: rule for rule in create_default_candidate_scoring_config().evaluator_rules
    }
    configured: list[CandidateRule] = []
    for item in raw["evaluator_rules"]:
        key = EvaluatorKey(item["key"])
        default = defaults.get(key)
        if default is None:
            raise CoreConfigLoadError(f"Unknown candidate evaluator: {key}")
        configured.append(
            replace(
                default,
                category=EvaluatorCategory(item["category"]),
                enabled=item["enabled"],
                order=item["order"],
                weight=item["weight"],
                minimum_score=item["minimum_score"],
            )
        )
    return CandidateConfig(
        evaluator_rules=tuple(configured),
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
    profiles: dict[str, FloorPlanSolverConfig] = {}
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
        profiles[item["slot"]] = FloorPlanSolverConfig(
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


def _post_processing(raw: dict[str, Any]) -> FloorPlanPostProcessingConfig:
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
    return FloorPlanPostProcessingConfig(
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


def _openings(raw: dict[str, Any]) -> FloorPlanOpeningsConfig:
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
    _exact(
        policy,
        {
            "allowed_room_pairs",
            "room_door_caps",
            "secondary_room_priority",
            "window_room_types",
            "main_side_priority",
            "secondary_side_priority",
            "window_side_priority",
            "required_access_room_types",
            "door_placement_priority",
        },
    )
    return FloorPlanOpeningsConfig(
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
            required_access_room_types=tuple(
                _room(value) for value in policy["required_access_room_types"]
            ),
            door_placement_priority=tuple(
                (_room(room_type), priority)
                for room_type, priority in policy["door_placement_priority"]
            ),
        ),
        objective=ObjectiveConfig(**raw["objective"]),
        solver=OpeningSolverConfig(**raw["solver"]),
    )


def _room_size_consistency_settings(
    raw: dict[str, Any],
) -> RoomSizeConsistencySettings:
    _exact(
        raw,
        {
            "relation_rules",
            "consistency_rules",
            "default_full_penalty_ratio_delta",
        },
    )
    relation_rules: list[RoomSizeRelationRule] = []
    for item in raw["relation_rules"]:
        _exact(
            item,
            {
                "reference_type",
                "compared_type",
                "min_ratio",
                "max_ratio",
                "reference_aggregation",
                "compared_aggregation",
                "weight",
                "full_penalty_ratio_delta",
            },
        )
        relation_rules.append(
            RoomSizeRelationRule(
                reference_type=_room(item["reference_type"]),
                compared_type=_room(item["compared_type"]),
                min_ratio=item["min_ratio"],
                max_ratio=item["max_ratio"],
                reference_aggregation=RoomAreaAggregation(
                    item["reference_aggregation"]
                ),
                compared_aggregation=RoomAreaAggregation(
                    item["compared_aggregation"]
                ),
                weight=item["weight"],
                full_penalty_ratio_delta=item["full_penalty_ratio_delta"],
            )
        )

    consistency_rules: list[RoomTypeConsistencyRule] = []
    for item in raw["consistency_rules"]:
        _exact(
            item,
            {
                "room_type",
                "maximum_spread_ratio",
                "weight",
                "full_penalty_ratio_delta",
            },
        )
        consistency_rules.append(
            RoomTypeConsistencyRule(
                room_type=_room(item["room_type"]),
                maximum_spread_ratio=item["maximum_spread_ratio"],
                weight=item["weight"],
                full_penalty_ratio_delta=item["full_penalty_ratio_delta"],
            )
        )

    return RoomSizeConsistencySettings(
        relation_rules=tuple(relation_rules),
        consistency_rules=tuple(consistency_rules),
        default_full_penalty_ratio_delta=raw[
            "default_full_penalty_ratio_delta"
        ],
    )


def _floor_scoring(raw: dict[str, Any]) -> FloorPlanScoringConfig:
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
    settings_builders = {
        "geometry_integrity": lambda settings: GeometryIntegritySettings(**settings),
        "required_adjacency": lambda settings: RequiredAdjacencySettings(**settings),
        "enclosed_voids": lambda settings: EnclosedVoidsSettings(**settings),
        "inward_recess": lambda settings: InwardRecessSettings(**settings),
        "room_size_consistency": _room_size_consistency_settings,
        "kitchen_dining_proximity": lambda settings: KitchenDiningSettings(
            **settings
        ),
    }
    unknown_evaluators = {
        item["key"] for item in raw["evaluators"]
    }.difference(settings_builders)
    if unknown_evaluators:
        raise CoreConfigLoadError(
            "Unknown floor-plan scoring evaluators: "
            f"{sorted(unknown_evaluators)}"
        )
    return FloorPlanScoringConfig(
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
                settings=settings_builders[item["key"]](item["settings"]),
                enabled=item["enabled"],
                order=item["order"],
                weight=item["weight"],
                minimum_score=item["minimum_score"],
            )
            for item in raw["evaluators"]
        ),
    )


def _buildable_space(raw: dict[str, Any]) -> BuildableSpaceConfig:
    _exact(
        raw,
        {
            "active_profile",
            "setback_profiles",
            "usable_land_constraints",
            "validation_limits",
        },
    )
    active_name = raw["active_profile"]
    profile_raw = raw["setback_profiles"][active_name]
    base = {
        LandSide(key): int(value)
        for key, value in profile_raw["base_setbacks"].items()
    }
    adjustments = {
        RoadType(road): {
            LandSide(side): int(value) for side, value in values.items()
        }
        for road, values in profile_raw["road_adjustments"].items()
    }
    return BuildableSpaceConfig(
        active_profile=SetbackProfile(
            name=active_name,
            status=profile_raw["status"],
            description=profile_raw["description"],
            calculation_mode=SetbackCalculationMode(
                profile_raw["calculation_mode"]
            ),
            base_setbacks=MappingProxyType(base),
            road_adjustments=MappingProxyType(
                {
                    key: MappingProxyType(value)
                    for key, value in adjustments.items()
                }
            ),
        ),
        usable_land_constraints=UsableLandConstraints(
            **raw["usable_land_constraints"]
        ),
        validation_limits=ValidationLimits(**raw["validation_limits"]),
    )


def _candidate_circulation(raw: dict[str, Any]) -> CandidateCirculationConfig:
    _exact(
        raw,
        {
            "costs",
            "max_routing_passes",
            "always_traversable_room_types",
            "hallway_consolidation",
            "route_rules",
        },
    )
    costs = raw["costs"]
    _exact(
        costs,
        {
            "empty_node_cost",
            "traversable_hint_node_cost",
            "turn_cost",
            "perimeter_bias_max_cost",
            "traffic_conflict_cost",
        },
    )
    for item in raw["route_rules"]:
        _exact(
            item,
            {
                "id",
                "name",
                "source_room_type",
                "destination_room_type",
                "destination_selection",
                "traffic_class",
                "allowed_transit_room_types",
                "required_transit_room_types",
                "importance_weight",
            },
        )
    rules = tuple(
        CirculationRouteRule(
            id=item["id"],
            name=item["name"],
            source_room_type=RoomType(item["source_room_type"]),
            destination_room_type=RoomType(item["destination_room_type"]),
            destination_selection=DestinationSelection(
                item["destination_selection"]
            ),
            traffic_class=CirculationTrafficClass(item["traffic_class"]),
            allowed_transit_room_types=tuple(
                RoomType(value) for value in item["allowed_transit_room_types"]
            ),
            importance_weight=item["importance_weight"],
            required_transit_room_types=tuple(
                RoomType(value) for value in item["required_transit_room_types"]
            ),
        )
        for item in raw["route_rules"]
    )
    return CandidateCirculationConfig(
        costs=RoutingCostProfile(**costs),
        route_rules=rules,
        always_traversable_room_types=tuple(
            RoomType(value) for value in raw["always_traversable_room_types"]
        ),
        max_routing_passes=raw["max_routing_passes"],
        hallway_consolidation=HallwayConsolidationConfig(
            **raw["hallway_consolidation"]
        ),
    )


def load_server_config(path: Path = SERVER_CONFIG_PATH) -> ServerConfig:
    try:
        document = _GenerationDocument.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        if document.schema_version != 2:
            raise CoreConfigLoadError("Unsupported server configuration schema.")
        if document.units.project_units_per_meter != 10:
            raise CoreConfigLoadError("project_units_per_meter must be exactly 10.")
        if document.units.front_axis != "-Y":
            raise CoreConfigLoadError("front_axis must be '-Y'.")
        if not document.server.api_prefix.startswith("/"):
            raise CoreConfigLoadError("server.api_prefix must start with '/'.")
        positive_server_values = (
            document.server.max_concurrent_jobs,
            document.server.max_queued_jobs,
            document.server.job_retention_seconds,
            document.server.request_timeout_seconds,
            document.server.cancellation_grace_seconds,
            document.server.sse_heartbeat_seconds,
        )
        if any(value <= 0 for value in positive_server_values):
            raise CoreConfigLoadError("Server limits and durations must be positive.")
        circulation = _candidate_circulation(document.candidate_circulation)
        floor_size_policy = _floor_size_policy(document.preprocessing)
        config = FpgCoreConfig(
            schema_version=document.schema_version,
            project_units_per_meter=document.units.project_units_per_meter,
            buildable_space=_buildable_space(document.buildable_space),
            preprocessing=_preprocessing(document.preprocessing, floor_size_policy),
            candidate_search=CandidateSearchConfig(**document.candidate_search),
            candidate_scoring=_candidate_scoring(document.candidate_scoring),
            floor_plan_solver=_solver_profiles(document.floor_plan_solver),
            post_processing=_post_processing(document.post_processing),
            openings=_openings(document.openings),
            floor_plan_scoring=_floor_scoring(document.floor_plan_scoring),
        )
        validate_fpg_core_config(config)
        return ServerConfig(
            server=document.server,
            generation=document.generation_runtime,
            core=config,
            candidate_circulation=circulation,
            floor_size_policy=floor_size_policy,
        )
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


def get_server_config(app: FastAPI) -> ServerConfig:
    config = getattr(app.state, "server_config", None)
    if not isinstance(config, ServerConfig):
        raise CoreConfigLoadError("Server configuration is not initialized")
    return config


def reload_server_config(
    app: FastAPI, path: Path = SERVER_CONFIG_PATH
) -> ServerConfig:
    replacement = load_server_config(path)
    app.state.server_config = replacement
    return replacement


@asynccontextmanager
async def server_lifespan(app: FastAPI) -> AsyncIterator[None]:
    reload_server_config(app)
    yield
