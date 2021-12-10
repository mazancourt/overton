# Converts a categorization table to a JSON file
import json
import sys

import pandas as pd


def csv_to_json(csv_file, json_file):
    cat = {}
    df = pd.read_csv(csv_file)
    for colname in df.columns[1:]:
        cat[colname] = []
        for item in df[colname]:
            if not pd.isna(item):
                cat[colname].append(item)
    with open(json_file, "w", encoding="utf8") as j:
        json.dump(cat, j, indent=4)


# SYNOPSIS: cat2json.py categories.csv classification.json
if __name__ == '__main__':
    csv_to_json(sys.argv[1], sys.argv[2])
