
def longest_consecutive(nums):
    seen=set(nums)
    max_length=0
    for i in seen:
        current=i
        length=1
        while current-1 in seen:
            current=current-1
            length+=1
            max_length = max(max_length,length)
    print(max_length)



print(longest_consecutive([100,4,200,1,3,2]))  # 4 (1,2,3,4)
print(longest_consecutive([0,3,7,2,5,8,4,6,0,1]))  # 9

