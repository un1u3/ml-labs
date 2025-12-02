with open('input.txt','r') as f:
    text = f.read()

print("length of dataset in chars",len(text))

# let's look at the first 1000 chars
print(text[:1000])

chars = sorted(list(set(text)))
vocab_size = len(chars)
print(''.join(chars))
print(vocab_size)
