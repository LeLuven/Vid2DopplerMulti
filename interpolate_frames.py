#
# Created by Yue Jiang in August 2020
# MODIFIED to extrapolate frames to full video length
#

import argparse
import os
import numpy as np
os.environ['PYOPENGL_PLATFORM'] = 'egl'
import csv
import cv2  # Import OpenCV
from config import get_paths, get_frame_path
from tqdm import tqdm # Optional: für eine schöne Fortschrittsanzeige

def main(args):

    # get video file name
    video_name = os.path.basename(args.input_video).replace('.mp4', '')
    
    # Get paths using config
    paths = get_paths(video_name, args.output_folder)

    # save hand info
    save_hand_csv = args.save_hand_csv

    # --- MODIFICATION START: Get full video frame count ---
    # get VIBE frames (the tracked subset)
    vibe_frames = np.load(paths['frames'], allow_pickle=True)
    vibe_start_frame = vibe_frames[0]
    vibe_end_frame = vibe_frames[-1]

    # Get true total frames from video
    video = cv2.VideoCapture(args.input_video)
    total_num_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    video.release()
    
    print(f"[INFO] Video total frames: {total_num_frames}")
    print(f"[INFO] VIBE tracked frames: {vibe_start_frame} to {vibe_end_frame}")

    # Save the NEW full frame list (from 0 to N)
    all_frames_list = np.arange(0, total_num_frames)
    np.save(paths['frames_new'], all_frames_list)
    
    # get camera transformation
    orig_cameras = np.genfromtxt(paths['orig_cam'], delimiter=',')
    new_cameras = []

    print(f"[INFO] Extrapolating frames from 0 to {vibe_start_frame - 1}...")
    
    # Load data for first VIBE frame
    first_frame_file = get_frame_path(paths, 'positions', vibe_start_frame)
    first_frame_data = np.genfromtxt(first_frame_file, delimiter=',')
    first_camera_data = orig_cameras[0]
    
    hand_first_frame_data = None
    if save_hand_csv:
        hand_first_file = f"{args.output_folder}/{video_name}/hand_frame_position/frame_{vibe_start_frame:06d}.csv"
        if os.path.isfile(hand_first_file):
            hand_first_frame_data = np.genfromtxt(hand_first_file, delimiter=',')

    for f in tqdm(range(0, vibe_start_frame)):
        new_cameras.append(first_camera_data)
        
        current_frame_file = get_frame_path(paths, 'positions', f)
        np.savetxt(current_frame_file, first_frame_data, delimiter=",")
        
        if save_hand_csv and hand_first_frame_data is not None:

            hand_file = f"{args.output_folder}/{video_name}/hand_frame_velocity/frame_{f:06d}.csv"
            np.savetxt(hand_file, hand_first_frame_data, delimiter=",")

    print(f"[INFO] Interpolating frames from {vibe_start_frame} to {vibe_end_frame}...")
    for i in tqdm(range(len(vibe_frames) - 1)):
        new_cameras.append(orig_cameras[i])
        if vibe_frames[i] + 1 != vibe_frames[i+1]:
            for f in range(vibe_frames[i] + 1, vibe_frames[i+1]):

                # get camera tansformation from the previous avaalable frame
                new_cameras.append(orig_cameras[i])

                # read frame info for human body
                previous_frame_file = get_frame_path(paths, 'positions', vibe_frames[i])
                next_frame_file = get_frame_path(paths, 'positions', vibe_frames[i+1])
                previous_frame = np.genfromtxt(previous_frame_file, delimiter=',')
                next_frame = np.genfromtxt(next_frame_file, delimiter=',')

                # interpolate to get the current frame
                current_frame = np.zeros_like(previous_frame)
                current_frame[:, 3] = np.maximum(previous_frame[:, 3], \
                                                        next_frame[:, 3])
                current_frame[:, :3] = (previous_frame[:, :3] * (vibe_frames[i+1] - f) \
                                        + next_frame[:, :3] * (f - vibe_frames[i])) \
                                                    / (vibe_frames[i+1] - vibe_frames[i])
                
                # read frame info for human hand
                if save_hand_csv:
                    hand_previous_frame = np.genfromtxt(args.output_folder + video_name \
                        + "/hand_frame_position/frame_%06d.csv" \
                                            % vibe_frames[i], delimiter=',')
                    hand_next_frame = np.genfromtxt(args.output_folder + video_name \
                        + "/hand_frame_velocity/frame_%06d.csv" \
                                            % vibe_frames[i+1], delimiter=',')

                    # interpolate to get the current frame
                    hand_current_frame = np.zeros_like(hand_previous_frame)
                    hand_current_frame[:, 3] = np.maximum(hand_previous_frame[:, 3], \
                                                            hand_next_frame[:, 3])
                    hand_current_frame[:, :3] = (hand_previous_frame[:, :3] * (vibe_frames[i+1] - f) \
                                            + hand_next_frame[:, :3] * (f - vibe_frames[i])) \
                                                        / (vibe_frames[i+1] - vibe_frames[i])

                # save each vertex velocity and visibility
                current_frame_file = get_frame_path(paths, 'positions', f)
                np.savetxt(current_frame_file, current_frame, delimiter=",")
                if save_hand_csv:
                    np.savetxt(args.output_folder + video_name \
                         + "/hand_frame_velocity/frame_%06d.csv" \
                                % f, hand_current_frame, delimiter=",")


    # Add the camera for the *last* vibe frame
    new_cameras.append(orig_cameras[-1])
    
    print(f"[INFO] Extrapolating frames from {vibe_end_frame + 1} to {total_num_frames - 1}...")
    
    # Load data for last VIBE frame
    last_frame_file = get_frame_path(paths, 'positions', vibe_end_frame)
    last_frame_data = np.genfromtxt(last_frame_file, delimiter=',')
    last_camera_data = orig_cameras[-1]

    hand_last_frame_data = None
    if save_hand_csv:
        hand_last_file = f"{args.output_folder}/{video_name}/hand_frame_position/frame_{vibe_end_frame:06d}.csv"
        if os.path.isfile(hand_last_file):
            hand_last_frame_data = np.genfromtxt(hand_last_file, delimiter=',')

    for f in tqdm(range(vibe_end_frame + 1, total_num_frames)):
        new_cameras.append(last_camera_data)
        
        current_frame_file = get_frame_path(paths, 'positions', f)
        np.savetxt(current_frame_file, last_frame_data, delimiter=",")
        
        if save_hand_csv and hand_last_frame_data is not None:
            hand_file = f"{args.output_folder}/{video_name}/hand_frame_velocity/frame_{f:06d}.csv"
            np.savetxt(hand_file, hand_last_frame_data, delimiter=",")

    # update camera transformation
    np.savetxt(paths['orig_cam_new'], np.array(new_cameras), delimiter=",")
    print(f"[INFO] Successfully processed and saved all {total_num_frames} frames.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--input_video', type=str,
                        help='input video path or youtube link')

    parser.add_argument('--output_folder', type=str,
                        help='output folder to write results')

    parser.add_argument('--wireframe', action='store_true',
                        help='render all meshes as wireframes.')

    parser.add_argument('--camera_orig', type=str, default="[0,0,10]",
                        help='camera origin position')

    parser.add_argument('--save_hand_csv', action='store_true',
                        help='render all meshes as wireframes.')

    args = parser.parse_args()

    main(args)