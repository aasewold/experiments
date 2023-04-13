FROM ubuntu:20.04

RUN apt update && \
    TZ=Europe/Oslo DEBIAN_FRONTEND=noninteractive \
    apt install -y python3.9 python3.9-venv python3.9-dev \
        build-essential \
        libgeos-dev

ENV VIRTUALENV=/opt/venv
RUN python3.9 -m venv $VIRTUALENV
ENV PATH="$VIRTUALENV/bin:$PATH"

RUN pip install --upgrade pip wheel setuptools \
    && pip install cartopy numpy matplotlib \
        rich ffmpeg-python scipy ouster-sdk \
        jupyterlab pymap3d

CMD ["jupyter-lab", "--allow-root"]
