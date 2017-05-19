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

import os

from json.decoder import JSONDecodeError

import lxml.html
import numpy as np
import pandas as pd
import requests


URL = 'http://tappedout.net/api/inventory/{owner:}/board/'
MTG_JSON = 'https://mtgjson.com/json/AllCards.json'
FIELDNAMES = [
    'Name',
    'Edition',
    'Qty',
    'Foil',
]
FNAME = os.path.join(os.sep, 'tmp', 'mtg_inventory.csv')


class MtgError(Exception):
    """simple error"""
    pass


def main(url=URL, owner='ndlambo', fname=FNAME):
    """main function"""
    inventory = pd.DataFrame(get_inventory(url, owner))
    inventory.name = inventory.name.str.replace('/', '//')
    inventory = inventory.rename(columns={
        'name': 'Name',
        'tla': 'Edition',
        'qty': 'Qty',
    })
    inventory.loc[:, 'Foil'] = np.where(inventory.foil.notnull(), 'Yes', 'No')
    inventory[FIELDNAMES].to_csv(fname, index=False)
    print('wrote file {}'.format(fname))


def get_inventory(url=URL, owner='ndlambo', pagelength=500):
    """simple inventory json getter"""
    inventory = []
    params = {
        'length': pagelength,
        'start': 0,
    }
    while True:
        resp = requests.get(url.format(owner=owner), params=params)
        try:
            j = resp.json()
        except JSONDecodeError:
            print(resp.status_code)
            raise
        tot = None
        if j['data']:
            tot = tot or j['data'][0]['amount']['pk']
            inventory += j['data']
            params['start'] += pagelength
            print('collected {} records so far'.format(len(inventory)))
        else:
            break

    # do some parsing of the html elements returned (because we can't just get
    # names, I guess)
    # also, join in the mtgjson data (for cmc, mainly)
    j = requests.get(MTG_JSON).json()

    for record in inventory:
        record['qty'] = record['amount']['qty']
        carddetails = lxml.html.fromstring(record['card']).find('.//a').attrib
        record.update({
            k.replace('data-', ''): v
            for (k, v) in carddetails.items()
            if k.startswith('data-')
        })
        record.update(record['edit'])
        price = lxml.html.fromstring(record['market_price']).text_content()
        try:
            record['px'] = float(price)
        except:
            record['px'] = None

        try:
            record.update(j[record['name']])
        except:
            pass

    return inventory


def binder_summary(url=URL, owner='ndlambo', bulkthresh=0.30, mainthresh=1.00):
    """break things down as if they're in a binder"""
    keepkeys = ['name', 'qty', 'foil', 'px', 'tla']
    inventory = pd.DataFrame(get_inventory(url, owner))[keepkeys]

    # join in mtgjson info

    # replace the island notion
    inventory.is_land.fillna(False, inplace=True)

    # only items we hold, not items in a deck (etc)
    inventory = inventory[inventory.qty.notnull()]

    # for prices, give everything the average, and then overwrite where foil
    inventory.loc[:, 'price'] = inventory.tcg_avg_price
    inventory.loc[inventory.foil, 'price'] = inventory[inventory.foil].tcg_foil_price

    # subset based on whether or not they meet my thresholds
    inventory.loc[:, 'card_value'] = pd.cut(
        inventory.price,
        right=False,
        bins=[0, bulkthresh, mainthresh, float('inf')],
        labels=['small', 'medium', 'large']
    )
    inventory.card_value = inventory.card_value.cat.reorder_categories(
        ['large', 'medium', 'small'],
        ordered=True
    )

    # drop small and sort the results in "binder order"
    inventory = inventory[inventory.card_value != 'small']

    # ordering for effective cost is tough
    inventory.effective_cost = inventory.effective_cost.astype('category')

    def category_order(cat):
        """order within the binder"""
        return (
            cat.strip().count(' '),
        ) + tuple(
            color not in cat.lower()
            for color in ['white', 'blue', 'black', 'red', 'green']
        )

    orderedcats = sorted(
        inventory.effective_cost.cat.categories,
        key=category_order
    )
    inventory.effective_cost = inventory.effective_cost.cat.reorder_categories(
        orderedcats, ordered=True
    )

    # ditto for type
    inventory.replace(
        {
            'type': {
                'Artifact Land': 'Land',
                'Basic Land': 'Land',
                'Enchantment ': '',
                'Tribal ': '',
                'Legendary ': '',
                'Legendary Enchantment ': '',
            },
        },
        inplace=True,
        regex=True
    )
    inventory.type = inventory.type.astype('category')
    inventory.type = inventory.type.cat.reorder_categories(
        [
            'Planeswalker',
            'Creature',
            'Enchantment',
            'Sorcery',
            'Instant',
            'Artifact',
            'Artifact Creature',
            'Land',
        ],
        ordered=True
    )

    inventory = inventory.sort_values(
        by=[
            'card_value', 'is_land', 'effective_cost', 'type', 'flat_cost',
            'power_toughness', 'name', 'foil'
        ]
    )

    inventory = inventory.drop(
        labels=['tcg_avg_price', 'tcg_foil_price', 'is_land'],
        axis=1
    )

    return inventory


if __name__ == '__main__':
    main()
