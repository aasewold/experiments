# Used to retreive the CARLA Python API
ARG CARLA_VERSION
FROM carlasim/carla:${CARLA_VERSION} AS carla


# Clones and checks out interfuser
FROM alpine/git AS interfuser

RUN mkdir /interfuser
WORKDIR /interfuser

RUN git clone https://github.com/aasewold/InterFuser.git /interfuser

# Final image
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

RUN mkdir /interfuser
WORKDIR /interfuser

RUN mkdir carla
COPY --from=carla /home/carla/PythonAPI carla/PythonAPI

RUN conda create -n interfuser python=3.7

SHELL ["conda", "run", "--no-capture-output", "-n", "interfuser", "/bin/bash", "-c"]

COPY --from=interfuser /interfuser /interfuser/requirements.txt ./
RUN pip install -r requirements.txt


COPY --from=interfuser /interfuser/interfuser /interfuser/interfuser
RUN cd interfuser && python setup.py develop && cd ..

RUN easy_install carla/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg

RUN pip install -U pip && pip install -U setuptools

COPY --from=interfuser /interfuser /interfuser

ENV CUDA_VISIBLE_DEVICES=0
ENV SDL_VIDEODRIVER=dummy

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "interfuser"]

CMD ["/bin/bash", "./leaderboard/scripts/run_evaluation.sh" ]
