import json, ast, sys
path = r"C:/GitHub/promptukit/notebooks/promptukit_colab_demo.ipynb"
with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)
errors = False
for idx, cell in enumerate(nb.get('cells', []), start=1):
    if cell.get('cell_type') != 'code':
        continue
    src_lines = cell.get('source', [])
    code = "\n".join(src_lines)
    filtered_lines = [ln for ln in code.splitlines() if not ln.strip().startswith(("!", "%", "%%"))]
    filtered = "\n".join(filtered_lines)
    if not filtered.strip():
        print(f"Cell {idx}: (empty after filtering)")
        continue
    try:
        ast.parse(filtered)
        print(f"Cell {idx}: OK")
    except SyntaxError as e:
        errors = True
        print(f"Cell {idx}: SyntaxError: {e}")
        print("Filtered code:")
        print(filtered)
if errors:
    sys.exit(2)
print("All checked cells OK")
