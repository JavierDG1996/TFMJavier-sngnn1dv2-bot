import sys
import pickle

if len(sys.argv)!=2:
    print('Please, specify a .db file')
    exit()

with open(sys.argv[1], 'rb') as fd:
    data = pickle.load(fd)

    #for k,v in data.items():
    #    print (k, v)
    #print()

    for k, v in data['users'].items():
        print('\n')
        print(str(k)+' ')#+data['users'][k].uname)
        for s, v in data['users'][k].input.items():
            print(s, end='(')
            c = '.'
            if s in data['files']['main']:
                c = '+'
            if s in data['files']['basic']:
                c = '*'
            print(c, end=') ')
            print(v, end=' ')


    print('\n\n')
    for k, v in data['users'].items():
        print(k, data['users'][k].uname, len(v.input))



