ARG CARLA_IMAGE=carlasim/carla:0.9.14
FROM ${CARLA_IMAGE}

CMD ["/bin/bash", "CarlaUE4.sh", "-vulkan", "-RenderOffScreen"]

HEALTHCHECK --interval=1s --timeout=1s --start-period=5s --retries=30 \
    CMD grep -qi ':07d0' /proc/1/net/tcp
