import pickle
import os, sys
import json

if len(sys.argv)<3:
	print(f'USAGE: python3 {sys.argv[0]} bot_database.db unlabelled_data_directory labelled_data_directory')
	exit()

bot_file = sys.argv[1]
unlabelled_dir = sys.argv[2]
labelled_dir = sys.argv[3]

labels = pickle.load(open('bot.db', 'rb'), fix_imports=True)

users = labels['users'].keys()

for user in users:
	files = labels['users'][user].input.keys()
	for fl in files: 
		dataname = fl.split('/')[1].split('.')[0]
		print(dataname)
		if os.path.exists(unlabelled_dir+'/'+dataname+'.json'):
			with open(unlabelled_dir+'/'+dataname+'.json', 'r') as fin:
				unlabelled_data = json.loads(fin.read())
		
			labelled_data = []
			for d in unlabelled_data:
				d['label_Q1'] = labels['users'][user].input[fl][0]
				d['label_Q2'] = labels['users'][user].input[fl][1]
				labelled_data.insert(0, d)

			file_list = [f for f in os.listdir(labelled_dir) if f.startswith(dataname)]
			ind = len(file_list)+1
			with open(labelled_dir+'/'+ dataname+'_L'+str(ind)+'.json', 'w') as fout:
				json.dump(labelled_data, fout, indent=4, sort_keys=True)


