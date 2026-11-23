"""quick views: python3 views.py out.png [pose json] [yaws]"""
import sys, json, animtools as A
from PIL import Image
out = sys.argv[1]; pose = json.loads(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else {}
yaws = [float(y) for y in (sys.argv[3] if len(sys.argv) > 3 else '20,90,160,250').split(',')]
an = {'name': 'pose', 'bones': {b: {k: [(0, v)] for k, v in ch.items()} for b, ch in pose.items()}}
ims = [Image.open(A.sheet(an, [0], f'/tmp/v_{i}.png', yaw=y, size=(420, 560), scale=5.0, oy=-22)) for i, y in enumerate(yaws)]
o = Image.new('RGB', (420 * len(ims), 560))
for i, im in enumerate(ims): o.paste(im, (420 * i, 0))
o.save(out)
