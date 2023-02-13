FROM carlasim/carla:0.9.10.1 as carla
# Nothing to do, just need this stage to copy some files from

# FROM nvidia/cuda:10.2-cudnn8-runtime-ubuntu18.04
FROM nvidia/cuda:11.3.1-cudnn8-runtime-ubuntu18.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    apt-get install -y \
        wget git gcc g++ \
        libxerces-c3.2 libpng16-16 libjpeg8 libtiff5 libglib2.0-0 libsm6 libxrender1

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && rm /tmp/miniconda.sh \
    && /opt/conda/bin/conda clean -ya
ENV PATH /opt/conda/bin:$PATH

RUN mkdir /transfuser
WORKDIR /transfuser

RUN git clone https://github.com/autonomousvision/transfuser.git /transfuser  \
    && git checkout 2022

RUN conda env create -f environment.yml 
SHELL ["conda", "run", "--no-capture-output", "-n", "tfuse", "/bin/bash", "-c"]

RUN pip install torch==1.11.0+cu113 torchvision==0.12.0+cu113 torchaudio==0.11.0 --extra-index-url https://download.pytorch.org/whl/cu113 \
    && pip install torch-scatter==2.0.9 -f https://data.pyg.org/whl/torch-1.11.0+cu113.html \
    && pip install mmcv-full==1.5.3 -f https://download.openmmlab.com/mmcv/dist/cu113/torch1.11.0/index.html

RUN mkdir carla
COPY --from=carla /home/carla/PythonAPI carla/PythonAPI

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "tfuse"]
CMD [ "/bin/bash", "./leaderboard/scripts/local_evaluation.sh", "carla", "." ]
