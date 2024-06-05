import pickle
import os, sys
from sklearn import metrics as sk
import pandas as pd


labels = pickle.load(open(sys.argv[1], 'rb'), fix_imports=True)

users = labels['users'].keys()

print(users)

samples = []

for user in users:
	l_user = labels['users'][user].input.keys()
	new_samples = [s for s in l_user if s not in samples and not s.endswith('D')]
	samples += new_samples

final_samples = [s.split('/')[-1].split('.')[0] for s in samples]

# final_samples.sort()

data = {}

# {'first_column':  ['first_value', 'second_value', ...],
#         'second_column': ['first_value', 'second_value', ...],
#          ....
#         }

for user in users:
	data[user] = []
	for s, fs in zip(samples, final_samples):
		if s in labels['users'][user].input.keys():
			data[user].append(labels['users'][user].input[s][0])
		else:
			data[user].append(-1)


# for s, fs in zip(samples, final_samples):
# 	data[fs] = []
# 	for user in users:
# 		if s in labels['users'][user].input.keys():
# 			data[fs].append(labels['users'][user].input[s][0])
# 		else:
# 			data[fs].append(-1)
	
df = pd.DataFrame(data, index = final_samples)
print(df)
# print(len(final_samples))
exit()

# print(labels)


for user1 in users:
	print(user1, '-', len(labels['users'][user1].input.keys()))
	l_user1 = labels['users'][user1].input.keys()
	for user2 in users:
		scores1_Q1 = []
		scores2_Q1 = []
		scores1_Q2 = []
		scores2_Q2 = []
		scores1_Q3 = []
		scores2_Q3 = []
		l_user2 = labels['users'][user2].input.keys()
		for l in l_user1:
			if user1 == user2:
				l2 = l + 'D'
				if l2 in l_user1:
					scores1_Q1.append(labels['users'][user1].input[l][0])
					scores2_Q1.append(labels['users'][user1].input[l2][0])
					# scores1_Q2.append(labels['users'][user1].input[l][1])
					# scores2_Q2.append(labels['users'][user1].input[l2][1])
					# scores1_Q3.append(labels['users'][user1].input[l][2])
					# scores2_Q3.append(labels['users'][user1].input[l2][2])
			else:
				if l in l_user2:
					scores1_Q1.append(labels['users'][user1].input[l][0])
					scores2_Q1.append(labels['users'][user2].input[l][0])
					# scores1_Q2.append(labels['users'][user1].input[l][1])
					# scores2_Q2.append(labels['users'][user2].input[l][1])
					# scores1_Q3.append(labels['users'][user1].input[l][2])
					# scores2_Q3.append(labels['users'][user2].input[l][2])


		if len(scores1_Q1)>0: #100:
			kcoeff1 = sk.cohen_kappa_score(scores1_Q1, scores2_Q1, labels=list(range(101)), weights='linear')
			kcoeff2 = 0#sk.cohen_kappa_score(scores1_Q2, scores2_Q2, labels=list(range(101)), weights='linear')
			kcoeff3 = 0#sk.cohen_kappa_score(scores1_Q3, scores2_Q3, labels=list(range(101)), weights='linear')			
			print(user1, "-", user2, "Q1:", kcoeff1, "Q2:", kcoeff2, "Q3:", kcoeff3, len(scores1_Q1))

