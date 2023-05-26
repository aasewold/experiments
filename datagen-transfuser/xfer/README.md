Used to continuously transfer data from Idun to the local machine, deleting the data on Idun after transfer.
This is due to the file quotas on Idun, which may be too small to store all the data generated.

Usage:
```bash
./run.sh <run>
```
where `run` is the name of a subfolder of `work/thesis/datagen/output` on Idun.
Note that you may have to modify the file paths in `xfer.py:parse_args` to match your setup.
