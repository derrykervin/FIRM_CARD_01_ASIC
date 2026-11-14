"""Use the exact info.yaml source list for RTL tests and GDS, without separate stale lists."""
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
text=(root/'info.yaml').read_text().split('  source_files:\n',1)[1].split('pinout:',1)[0]
names=re.findall(r'    - "([^"]+)"',text)
assert names and len(set(names))==len(names)
assert all(not Path(n).is_absolute()and '..'not in Path(n).parts and(root/'src'/n).is_file()for n in names)
print(' '.join(names))
