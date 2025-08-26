import random

names = []
while True: # 1
    inputStr = input("input a name or leave empty to exit\n> ")
    if inputStr == "quit" or inputStr == "": break
    names.append(inputStr)

names = list(set(names)) # 4

for name in names: print(name) # 2

randindex = random.randint(0,len(names)-1) #3
print(names[randindex], "is our lucky winner")
