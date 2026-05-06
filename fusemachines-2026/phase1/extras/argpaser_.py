# learning arg parser convering csv to json 

import argparse
import json 
import csv 

parser = argparse.ArgumentParser(description="CSV to json")
parser.add_argument('input',help= "ENter CSV file")
parser.add_argument('--output','--op', default='output.json')


args = parser.parse_args()

with open(args.input,'r') as csvfile:
    reader = csv.DictReader(csvfile)
    data = list(reader)

with open(args.output,'w') as jsonfile:
    json.dump(data, jsonfile, indent=2)

print("COnveredCSVto  json")
