import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
import sys
import argparse # Import the argparse module

# --- 1. Initialize MediaPipe PoseLandmarker ---
mp_pose = mp.solutions.pose
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode
BaseOptions = mp.tasks.BaseOptions

# --- IMPORTANT: Download the model file first ---
# Download from: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker/index#models
# Example: 'pose_landmarker_heavy.task'
model_file_name = 'pose_landmarker_heavy.task' # Or lite, full, etc.

# Check if the model file exists
if not os.path.exists(model_file_name):
    print(f"Error: Model file '{model_file_name}' not found.")
    print(f"Please download it from https://developers.google.com/mediapipe/solutions/vision/pose_landmarker/index#models and place it in the same directory as the script, or provide the full path.")
    sys.exit(1) # Use sys.exit for clean exit on error

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_file_name),
    running_mode=VisionRunningMode.VIDEO,
    num_poses=1,  # Adjust if you need to detect multiple people
    min_pose_detection_confidence=0.5,
    min_pose_presence_confidence=0.5,
    min_tracking_confidence=0.5,
    output_segmentation_masks=False
)

# Create the landmarker
try:
    landmarker = PoseLandmarker.create_from_options(options)
except Exception as e:
    print(f"Error creating PoseLandmarker: {e}")
    sys.exit(1) # Use sys.exit for clean exit on error

# --- Command-line Argument Parsing ---
parser = argparse.ArgumentParser(description='Process a video file to extract MediaPipe pose landmarks.')
parser.add_argument('video_path', help='Path to the input video file.') # Define the command-line argument
args = parser.parse_args() # Parse the arguments

# Use the video path from the command-line arguments
video_path = args.video_path

# --- 2. Open Video File ---
if not os.path.exists(video_path):
    print(f"Error: Video file '{video_path}' not found.")
    sys.exit(1) # Use sys.exit for clean exit on error

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: Could not open video {video_path}")
    sys.exit(1) # Use sys.exit for clean exit on error

# --- 3. Process Video and Extract Positional Data ---
all_pose_positions = []  # List to store positional data for all frames
frame_number = 0

print(f"Processing video: {video_path}")
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Get the timestamp of the current frame in milliseconds
    frame_timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))

    # Convert the BGR frame to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # Perform pose landmarking on the frame.
    try:
        pose_landmarker_result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)
    except Exception as e:
        print(f"Error during landmark detection on frame {frame_number}: {e}")
        frame_number += 1
        continue # Skip to next frame

    if pose_landmarker_result.pose_landmarks:
        for person_landmarks in pose_landmarker_result.pose_landmarks: # Loop through each detected person
            # For simplicity, if num_poses > 1, you might want to add a 'person_id' column
            frame_data = {'frame': frame_number, 'timestamp_ms': frame_timestamp_ms}
            for i, landmark in enumerate(person_landmarks):
                frame_data[f'landmark_{i}_x'] = landmark.x
                frame_data[f'landmark_{i}_y'] = landmark.y
                frame_data[f'landmark_{i}_z'] = landmark.z
            all_pose_positions.append(frame_data)
    else:
        # Optionally, record frames where no poses were detected
        # You might want to add None or NaN for landmark data in these frames
        all_pose_positions.append({'frame': frame_number, 'timestamp_ms': frame_timestamp_ms})


    # Optional: Display progress (e.g., every 100 frames)
    if frame_number % 100 == 0:
        print(f"Processed frame {frame_number} at timestamp {frame_timestamp_ms}ms")

    # Optional: Display the frame with landmarks (uncomment to use)
    # ---
    # display_frame = frame.copy()
    # if pose_landmarker_result.pose_landmarks:
    #     mp_drawing = mp.solutions.drawing_utils
    #     for single_pose_landmarks in pose_landmarker_result.pose_landmarks:
    #         # Convert normalized landmarks to PoseLandmarkerResult format for drawing
    #         # This part requires careful conversion if using mp_drawing directly with PoseLandmarker results
    #         # Alternatively, iterate through single_pose_landmarks and draw circles/lines manually
    #         # For simplicity, drawing is omitted here but can be added as in the previous, more detailed example
    #         # This often involves creating a LandmarkList object or similar structure that mp_drawing expects.
    #         # The PoseLandmarker result already contains the landmarks in a list.
    #
    #         # Example manual drawing of landmarks:
    #         # for lm in single_pose_landmarks:
    #         #     h, w, _ = display_frame.shape
    #         #     cx, cy = int(lm.x * w), int(lm.y * h)
    #         #     cv2.circle(display_frame, (cx, cy), 5, (0, 255, 0), -1)
    #
    #         # Using mp_drawing.draw_landmarks might require converting to a format it expects,
    #         # such as a list of NormalizedLandmark objects. The structure of
    #         # pose_landmarker_result.pose_landmarks[0] is already a list of these.
    #         # Note: This conversion might need adjustment based on your specific mp_drawing version
    #         # and the exact structure of pose_landmarker_result.pose_landmarks
    #         # This commented section is provided as a starting point and might require debugging
    #         # proto_landmarks = [
    #         #     mp.framework.formats.landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z)
    #         #     for lm in single_pose_landmarks
    #         # ]
    #         # landmark_list = mp.framework.formats.landmark_pb2.NormalizedLandmarkList(landmark=proto_landmarks)
    #
    #         # mp_drawing.draw_landmarks(
    #         #     image=display_frame,
    #         #     landmark_list=landmark_list, # This expects a NormalizedLandmarkList
    #         #     connections=mp_pose.POSE_CONNECTIONS,
    #         #     landmark_drawing_spec=mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2),
    #         #     connection_drawing_spec=mp_drawing.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=1)
    #         # )
    #
    # # cv2.imshow('MediaPipe Pose Output', display_frame)
    # # if cv2.waitKey(1) & 0xFF == 27: # Press ESC to exit
    # #     break
    # # ---

    frame_number += 1

# --- 4. Release Resources ---
cap.release()
# if cv2.getWindowProperty('MediaPipe Pose Output', 0) >= 0: # Check if window was opened
#     cv2.destroyAllWindows()
landmarker.close()
print("Video processing complete.")

# --- 5. Store the Positional Timeseries Data ---
if all_pose_positions:
    df_pose_positions = pd.DataFrame(all_pose_positions)

    # Ensure 'frame' and 'timestamp_ms' are the first columns
    cols_to_front = ['frame', 'timestamp_ms']
    other_cols = [col for col in df_pose_positions.columns if col not in cols_to_front]
    # Filter out empty columns if no landmarks were found in some frames
    other_cols = [col for col in other_cols if not df_pose_positions[col].isnull().all()]

    df_pose_positions = df_pose_positions[cols_to_front + other_cols]

    # Save to CSV
    # Generate output filename based on input video name
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_csv_path = f'{base_name}_pose_positions_timeseries.csv'

    df_pose_positions.to_csv(output_csv_path, index=False)
    print(f"Pose positional data saved to {output_csv_path}")
else:
    print("No pose positional data was extracted.")