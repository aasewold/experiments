# Used to retreive the CARLA Python API
ARG CARLA_VERSION
FROM carlasim/carla:${CARLA_VERSION} AS carla


FROM ubuntu:18.04 as routegen

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    apt-get install -y \
        python3 python3-pip \
        wget git gcc g++ \
        libxerces-c3.2 libpng16-16 libjpeg8 libtiff5 libglib2.0-0 libsm6 libxrender1

RUN python3 -m pip install lxml==4.9.2 numpy==1.18.1 networkx==2.2

RUN mkdir /routegen
WORKDIR /routegen

RUN mkdir carla
COPY --from=carla /home/carla/PythonAPI carla/PythonAPI

RUN mkdir results

ENV WORK_DIR    /routegen
ENV CARLA_ROOT  /routegen/carla
ENV RESULTS_DIR /routegen/results

COPY . .
