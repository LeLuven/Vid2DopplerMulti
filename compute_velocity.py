import argparse
import csv
import math
import cv2
import os
import numpy as np
from config import get_paths, get_frame_path


def main(args):

    # define camera origin position
    camera_orig = [float(i) for i in args.camera_orig[1:-1].split(',')]

    # get video file name
    video_name = os.path.basename(args.input_video).replace('.mp4', '')
    
    paths = get_paths(video_name, args.output_folder)
    velocities_dir = paths['velocities']

    # get fps of the video
    video = cv2.VideoCapture(args.input_video)
    fps = video.get(cv2.CAP_PROP_FPS)

    # get the number of frames
    num_frames = len([name for name in os.listdir(paths['positions']) \
                            if "frame_" in  name])

    # read frame info as numpy arrays from csv files
    vertex_position = []
    vertex_visibilty = []

    if os.path.isfile(paths['frames_new']):
        frames = np.load(paths['frames_new'], allow_pickle=True)
    else:
        frames = np.load(paths['frames'], allow_pickle=True)

    for frame_idx in frames:

        # read frame info for human body
        position_file = get_frame_path(paths, 'positions', frame_idx)
        frame_info = np.genfromtxt(position_file, delimiter=',')
        vertex_position.append(frame_info[:, :3])
        vertex_visibilty.append(frame_info[:, 3:])

    # change position and visibility lists to numpy arrays
    vertex_position = np.array(vertex_position)
    vertex_visibilty = np.array(vertex_visibilty)

    # get camera transformation
    if os.path.isfile(paths['orig_cam_new']):
        orig_cameras = np.genfromtxt(paths['orig_cam_new'], delimiter=',')
    else:
        orig_cameras = np.genfromtxt(paths['orig_cam'], delimiter=',')


    # compute radial velocity for human body
    vertex_velocity_list = []


    for frame_idx in range(len(frames)):

        # skip the first frame
        if frame_idx < 1:
            vertex_velocity = np.expand_dims(np.zeros_like(\
                        vertex_position[frame_idx][:,0]), axis=1)
            vertex_velocity_list.append(vertex_velocity)

        # Calculate radial velocity
        else:

            # compute radial velocity for human body
            v = vertex_position[frame_idx] - vertex_position[frame_idx-1]
            p_t_1 = vertex_position[frame_idx-1] - camera_orig
            p_t_2 = vertex_position[frame_idx] - camera_orig
            v = p_t_2 - p_t_1
            dot_prod = np.multiply(v, p_t_2).sum(axis=1)
            mag = np.linalg.norm(p_t_2, axis=1)
            vertex_velocity = np.expand_dims(-(dot_prod / mag) * fps, axis=1)
            vertex_velocity_list.append(vertex_velocity)


    # compute velocity mean for human body using convolution
    velocity_map = np.array(vertex_velocity_list)
    velocity_map = velocity_map[:,:,0]
    for j in range(velocity_map.shape[1]):
       velocity_map[:,j] = np.convolve(velocity_map[:,j], \
                                np.ones((5,))/5, mode='same')
    velocity_map = np.expand_dims(velocity_map, axis=2)

    # save velocities and visibilities
    index = 0
    for frame_idx in frames:

        # concatenate velocities and visibilities
        frame_info = np.concatenate((velocity_map[index], \
                                vertex_visibilty[index]), axis=1)


        # save each vertex velocity and visibility
        velocity_file = get_frame_path(paths, 'velocities', frame_idx)
        np.savetxt(velocity_file, frame_info, delimiter=",")

        index += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--input_video', type=str,
                        help='input video file')

    parser.add_argument('--output_folder', type=str,
                        help='output folder to write results')

    parser.add_argument('--camera_orig', type=str, default="[0,0,10]",
                        help='camera origin position')


    args = parser.parse_args()

    main(args)
