import os
key = input("Paste your Anthropic API key and press Enter: ")
key = key.strip()
with open(".env", "w") as f:
    f.write("ANTHROPIC_API_KEY=" + key + "\n")
print("Done! Length:", len(key))
