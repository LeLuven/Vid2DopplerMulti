
# Environment Setup
1. Create Conda venv with python3.9
2. Prepare mesh repo and python packages
3. Set Cuda environment variables 

## prerequisites
- conda
- python3.9
- nvidia drivers 
- libboost-dev

# 1. Create Conda venv 
```bash
conda create -n vid2dop39 python=3.9
conda activate vid2dop39
conda install -c conda-forge cudatoolkit=11.3 cudnn=8.2
conda install -c conda-forge ffmpeg libiconv
conda update -c conda-forge libstdcxx-ng
export CUDA_BIN_PATH=$CONDA_PREFIX/bin
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
pip install -r requirements.txt

```

# 2. Prepare mesh repo and python packages
mesh is part of this repo, just cd into mesh folder
install boost if not already done: 
```shell
sudo apt-get install libboost-dev
```
(On Mac os)
```shell
$ brew install boost
```
In the mesh folder, run:
```
BOOST_INCLUDE_DIRS=/path/to/boost/include make all
```
Now go to the `Python` folder in `Vid2DopplerMulti` and replace the `meshviewer.py` installed by pybody with the custom one:
```
cp meshviewer.py $CONDA_PREFIX/lib/python3.9/site-packages/psbody/mesh/meshviewer.py
```
In case of using some other virtual environment manager, replace the `meshviewer.py` file installed by psbody with the one provided.

python doppler_from_vid.py --input_video YOUR_INPUT_VIDEO_FILE --model_path PATH_TO_DL_MODELS_FOLDER  



 