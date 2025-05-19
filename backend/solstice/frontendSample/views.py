import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
import sys
import argparse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status

# --- 1. Initialize MediaPipe PoseLandmarker ---
mp_pose = mp.solutions.pose
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode
BaseOptions = mp.tasks.BaseOptions


class VideoUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, format=None):
        video = request.FILES.get("video")
        option = request.data.get("option")  # Get the option from the form data
        print("Received option:", option)  # Print the option to the console
        if video:
            save_path = os.path.join(settings.MEDIA_ROOT, video.name)
            with open(save_path, "wb+") as destination:
                for chunk in video.chunks():
                    destination.write(chunk)
            return Response(
                {"message": "Video uploaded", "option": option},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"error": "No video uploaded"}, status=status.HTTP_400_BAD_REQUEST
        )


class VideoListView(APIView):
    def get(self, request, format=None):
        video_dir = settings.MEDIA_ROOT
        videos = sorted(
            [f for f in os.listdir(video_dir) if f.endswith((".mp4", ".webm", ".ogg"))],
            key=lambda x: os.path.getmtime(os.path.join(video_dir, x)),
        )
        video_url = (
            request.build_absolute_uri(settings.MEDIA_URL + videos[-1])
            if videos
            else ""
        )
        processed_video_url = process_video_and_save_csv(video_url)
        return Response({"video1": video_url, "video2": processed_video_url})


def process_video_and_save_csv(video_path):
    # --- MediaPipe setup (reuse your initialization code) ---
    mp_pose = mp.solutions.pose
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    BaseOptions = mp.tasks.BaseOptions

    # error here
    model_file_name = "pose_landmarker_lite.task"
    if not os.path.exists(model_file_name):
        raise FileNotFoundError(
            f"Model file '{model_file_name}' not found. "
            "Download it from https://developers.google.com/mediapipe/solutions/vision/pose_landmarker/index#models"
        )

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_file_name),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )

    landmarker = PoseLandmarker.create_from_options(options)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file '{video_path}' not found.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {video_path}")

    all_pose_positions = []
    frame_number = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        try:
            pose_landmarker_result = landmarker.detect_for_video(
                mp_image, frame_timestamp_ms
            )
        except Exception:
            frame_number += 1
            continue

        if pose_landmarker_result.pose_landmarks:
            for person_landmarks in pose_landmarker_result.pose_landmarks:
                frame_data = {"frame": frame_number, "timestamp_ms": frame_timestamp_ms}
                for i, landmark in enumerate(person_landmarks):
                    frame_data[f"landmark_{i}_x"] = landmark.x
                    frame_data[f"landmark_{i}_y"] = landmark.y
                    frame_data[f"landmark_{i}_z"] = landmark.z
                all_pose_positions.append(frame_data)
        else:
            all_pose_positions.append(
                {"frame": frame_number, "timestamp_ms": frame_timestamp_ms}
            )

        frame_number += 1

    cap.release()
    landmarker.close()

    if all_pose_positions:
        df_pose_positions = pd.DataFrame(all_pose_positions)
        cols_to_front = ["frame", "timestamp_ms"]
        other_cols = [
            col for col in df_pose_positions.columns if col not in cols_to_front
        ]
        other_cols = [
            col for col in other_cols if not df_pose_positions[col].isnull().all()
        ]
        df_pose_positions = df_pose_positions[cols_to_front + other_cols]
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_csv_path = os.path.join(
            os.path.dirname(video_path), f"{base_name}_pose_positions_timeseries.csv"
        )
        df_pose_positions.to_csv(output_csv_path, index=False)
        return output_csv_path
    else:
        return None
