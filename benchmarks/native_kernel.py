import sys
n=int(sys.argv[1]); i=0; x=1
while i<n:
    x=(x*17+i)%1000003
    i=i+1
print(x)
