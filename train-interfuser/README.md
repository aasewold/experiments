# Training InterFuser on custom data

1. `python create_dataset.py <DATETIME>`
    - This will copy the dataset from IDUN to naplab, untar and convert it to the correct format.
2. `./run.sh <DATASET_PATH>`
    - This will run the training script on the dataset created from the step above.
