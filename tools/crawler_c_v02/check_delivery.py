"""Check portable source references and all eight delivered preview images."""
from pathlib import Path
import json
import bpy
import numpy as np

OUT = Path(__file__).resolve().parents[2] / "assets/model/enemy_crawler_c_v02"
bpy.ops.wm.open_mainfile(filepath=str(OUT / "CrawlerC_Review.blend"))
report = {"source_images": [], "previews": [], "failures": []}
for im in bpy.data.images:
    if not im.filepath:
        continue
    resolved = Path(bpy.path.abspath(im.filepath)).resolve()
    ok = resolved.is_relative_to(OUT.resolve()) and resolved.is_file()
    if not ok:
        report["failures"].append("Missing or external source image: " + str(resolved))
    report["source_images"].append({"path": im.filepath, "present_in_delivery": ok})
expected = ["01_ThreeQuarter", "02_Front", "03_Side", "04_HeadDetail", "05_Attack", "06_LightFlinch", "07_Death", "08_WallCrawl"]
for name in expected:
    path = OUT / "previews" / (name + ".png")
    im = bpy.data.images.load(str(path), check_existing=False)
    pixels = np.empty(len(im.pixels), dtype=np.float32)
    im.pixels.foreach_get(pixels)
    contrast = float(pixels.reshape(-1, 4)[:, :3].std())
    if contrast < .025:
        report["failures"].append(name + ": blank preview")
    report["previews"].append({"name": name, "size": list(im.size), "contrast": contrast})
(OUT / "validation_delivery.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("DELIVERY failures=" + str(len(report["failures"])), flush=True)
if report["failures"]:
    raise RuntimeError(report["failures"])
