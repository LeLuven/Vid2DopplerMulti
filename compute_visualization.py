#
# Created by Yue Jiang in June 2020
#

import argparse
import csv
import math
import cv2
import os
os.environ['PYOPENGL_PLATFORM'] = 'egl'
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from velocity_renderer import VelocityRenderer
import colorsys
from config import get_paths, get_frame_path


def main(args):

    # define camera origin position
    camera_orig = [float(i) for i in args.camera_orig[1:-1].split(',')]

    # get video file name
    video_name = os.path.basename(args.input_video).replace('.mp4', '')
    
    # Get paths using config
    paths = get_paths(video_name, args.output_folder)

    # get fps of the video
    video = cv2.VideoCapture(args.input_video)
    fps = video.get(cv2.CAP_PROP_FPS)

    # define video writer
    fourcc = cv2.VideoWriter_fourcc('D', 'I', 'V', 'X')
    if args.wireframe:
        out = cv2.VideoWriter(os.path.join(paths['videos'], f'{video_name}_result_wireframe.mp4'), fourcc, fps, \
                            (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), \
                            int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))))
    else:
        out = cv2.VideoWriter(os.path.join(paths['videos'], f'{video_name}_result_mesh.mp4'), fourcc, fps, \
                            (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), \
                            int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))))

    # get the number of frames
    num_frames = len([name for name in \
            os.listdir(paths['positions']) \
            if "frame_" in name])
            
    if os.path.isfile(paths['frames_new']):
        frames = np.load(paths['frames_new'], allow_pickle=True)
    else:
        frames = np.load(paths['frames'], allow_pickle=True)
    print("visualized frames: ", len(frames))

    # read frame info as numpy arrays from csv files
    vertex_position = []
    vertex_velocity = []

    for frame_idx in frames:

        # read frame info for human body
        position_file = get_frame_path(paths, 'positions', frame_idx)
        frame_info = np.genfromtxt(position_file, delimiter=',')
        vertex_position.append(frame_info[:, :3])
        
        velocity_file = get_frame_path(paths, 'velocities', frame_idx)
        frame_info = np.genfromtxt(velocity_file, delimiter=',')
        vertex_velocity.append(frame_info[:, 0])


    # get the number of vertices
    num_vertices = vertex_position[0].shape[0]

    # get predicted camera positions from the model
    orig_cameras = np.genfromtxt(paths['orig_cam'], delimiter=',')

    # change position and velocity lists to numpy arrays
    vertex_position = np.array(vertex_position)
    vertex_velocity = np.array(vertex_velocity)


    # loop over frames
    count = 0
    for frame_idx in frames:

        # capture frames in the video
        ret, frame = video.read()
        print("Visualizing Frame #" + str(count))
        count +=1

        # define renderer
        if frame_idx == 0:
            orig_height, orig_width = frame.shape[:2]
            renderer = VelocityRenderer(resolution=(orig_width, \
                                    orig_height), orig_img=True, \
                                    wireframe=args.wireframe)

        # skip frames without the main person
        if frame_idx not in frames:
            continue

        # compute velocity colors
        velocity_colors = np.zeros((num_vertices, 3))
        max_velocity = 2
        min_velocity = -2

        # define coolwarm mapping
        cmap = plt.get_cmap("RdYlBu")
        norm = matplotlib.colors.Normalize(vmin=-0.5, vmax=0.5)
        coolwarm_mapping = matplotlib.cm.ScalarMappable(cmap=cmap, norm=norm)

        # get velocity colors
        velocity_colors = coolwarm_mapping.to_rgba(\
                                        vertex_velocity[frame_idx])[:, :-1]

        # get camera direction
        camera_dir = camera_orig / np.linalg.norm(camera_orig)

        # smooth the video result
        count_frame = 1
        position = vertex_position[frame_idx]
        for i in range(7):
            if frame_idx > i:
                position += vertex_position[frame_idx-i-1]
                count_frame += 1
            if frame_idx < len(frames) - (i + 1):
                position += vertex_position[frame_idx+i+1]
                count_frame += 1
        position /= count_frame

        # render images
        visibility_image, velocity_image, example_image = renderer.render(
            frame, position,
            cam_transformation=orig_cameras[frame_idx],
            cam_dir = camera_dir,
            velocity_colors=velocity_colors,
            mesh_filename=None,
            # angle=45,
            # axis=[ -0.3826834, 0, 0, 0.9238795 ]
        )

        # output with or without background
        if args.background:
            frame = velocity_image * (velocity_image > 0) + frame * (velocity_image == 0)
        else:
            frame = velocity_image

        # output results with both velocity and visibility
        if args.concatenate_result:
            frame = np.concatenate([frame, visibility_image, \
                                    velocity_image, example_image], axis=1)

        # Display the resulting frame
        out.write(frame)

    # release the cap object
    out.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--input_video', type=str,
                        help='input video file')

    parser.add_argument('--output_folder', type=str,
                        help='output folder to write results')

    parser.add_argument('--wireframe', action='store_true',
                        help='render all meshes as wireframes.')

    parser.add_argument('--concatenate_result', action='store_true',
                        help='output concatenate result of velocity and visibility.')

    parser.add_argument('--background', action='store_true',
                        help='output result with original background.')

    parser.add_argument('--camera_orig', type=str, default="[0,0,10]",
                        help='camera origin position')

    args = parser.parse_args()

    main(args)
