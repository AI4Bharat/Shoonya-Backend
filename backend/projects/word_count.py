
import re
def no_of_words(string):
    filter1 = [word for word in string.split() if len(word) > 1]
    filter2 = [word for word in filter1 if re.search('[a-zA-Z]', word) != None]
    length = len(filter2)
    return length 


# string =  "hello123 a"
# length = no_of_words(string)
# print(length )