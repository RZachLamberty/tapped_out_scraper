#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module: temp.py
Author: zlamberty
Created: 2016-02-09

Description:


Usage:
<usage>

"""

import csv
import os
import numpy as np
import pandas as pd
import requests


URL = 'http://tappedout.net/api/collection-board/?owner={owner:}&type=inventory&page={page:}'
FIELDNAMES = [
    'Name',
    'Edition',
    'Qty',
    'Foil',
]
FNAME = os.path.join(os.sep, 'tmp', 'mtg_inventory.csv')


class MtgError(Exception):
    pass


def main(url=URL, owner='ndlambo', fname=FNAME):
    inventory = pd.DataFrame(get_inventory(url, owner))
    inventory.name = inventory.name.str.replace('/', '//')
    inventory = inventory.rename(columns={
        'name': 'Name',
        'tla': 'Edition',
        'qty': 'Qty',
    })
    inventory.loc[:, 'Foil'] = np.where(inventory.foil, 'Yes', 'No')
    inventory[FIELDNAMES].to_csv(fname, index=False)


def get_inventory(url=URL, owner='ndlambo'):
    inventory = []
    i = 1
    while True:
        try:
            urlnow = url.format(owner=owner, page=i)
            resp = requests.get(urlnow).json()
            inventory += resp['results']
            i += 1
        except:
            break

    return inventory


if __name__ == '__main__':
    main()
