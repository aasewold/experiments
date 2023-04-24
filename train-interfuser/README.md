# Training InterFuser on custom data

In order to train InterFuser on custom data generated on IDUN, we first need to sync and convert the data. This is done using the CLI defined in `dataset.py` like this:
1. `python dataset.py sync <DATASET_DATETIME>`
    - This will copy the dataset from IDUN to naplab. See `python dataset.py sync --help` for detailed usage.
2. `python dataset.py extract <DATASET_PATH>`
    - This will untar and convert the dataset to the correct format.
3. `python dataset.py rm-blocked-data <DATASET_PATH>`
    - This will remove data from the dataset where ego is blocked over many frames.
4. `python dataset.py create-index <DATASET_PATH>`
    - This will create an index file for the dataset, used during training.


When these steps are done you can start training:
- `./run.sh <DATASET_PATH>`
    - This will run the training script on the dataset created from the step above.
