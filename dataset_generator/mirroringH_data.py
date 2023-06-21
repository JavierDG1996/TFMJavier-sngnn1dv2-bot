import json
import os
import sys
import math

if len(sys.argv) < 2:
	print("USAGE: python3 mirroring_data.py directory_path")
	exit()

directory_path = sys.argv[1]

for filename in os.listdir(directory_path):
	if not filename.endswith('.json'):
		continue

	save = "mH_"+filename
	if 'mH' in filename:
		continue

	# Read JSON data into the datastore variable
	if filename:
	    with open(directory_path+'/'+filename, 'r') as f:
	        datastore = json.load(f)
	        f.close()

	for data in datastore:
		data['command'][0] = -data['command'][0]

		for i in range(len(data['goal'])):
			data['goal'][i]['x'] = -data['goal'][i]['x']
			data['goal'][i]['y'] = -data['goal'][i]['y']

		for i in range(len(data['objects'])):
			data['objects'][i]['a'] = math.atan2(-math.sin(data['objects'][i]['a']), -math.cos(data['objects'][i]['a']))

			data['objects'][i]['x'] = -data['objects'][i]['x']
			data['objects'][i]['y'] = -data['objects'][i]['y']
			data['objects'][i]['vx'] = -data['objects'][i]['vx']
			data['objects'][i]['vy'] = -data['objects'][i]['vy']

		for i in range(len(data['people'])):
			data['people'][i]['a'] = math.atan2(-math.sin(data['people'][i]['a']), -math.cos(data['people'][i]['a']))


			data['people'][i]['x'] = -data['people'][i]['x']
			data['people'][i]['y'] = -data['people'][i]['y']
			data['people'][i]['vx'] = -data['people'][i]['vx']
			data['people'][i]['vy'] = -data['people'][i]['vy']

		for i in range(len(data['walls'])):
			data['walls'][i]['x1'] = -data['walls'][i]['x1']
			data['walls'][i]['y1'] = -data['walls'][i]['y1']
			data['walls'][i]['x2'] = -data['walls'][i]['x2']
			data['walls'][i]['y2'] = -data['walls'][i]['y2']

	with open(directory_path+'/'+save, 'w') as outfile: 
	    json.dump(datastore, outfile, indent=4, sort_keys=True) 
	    outfile.close()
