#!/bin/bash
set -euo pipefail
export LC_NUMERIC="en_US.UTF-8"

run_path="$1"; shift

run_path="$(realpath "$run_path")"
run_name="$(basename "$run_path")"

is_interfuser() {
    if [[ "$run_path" == *"inter"* ]]; then
        return 0
    fi
    return 1
}

viz_path="$run_path/$(is_interfuser && echo 'data/eval' || echo 'viz')"
if [ ! -d "$viz_path" ]; then
    echo "Directory $viz_path does not exist"
    exit 1
fi

FPS=${FPS:-60}
echo "Using FPS: $FPS"

mov_path="$run_path"/mov
final_mp4="$run_path"/"$run_name".mp4

if [ -d "$mov_path" ]; then
    echo "Directory $mov_path already exists"
    exit 1
fi

if [ -f "$final_mp4" ]; then
    echo "File $final_mp4 already exists"
    exit 1
fi

mkdir -p "$mov_path"
echo "$USER@$(hostname)" > "$mov_path"/host

ffmpeg() {
    # 'chapter' isn't supported for ffmpeg < v5, so we use a docker image
    # to get the newest version
    docker run --rm \
        -e PUID="$(id -u)" \
        -e PGID="$(id -g)" \
        -v "$(pwd -P)":"$(pwd -P)" \
        -w "$(pwd -P)" \
        linuxserver/ffmpeg \
        -nostdin "$@"
}

enough_free_mem() {
    local free=$(cat /proc/meminfo | grep MemAvailable | awk '{print $2}')
    if [ "$free" -lt 5000000 ]; then
        return 1
    fi
    return 0
}

# For each route in viz/*, create a video of that route
# FFmpeg flags are chosen according to
# https://gist.github.com/mikoim/27e4e0dc64e384adbcb91ff10a2d3678
# and https://trac.ffmpeg.org/wiki/Encode/YouTube.
# Upscaling is done to keep the video quality high when YouTube
# compresses it.

# Kill all ffmpeg processes on exit
trap "trap - SIGTERM && killall ffmpeg && exit 1" SIGINT SIGTERM

# InterFuser routes have a 'meta' subdirectory
meta=$(is_interfuser && echo "meta" || echo "")

shopt -s nullglob
for route in "$viz_path" "$viz_path"/*/; do
    while ! enough_free_mem; do
        echo "Not enough free memory, waiting"
        sleep 5
    done
    echo "Processing $route"
    routename="$(basename "$route")"
    
    route="$route$meta"

    if [ -f "$route"/1.jpg ]; then
        fmt="%d.jpg"
    elif [ -f "$route"/1.png ]; then
        fmt="%d.png"
    elif [ -f "$route"/0001.jpg ]; then
        fmt="%04d.jpg"
    elif [ -f "$route"/0001.png ]; then
        fmt="%04d.png"
    else
        echo "No images found in $route"
        continue
    fi

    ffmpeg -y -r "$FPS" -f image2 \
        -i "$route/$fmt" \
        -vf 'scale=iw*2:ih*2:flags=neighbor' \
        -c:v libx264 -preset veryfast -profile:v high -bf 2 -g 30 -crf 18 -pix_fmt yuv420p -movflags faststart \
        -y "$mov_path/$routename.mp4" \
        -hide_banner -loglevel error &
    sleep 2
done
shopt -u nullglob

echo "Waiting for all processes to finish"
wait

round() {
    printf "%.0f" "${1}"
}

fmt_time() {
    t="$1"
    t="$(round "$t")"
    h=$(echo "$t / 3600" | bc)
    m=$(echo "($t - $h * 3600) / 60" | bc)
    s=$(echo "$t - $h * 3600 - $m * 60" | bc)
    if [ "$h" -eq 0 ]; then
        printf "%02d:%02d" "$m" "$s"
    else
        printf "%02d:%02d:%02d" "$h" "$m" "$s"
    fi
}

# Generate captions for the YouTube video description
# and instructions for the ffmpeg concat demuxer
yt_desc="$mov_path/yt-desc.txt"
echo "Routes:" > "$yt_desc"

t_prev=0
chapter=1
truncate -s 0 "$mov_path"/concat.txt

find "$mov_path" -name '*.mp4' -print0 | sort -zV \
    | while IFS= read -r -d '' line; do
        t_len=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$line")
        t_curr=$(echo "$t_prev + $t_len" | bc)
        echo "$(fmt_time $t_prev)-$(fmt_time $t_curr) $(basename "$line" .mp4)" \
            >> "$yt_desc"
        echo "chapter $chapter $t_prev $t_curr" >> "$mov_path"/concat.txt
        echo "file '$line'" >> "$mov_path"/concat.txt
        t_prev="$t_curr"
        chapter=$((chapter + 1))
    done

# Concatenate all route videos into one
ffmpeg -f concat -safe 0 -i "$mov_path/concat.txt" \
       -c copy -movflags faststart \
       -hide_banner \
       -y "$final_mp4"
