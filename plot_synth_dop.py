import os
import numpy as np
import matplotlib
from helper import get_spectograms, root_mean_squared_error, color_scale, rolling_window_combine
from tensorflow.keras.models import load_model
import pickle
import cv2
import argparse
from config import get_paths

def main(args):
    print("Doppler Plot started")
    out_vid = None
    writer_size = None  
    model_path = args.model_path

    lb = pickle.loads(open(os.path.join(model_path, "classifier_classes.lbl"), "rb").read())
    autoencoder = load_model(os.path.join(model_path, "autoencoder_weights.hdf5"), custom_objects={'root_mean_squared_error': root_mean_squared_error})
    scale_vals = np.load(os.path.join(model_path, "scale_vals.npy"))
    fps = 24
    TIME_CHUNK = 3
    max_dopVal = scale_vals[0]
    max_synth_dopVal =  scale_vals[1]
    min_dopVal = scale_vals[2]
    min_synth_dopVal = scale_vals[3]

    vid_f = args.input_video
    in_folder = os.path.dirname(vid_f)
    vid_file_name = os.path.basename(vid_f).replace('.mp4', '')
    
    paths = get_paths(vid_file_name, "output")
    if not os.path.exists(paths['synth_doppler']):
        paths = get_paths("video", "output")

    cap = cv2.VideoCapture(vid_f)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    synth_doppler_dat_f = paths['synth_doppler']
    synth_doppler_dat = np.load(synth_doppler_dat_f)
    synth_spec_pred = get_spectograms(synth_doppler_dat, TIME_CHUNK, fps, synthetic=True, zero_pad=True)
    synth_spec_pred = synth_spec_pred.astype("float32")
    synth_spec_test = (synth_spec_pred - min_synth_dopVal)/(max_synth_dopVal - min_synth_dopVal)
    dop_spec_test = np.zeros_like(synth_spec_test)

    if args.doppler_gt:
        doppler_dat_pos_f = in_folder + "/doppler_gt.npy"
        doppler_dat_pos = np.load(doppler_dat_pos_f)
        dop_spec = get_spectograms(doppler_dat_pos, TIME_CHUNK, fps, zero_pad=True)
        dop_spec = dop_spec.astype("float32")
        dop_spec_test = (dop_spec - min_dopVal)/(max_dopVal - min_dopVal)

    decoded = autoencoder.predict(synth_spec_test)
    decoded = decoded[:,:,:,0]
    decoded = rolling_window_combine(decoded)

    y_max = max(np.max(decoded),np.max(synth_spec_test),np.max(dop_spec_test))
    norm = matplotlib.colors.Normalize(vmin=0, vmax=y_max)

    print(f"Video has {total_frames} frames, Doppler data has {len(dop_spec_test)} frames")

    frames_to_process = min(len(dop_spec_test), total_frames)
    print(f"Processing {frames_to_process} frames")

    for idx in range(0, frames_to_process):
        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                print(f"Warning: Could not read frame {idx}, skipping...")
                continue
            print(f"\rProcessing frame {idx+1}/{frames_to_process}", end="")
            
            original_synth = color_scale(synth_spec_test[idx],matplotlib.colors.Normalize(vmin=0, vmax=np.max(synth_spec_test)),"Initial Synthetic Doppler")
            original_dop = color_scale(dop_spec_test[idx],matplotlib.colors.Normalize(vmin=0, vmax=np.max(dop_spec_test)),"Real World Doppler")
            recon = color_scale(decoded[idx],matplotlib.colors.Normalize(vmin=0, vmax=np.max(decoded)),"Final Synthetic Doppler")
            in_frame = color_scale(frame,None,"Input Video")
            output = np.hstack([in_frame,original_dop, original_synth, recon])

            if out_vid is None:
                frame_height = output.shape[0]
                frame_width = output.shape[1]
                writer_size = (frame_width, frame_height)
                
                print(f"\nInitialisiere VideoWriter mit Größe {frame_width}x{frame_height} und Codec 'mp4v'\n")

                out_vid = cv2.VideoWriter(os.path.join(paths['videos'], vid_file_name+'_output_signal.mp4'),
                                          cv2.VideoWriter_fourcc(*'mp4v'), 
                                          fps,
                                          writer_size) 
            
            current_shape_wh = (output.shape[1], output.shape[0])
            if current_shape_wh != writer_size:
                print(f"\nFEHLER: Frame-Größe hat sich geändert! Writer erwartet {writer_size}, aber Frame {idx} hat {current_shape_wh}\n")
                break 
            
            out_vid.write(output.astype(np.uint8))

        except Exception as e:
            print(f"\nError processing frame {idx}: {e}") 
            break

    cap.release()
    if out_vid is not None:
        out_vid.release()
        print(f"\nOutput-Video gespeichert in: {paths['videos']}")
    else:
        print("\nKeine Frames verarbeitet, kein Video gespeichert.")
        
if __name__ == '__main__':

	parser = argparse.ArgumentParser()

	parser.add_argument('--input_video', type=str, help='Input video file')

	parser.add_argument('--model_path', type=str, help='Path to DL models')

	parser.add_argument('--doppler_gt', help='Doppler Ground Truth is available for reference', action='store_true')

	args = parser.parse_args()

	main(args)
