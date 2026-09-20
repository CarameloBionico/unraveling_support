"""Package current prototypes without environments or generic audit G-code."""
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent
files=[root/name for name in ('README.md','README_v1.md','generate.py','generate_v2.py',
    'validate_slicing.py','validate_v2.py','requirements.txt','index.html','v1.html','bundle_v2.py')]
for folder in ('output','output_v2'):
    directory=root/folder
    files+=list(directory.glob('*.stl'))
    files+=[directory/name for name in ('preview-data.js','config.json','validation.json')]
    files+=list((directory/'audit').glob('*validation.json'))
destination=root/'output_v2'/'prototipo_02.zip'
with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path,path.relative_to(root))
print(f'{len(files)} files packaged: {destination} ({destination.stat().st_size} bytes)')
