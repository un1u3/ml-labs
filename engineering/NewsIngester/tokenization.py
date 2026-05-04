from transformers import AutoTokenizer


tokenizer = AutoTokenizer.from_pretrained('google-bert/bert-base-cased')
print(tokenizer)