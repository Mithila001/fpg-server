#!/usr/bin/env python3
"""
Test script for spatial coverage scoring implementation.
Validates helper functions and main scoring logic.
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.algorithms.fpg_optuna_score.score.spatial_coverage import (
    _get_boundary_virtual_points,
    _calculate_ideal_distance,
    _calculate_nnd_metrics,
    _compute_density_penalty,
    _compute_uniformity_score,
    _compute_edge_coverage_score,
    score_spatial_coverage,
)
from app.algorithms.fpg_optuna_score.util.scoring_common import OptunaScorePoint
from app.algorithms.types.domain import FpgRequirements, RoomData, ConfigData


def test_boundary_virtual_points():
    """Test virtual boundary point generation."""
    print("\n=== Test: Boundary Virtual Points ===")
    points = _get_boundary_virtual_points(100.0, 150.0)

    print(f"Generated {len(points)} boundary points")
    assert len(points) == 12, f"Expected 12 points, got {len(points)}"

    # Verify corners
    corners = points[:4]
    assert (0.0, 0.0) in corners, "Missing bottom-left corner"
    assert (100.0, 0.0) in corners, "Missing bottom-right corner"
    assert (100.0, 150.0) in corners, "Missing top-right corner"
    assert (0.0, 150.0) in corners, "Missing top-left corner"

    print("✓ All 4 corners present")
    print(f"✓ All 12 boundary points valid: {points}")


def test_ideal_distance():
    """Test ideal distance calculation."""
    print("\n=== Test: Ideal Distance ===")

    # 100 x 150 area = 15000, with 5 points
    floor_area = 100.0 * 150.0
    num_points = 5
    ideal = _calculate_ideal_distance(floor_area, num_points)

    print(f"Floor area: {floor_area}, Num points: {num_points}")
    print(f"Ideal distance: {ideal:.2f}")

    # Should be sqrt(15000 / 5) = sqrt(3000) ≈ 54.77
    expected = (floor_area / num_points) ** 0.5
    assert abs(ideal - expected) < 0.01, f"Expected ~{expected}, got {ideal}"

    print(f"✓ Ideal distance matches expectation: {expected:.2f}")


def test_nnd_metrics():
    """Test NND metrics calculation."""
    print("\n=== Test: NND Metrics ===")

    # Create simple test points (grid pattern)
    room_points = [
        OptunaScorePoint("R1", "bedroom", 25.0, 25.0),
        OptunaScorePoint("R2", "bedroom", 75.0, 25.0),
        OptunaScorePoint("R3", "bedroom", 25.0, 75.0),
        OptunaScorePoint("R4", "bedroom", 75.0, 75.0),
    ]
    boundary_points = []

    mean_nnd, std_dev, distances = _calculate_nnd_metrics(room_points, boundary_points)

    print(f"Mean NND: {mean_nnd:.2f}")
    print(f"Std Dev NND: {std_dev:.2f}")
    print(f"All distances: {distances}")

    assert mean_nnd > 0, "Mean NND should be positive"
    assert std_dev >= 0, "Std dev should be non-negative"
    assert len(distances) == 4, f"Expected 4 distances, got {len(distances)}"

    print("✓ NND metrics valid")


def test_density_penalty():
    """Test density penalty calculation."""
    print("\n=== Test: Density Penalty ===")

    ideal_dist = 50.0

    # Test within range (no penalty)
    penalty_ok = _compute_density_penalty(50.0, ideal_dist)
    print(f"Penalty (mean_nnd=50, ideal=50): {penalty_ok:.2f}")
    assert abs(penalty_ok - 1.0) < 0.01, "Expected ~1.0 (no penalty)"

    # Test clumping
    penalty_clump = _compute_density_penalty(30.0, ideal_dist)
    print(f"Penalty (clump: mean_nnd=30, ideal=50): {penalty_clump:.2f}")
    assert penalty_clump < 1.0, "Clumping should incur penalty"

    # Test gap
    penalty_gap = _compute_density_penalty(80.0, ideal_dist)
    print(f"Penalty (gap: mean_nnd=80, ideal=50): {penalty_gap:.2f}")
    assert penalty_gap < 1.0, "Gap should incur penalty"

    print("✓ Density penalties work correctly")


def test_uniformity_score():
    """Test uniformity score calculation."""
    print("\n=== Test: Uniformity Score ===")

    # Low std dev (uniform) - std_dev=5 with discrepancy=10 gives exp(-0.5) ≈ 60.7%
    score_uniform = _compute_uniformity_score(5.0)
    print(f"Uniformity score (std_dev=5): {score_uniform:.1f}%")
    assert 50 < score_uniform < 70, f"Expected ~60%, got {score_uniform}%"

    # High std dev (non-uniform) - std_dev=50 with discrepancy=10 gives exp(-5) ≈ 0.67%
    score_rough = _compute_uniformity_score(50.0)
    print(f"Uniformity score (std_dev=50): {score_rough:.1f}%")
    assert score_rough < 2, "Rough distribution should have very low score"

    # Zero std dev (perfect uniformity)
    score_perfect = _compute_uniformity_score(0.0)
    print(f"Uniformity score (std_dev=0): {score_perfect:.1f}%")
    assert abs(score_perfect - 100.0) < 0.01, "Perfect uniformity should score 100"

    # Moderate std dev
    score_moderate = _compute_uniformity_score(10.0)
    print(f"Uniformity score (std_dev=10): {score_moderate:.1f}%")
    assert 30 < score_moderate < 50, "Moderate std dev should give moderate score"

    print("✓ Uniformity scoring works correctly")


def test_edge_coverage_score():
    """Test edge coverage score calculation."""
    print("\n=== Test: Edge Coverage Score ===")

    # Room points near boundary
    room_points = [
        OptunaScorePoint("R1", "bedroom", 10.0, 10.0),
        OptunaScorePoint("R2", "bedroom", 90.0, 10.0),
        OptunaScorePoint("R3", "bedroom", 10.0, 90.0),
        OptunaScorePoint("R4", "bedroom", 90.0, 90.0),
    ]
    boundary_points = _get_boundary_virtual_points(100.0, 100.0)
    ideal_dist = 30.0

    coverage = _compute_edge_coverage_score(room_points, boundary_points, ideal_dist)
    print(f"Edge coverage score: {coverage:.1f}%")
    assert 0 <= coverage <= 100, "Coverage should be between 0-100"

    print("✓ Edge coverage score valid")


def test_score_spatial_coverage_complete():
    """Test complete scoring function."""
    print("\n=== Test: Complete Spatial Coverage Scoring ===")

    # Create a sample floor plan with 5 rooms
    rooms = [
        RoomData(
            name="Living Room",
            type="livingRoom",
            min_w=30,
            min_h=30,
            max_w=50,
            max_h=50,
        ),
        RoomData(
            name="Kitchen",
            type="kitchen",
            min_w=20,
            min_h=20,
            max_w=40,
            max_h=40,
        ),
        RoomData(
            name="Bedroom 1",
            type="bedroom",
            min_w=20,
            min_h=20,
            max_w=30,
            max_h=30,
        ),
        RoomData(
            name="Bedroom 2",
            type="bedroom",
            min_w=20,
            min_h=20,
            max_w=30,
            max_h=30,
        ),
        RoomData(
            name="Bathroom",
            type="bathroom",
            min_w=10,
            min_h=10,
            max_w=15,
            max_h=15,
        ),
    ]

    config = ConfigData(
        min_coverage=0.5,
        max_aspect_ratio=10.0,
        min_aspect_ratio=0.1,
        floor_plan_width=150.0,
        floor_plan_height=200.0,
    )

    requirements = FpgRequirements(rooms=rooms, config=config)

    # Create room points (scattered across floor)
    room_points = [
        OptunaScorePoint("Living Room", "livingRoom", 40.0, 100.0),
        OptunaScorePoint("Kitchen", "kitchen", 100.0, 100.0),
        OptunaScorePoint("Bedroom 1", "bedroom", 40.0, 40.0),
        OptunaScorePoint("Bedroom 2", "bedroom", 100.0, 40.0),
        OptunaScorePoint("Bathroom", "bathroom", 75.0, 150.0),
    ]

    result = score_spatial_coverage(requirements, room_points)

    print("\nScoring Results:")
    print(f"  Final Score: {result.score:.2f} / {result.max_score}")
    print(
        f"  Raw Internal Score: {result.details.get('raw_internal_score', 'N/A'):.1f}"
    )
    print(f"  Mean NND: {result.details.get('mean_nnd', 'N/A'):.2f}")
    print(f"  Std Dev NND: {result.details.get('std_dev_nnd', 'N/A'):.2f}")
    print(f"  Uniformity Score: {result.details.get('uniformity_score', 'N/A'):.1f}%")
    print(f"  Edge Coverage: {result.details.get('edge_coverage_score', 'N/A'):.1f}%")
    print(f"  Density Penalty: {result.details.get('density_penalty', 'N/A'):.2f}")

    if result.warnings:
        print("\n  Warnings:")
        for warning in result.warnings:
            print(f"    - {warning}")

    # Verify output
    assert 0 <= result.score <= result.max_score, (
        f"Score {result.score} out of range [0, {result.max_score}]"
    )
    assert result.details is not None, "Details should not be None"
    assert result.max_score == 10, "Max score should be 10"

    print("\n✓ Complete scoring function works correctly")
    print("✓ Heatmap saved to test/outputs/optuna_score/spatial_coverage/")


def test_edge_cases():
    """Test edge cases."""
    print("\n=== Test: Edge Cases ===")

    config = ConfigData(
        min_coverage=0.5,
        max_aspect_ratio=10.0,
        min_aspect_ratio=0.1,
        floor_plan_width=100.0,
        floor_plan_height=150.0,
    )
    requirements = FpgRequirements(rooms=[], config=config)

    # Empty room points
    print("Testing empty room points...")
    result_empty = score_spatial_coverage(requirements, [])
    assert result_empty.score == 0, "Empty room points should score 0"
    assert len(result_empty.warnings) > 0, "Should have warning for empty points"
    print("✓ Empty points handled correctly")

    # Single room point
    print("Testing single room point...")
    single_point = [OptunaScorePoint("Room1", "bedroom", 50.0, 75.0)]
    result_single = score_spatial_coverage(requirements, single_point)
    assert 0 <= result_single.score <= 10, "Single point score should be valid"
    print(f"✓ Single point score: {result_single.score:.2f}")


if __name__ == "__main__":
    print("=" * 60)
    print("SPATIAL COVERAGE SCORING - TEST SUITE")
    print("=" * 60)

    try:
        test_boundary_virtual_points()
        test_ideal_distance()
        test_nnd_metrics()
        test_density_penalty()
        test_uniformity_score()
        test_edge_coverage_score()
        test_score_spatial_coverage_complete()
        test_edge_cases()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
