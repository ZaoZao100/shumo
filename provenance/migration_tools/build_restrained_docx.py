"""Create an independent DOCX revision by replacing the 24 paper figures."""
from __future__ import annotations

import argparse
import io
import json
import os
import zipfile
from pathlib import Path

from PIL import Image
from lxml import etree as ET


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}


PAPER_FIGURES = [
    "fig_roadmap",
    "fig_att1_profile",
    "fig_load_regime_ridgeline",
    "fig_load_calendar",
    "fig_regime_shape",
    "tikz_feasible_q1",
    "tikz_soc_corridor",
    "fig_q1_dispatch_stack",
    "fig_q1_soc_price",
    "fig_q1_savings_waterfall",
    "fig_eta_sensitivity",
    "fig_predictor_mae_bar",
    "fig_q2_margin_ucurve",
    "tikz_info_set",
    "fig_forecast_same_target",
    "fig_q3_rolling_timeline",
    "fig_q3_cost_decomp",
    "fig_q2_emergency_calendar",
    "fig_q3_interp_check",
    "fig_q4_price_ridgeline",
    "fig_q4_price_hovmoller",
    "fig_q4_fixed_vs_vol",
    "fig_forecast_decay",
    "fig_arch_solver",
]


def dimensions(blob: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(blob)) as image:
        return image.size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_docx", type=Path)
    parser.add_argument("figures_dir", type=Path)
    parser.add_argument("output_docx", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    replacements = {
        index: (name, (args.figures_dir / f"{name}.png").read_bytes())
        for index, name in enumerate(PAPER_FIGURES, 1)
    }
    missing = [name for name in PAPER_FIGURES if not (args.figures_dir / f"{name}.png").exists()]
    if missing:
        raise FileNotFoundError(f"missing revised figures: {missing}")

    with zipfile.ZipFile(args.source_docx) as source:
        source_document_xml = source.read("word/document.xml")
        document = ET.fromstring(source_document_xml)
        rels = ET.fromstring(source.read("word/_rels/document.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pr:Relationship", NS)
        }
        drawings = document.findall(".//w:body//w:drawing", NS)
        if len(drawings) != len(PAPER_FIGURES):
            raise ValueError(f"expected 24 drawings, found {len(drawings)}")

        report_rows: list[dict[str, object]] = []
        target_blobs: dict[str, bytes] = {}
        for index, drawing in enumerate(drawings, 1):
            blip = drawing.find(".//a:blip", NS)
            if blip is None:
                raise ValueError(f"drawing {index} has no embedded image")
            rid = blip.attrib[f"{{{NS['r']}}}embed"]
            target = rel_map[rid]
            member = str(Path("word") / target).replace("\\", "/")
            name, new_blob = replacements[index]
            old_blob = source.read(member)
            old_px = dimensions(old_blob)
            new_px = dimensions(new_blob)

            inline_extent = drawing.find(".//wp:extent", NS)
            if inline_extent is None:
                raise ValueError(f"drawing {index} has no Word extent")
            old_cx = int(inline_extent.attrib["cx"])
            old_cy = int(inline_extent.attrib["cy"])
            source_ratio = new_px[0] / new_px[1]
            frame_ratio = old_cx / old_cy
            if source_ratio >= frame_ratio:
                new_cx = old_cx
                new_cy = round(old_cx / source_ratio)
            else:
                new_cy = old_cy
                new_cx = round(old_cy * source_ratio)
            inline_extent.set("cx", str(new_cx))
            inline_extent.set("cy", str(new_cy))
            for shape_extent in drawing.findall(".//a:xfrm/a:ext", NS):
                shape_extent.set("cx", str(new_cx))
                shape_extent.set("cy", str(new_cy))

            target_blobs[member] = new_blob
            report_rows.append(
                {
                    "figure_number": index,
                    "figure": name,
                    "rid": rid,
                    "member": member,
                    "old_px": old_px,
                    "new_px": new_px,
                    "old_extent_emu": [old_cx, old_cy],
                    "new_extent_emu": [new_cx, new_cy],
                    "fit_within_original_frame": True,
                }
            )

        xml_blob = ET.tostring(
            document,
            encoding="UTF-8",
            xml_declaration=True,
            standalone=True,
        )
        args.output_docx.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output_docx.with_suffix(args.output_docx.suffix + ".tmp")
        with zipfile.ZipFile(temp, "w") as output:
            for info in source.infolist():
                if info.filename == "word/document.xml":
                    blob = xml_blob
                elif info.filename in target_blobs:
                    blob = target_blobs[info.filename]
                else:
                    blob = source.read(info.filename)
                output.writestr(info, blob)
        os.replace(temp, args.output_docx)

    report = {
        "source": str(args.source_docx),
        "output": str(args.output_docx),
        "figure_count": len(report_rows),
        "figures": report_rows,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output_docx), "figure_count": len(report_rows)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
