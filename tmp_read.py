import pathlib, sys
path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding='utf-8')
out = pathlib.Path('stub_fix_summary.json')
out.write_text(text[:8000], encoding='utf-8')
