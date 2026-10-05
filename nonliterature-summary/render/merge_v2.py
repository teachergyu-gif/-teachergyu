"""Merge rewritten one_line/structure (data2/*.json) into data/*.json by passage title."""
import json, os, sys
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
src = sys.argv[1]
for f in sorted(os.listdir(src)):
    if not f.endswith(".json"):
        continue
    new = {p["title"]: p for p in json.load(open(os.path.join(src, f), encoding="utf-8"))["passages"]}
    path = os.path.join(D, f)
    d = json.load(open(path, encoding="utf-8"))
    for p in d["passages"]:
        n = new.get(p["title"])
        if n:
            p["one_line"], p["structure"] = n["one_line"], n["structure"]
            print(f, p["title"], len(p["one_line"]), sum(len(s["content"]) for s in p["structure"]))
        else:
            print(f, p["title"], "NOT FOUND in rewrite")
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
