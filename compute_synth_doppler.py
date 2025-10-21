import numpy as np
import os
from os import listdir
from os.path import isfile, join
from scipy.ndimage import gaussian_filter1d
import argparse
import cv2
from config import get_paths, get_frame_path


N_BINS = 32
DISCARD_BINS = [14,15,16]
GAUSSIAN_BLUR = True
GAUSSIAN_KERNEL = 5
TIME_CHUNK = 1 # 1 second for creating the spectogram


def main(args):

    video_name = os.path.basename(args.input_video).replace('.mp4', '')
    
    paths = get_paths(video_name, args.output_folder)
    
    video = cv2.VideoCapture(args.input_video)
    fps = video.get(cv2.CAP_PROP_FPS)

    num_frames = len([name for name in \
            os.listdir(paths['velocities']) \
            if "frame_" in name])
            
    if os.path.isfile(paths['frames_new']):
        frames = np.load(paths['frames_new'], allow_pickle=True)
    else:
        frames = np.load(paths['frames'], allow_pickle=True)
    print("frames: ", num_frames)

    # compute synthetic doppler data
    synth_doppler_dat = []
    for frame_idx in frames:
        velocity_file = get_frame_path(paths, 'velocities', frame_idx)
        gen_doppler = np.genfromtxt(velocity_file, delimiter=',')
        velocity = gen_doppler[gen_doppler[:, 1]==1, 0]
        hist = np.histogram(velocity, bins=np.linspace(-2, 2, num=N_BINS+1))[0]
        for bin_idx in DISCARD_BINS:
            hist[bin_idx] = 0
        synth_doppler_dat.append(hist/gen_doppler.shape[0])

    synth_doppler_dat = np.array(synth_doppler_dat)

    if GAUSSIAN_BLUR:
        for i in range(len(synth_doppler_dat)):
            synth_doppler_dat[i] = gaussian_filter1d(synth_doppler_dat[i], GAUSSIAN_KERNEL)

    np.save(paths['synth_doppler'], synth_doppler_dat)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('--input_video', type=str, help='input video file')

    parser.add_argument('--output_folder', type=str, help='output folder to write results')

    args = parser.parse_args()

    main(args)
