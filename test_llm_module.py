from script_parser import _extract_entities_with_llm

with open("/Users/alexkasama/Downloads/the_last_shelter_wolf_snow_shelter_episode.md", "r") as f:
    text = f.read()

print("Running extraction...")
res = _extract_entities_with_llm(text)
print("Result:")
print(res)
