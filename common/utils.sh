#!/bin/bash

run_in_screen() {
    screen -S "$1" -- \
        sh -c "
            echo 'Running in SCREEN - Press Ctrl+A then Ctrl+D to detach'
            $2
            echo 'Still running in SCREEN - Press Ctrl+D to exit'
            exec bash
        "
}
