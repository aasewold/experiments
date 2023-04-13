from contextlib import suppress
from src import profile
from src.nap.kia.dataloader import iter_data


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            iter_data()
