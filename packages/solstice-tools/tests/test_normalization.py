"""Tests for pose normalization functionality."""

import numpy as np
import pytest

from solstice_tools.pose.normalization import (
    normalize_pose_frame,
    normalize_pose_csv_data,
    validate_pose_landmarks,
)
from solstice_tools.exceptions import InvalidDataError


class TestNormalizePoseFrame:
    def test_basic_normalization(self):
        """Test basic pose frame normalization with valid data."""
        # Create mock pose data (33 landmarks * 3 coordinates = 99 values)
        np.random.seed(42)
        mock_landmarks = (
            np.random.rand(33 * 3) * 0.8 + 0.1
        )  # Values between 0.1 and 0.9

        result = normalize_pose_frame(mock_landmarks)

        assert result.shape == mock_landmarks.shape
        assert result.dtype == mock_landmarks.dtype
        assert not np.array_equal(
            result, mock_landmarks
        )  # Should be different after normalization

    def test_empty_landmarks(self):
        empty_landmarks = np.array([])

        with pytest.raises(InvalidDataError, match="Empty landmarks array"):
            normalize_pose_frame(empty_landmarks)

    def test_invalid_shape(self):
        invalid_landmarks = np.array([1, 2, 3, 4, 5])  # 5 elements, not divisible by 3

        with pytest.raises(InvalidDataError, match="not divisible by 3"):
            normalize_pose_frame(invalid_landmarks)

    def test_insufficient_landmarks(self):
        few_landmarks = np.random.rand(15)  # Only 5 landmarks, need at least 25

        with pytest.raises(InvalidDataError, match="Need at least"):
            normalize_pose_frame(few_landmarks)

    def test_custom_target_width(self):
        np.random.seed(42)
        mock_landmarks = np.random.rand(33 * 3) * 0.8 + 0.1

        result1 = normalize_pose_frame(mock_landmarks, target_shoulder_width=0.2)
        result2 = normalize_pose_frame(mock_landmarks, target_shoulder_width=0.3)

        assert not np.array_equal(
            result1, result2
        )  # Different target widths should give different results

    def test_coordinate_bounds(self):
        np.random.seed(42)
        mock_landmarks = np.random.rand(33 * 3) * 2.0  # Wider range to test clipping

        result = normalize_pose_frame(mock_landmarks)
        coords = result.reshape(-1, 3)

        # Check that x,y coordinates are within bounds [-0.3, 1.3]
        assert np.all(coords[:, 0] >= -0.3)
        assert np.all(coords[:, 0] <= 1.3)
        assert np.all(coords[:, 1] >= -0.3)
        assert np.all(coords[:, 1] <= 1.3)


class TestNormalizePoseCSV:
    def test_basic_csv_normalization(self):
        # Create mock CSV with all 33 landmarks
        landmarks = []
        for i in range(33):
            landmarks.extend([f"landmark_{i}_x", f"landmark_{i}_y", f"landmark_{i}_z"])

        header = "frame," + ",".join(landmarks)
        row1_data = [0] + [0.3 + 0.01 * i for i in range(99)]
        row2_data = [1] + [0.31 + 0.01 * i for i in range(99)]

        csv_content = f"{header}\n{','.join(map(str, row1_data))}\n{','.join(map(str, row2_data))}"
        csv_bytes = csv_content.encode("utf-8")

        result = normalize_pose_csv_data(csv_bytes)

        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify it's valid CSV
        result_text = result.decode("utf-8")
        lines = result_text.strip().split("\n")
        assert len(lines) == 3  # Header + 2 data rows

    def test_empty_csv(self):
        empty_csv = b""

        with pytest.raises(InvalidDataError, match="Empty or invalid CSV"):
            normalize_pose_csv_data(empty_csv)

    def test_invalid_encoding(self):
        invalid_bytes = b"\x80\x81\x82"  # Invalid UTF-8

        with pytest.raises(InvalidDataError, match="Invalid CSV encoding"):
            normalize_pose_csv_data(invalid_bytes)

    def test_no_coordinate_columns(self):
        csv_content = "frame,name,other\n0,test,value\n1,test2,value2"
        csv_bytes = csv_content.encode("utf-8")

        with pytest.raises(InvalidDataError, match="No landmark columns found"):
            normalize_pose_csv_data(csv_bytes)

    def test_custom_target_width_csv(self):
        """Test CSV normalization with custom target width."""
        # Create minimal valid CSV
        csv_content = self._create_minimal_csv()
        csv_bytes = csv_content.encode("utf-8")

        result1 = normalize_pose_csv_data(csv_bytes, target_shoulder_width=0.2)
        result2 = normalize_pose_csv_data(csv_bytes, target_shoulder_width=0.3)

        assert result1 != result2

    def _create_minimal_csv(self):
        """Helper to create minimal valid CSV."""
        landmarks = []
        for i in range(33):
            landmarks.extend([f"landmark_{i}_x", f"landmark_{i}_y", f"landmark_{i}_z"])

        header = "frame," + ",".join(landmarks)
        row_data = [0] + [0.5 + 0.01 * i for i in range(99)]

        return f"{header}\n{','.join(map(str, row_data))}"


class TestValidatePoseLandmarks:
    def test_valid_landmarks(self):
        valid_landmarks = np.random.rand(33 * 3)
        validate_pose_landmarks(valid_landmarks)

    def test_empty_landmarks(self):
        empty_landmarks = np.array([])
        with pytest.raises(InvalidDataError, match="Empty landmarks array"):
            validate_pose_landmarks(empty_landmarks)

    def test_invalid_shape(self):
        invalid_landmarks = np.array([1, 2, 3, 4, 5])  # Not divisible by 3
        with pytest.raises(InvalidDataError, match="not divisible by 3"):
            validate_pose_landmarks(invalid_landmarks)

    def test_insufficient_landmarks(self):
        few_landmarks = np.random.rand(15)  # Only 5 landmarks
        with pytest.raises(InvalidDataError, match="Need at least"):
            validate_pose_landmarks(few_landmarks)

    def test_nan_values(self):
        landmarks_with_nan = np.random.rand(33 * 3)
        landmarks_with_nan[0] = np.nan
        with pytest.raises(InvalidDataError, match="NaN values"):
            validate_pose_landmarks(landmarks_with_nan)

    def test_inf_values(self):
        landmarks_with_inf = np.random.rand(33 * 3)
        landmarks_with_inf[0] = np.inf
        with pytest.raises(InvalidDataError, match="infinite values"):
            validate_pose_landmarks(landmarks_with_inf)


class TestNormalizationIntegration:
    def test_frame_to_csv_consistency(self):
        np.random.seed(42)
        mock_landmarks = np.random.rand(33 * 3) * 0.8 + 0.1

        # Normalize as frame
        frame_result = normalize_pose_frame(mock_landmarks)

        # Create CSV with same data and normalize
        landmarks = []
        for i in range(33):
            landmarks.extend([f"landmark_{i}_x", f"landmark_{i}_y", f"landmark_{i}_z"])

        header = "frame," + ",".join(landmarks)
        row_data = [0] + mock_landmarks.tolist()
        csv_content = f"{header}\n{','.join(map(str, row_data))}"
        csv_bytes = csv_content.encode("utf-8")

        csv_result = normalize_pose_csv_data(csv_bytes)
        csv_text = csv_result.decode("utf-8")
        csv_lines = csv_text.strip().split("\n")
        csv_values = csv_lines[1].split(",")[1:]  # Skip frame column
        csv_landmarks = np.array([float(x) for x in csv_values])

        np.testing.assert_allclose(frame_result, csv_landmarks, rtol=1e-10)
