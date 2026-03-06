"""
Restructure the 1P Ads in Ad Server tech spec Google Doc.

Applies all post-restructure passes in order:
  1. Fix section divider headers (replaceAllText)
  2. Apply heading styles
  3. Insert images from original doc
  4. Remove blank paragraphs
  5. Apply bold labels
  6. Convert fake lists to real bullets
  7. Fix garbled text from lettered-list prefix deletion

Run individual steps with --step <name> or run all with no arguments.

Usage:
  uv run scripts/restructure.py
  uv run scripts/restructure.py --step fix-headers
  uv run scripts/restructure.py --step apply-headings
  uv run scripts/restructure.py --step insert-images
  uv run scripts/restructure.py --step remove-blanks
  uv run scripts/restructure.py --step apply-bold
  uv run scripts/restructure.py --step convert-lists
  uv run scripts/restructure.py --step fix-garbled
"""
import sys
import json
from gdocs.pipeline import GDocsPipeline
from gdocs.client import fetch_doc
from gdocs.transforms import apply_heading, insert_image
from gdocs.models import get_image_info

DOC_ID = "1VvNIj9zfRyenLKdOVnj4NnHppJU0H91RBZRjJQjZCf4"
ORIG_DOC_ID = "1isHvO9AEJzlZ9j0dq_JvHhIJMvyZdsoPK-OYBm0KFTI"

# Ranges to skip when converting fake lists (TOC + standalone section refs)
SKIP_RANGES = {
    (3191, 3711),   # How to Read list
    (8113, 8137),
    (10806, 10836),
    (14443, 14467),
    (16814, 16841),
    (18418, 18443),
    (28506, 28527),
    (28887, 28925),
    (29830, 29861),
    (30120, 30137),
    (30550, 30567),
    (31065, 31090),
    (32040, 32067),
    (32281, 32300),
    (32804, 32817),
}

# Garbled strings from lettered-list prefix deletion
GARBLED_REPLACEMENTS = [
    ("M  aaps slot type to ad type", "Maps slot type to ad type"),
    ("F  betches all candidate ads.", "Fetches all candidate ads."),
    ("A  cpplies SSP Guardrails.", "Applies SSP Guardrails."),
    ("A  dpplies publisher whitelist guardrails.", "Applies publisher whitelist guardrails."),
    ("A  epplies merchant segmentation check.", "Applies merchant segmentation check."),
    ("A  fpplies other guardrails and ad-level rules.", "Applies other guardrails and ad-level rules."),
    ("P  gerforms bulk customer segmentation check", "Performs bulk customer segmentation check"),
    ("C  halls Offers Engine /geteligibleoffers", "Calls Offers Engine /geteligibleoffers"),
    ("O  iffers Engine runs transaction rules", "Offers Engine runs transaction rules"),
    ("A  jd Server maps filtered ads to slots.", "Ad Server maps filtered ads to slots."),
    ("A  kd Server ranks ads per slot.", "Ad Server ranks ads per slot."),
    ("C  aalls Ad Server with ad_id", "Calls Ad Server with ad_id"),
    ("A  bd Server fetches reward entity", "Ad Server fetches reward entity"),
    ("A  cd Server returns reward + RMP", "Ad Server returns reward + RMP"),
    ("O  dffers Engine sends notification to customer.", "Offers Engine sends notification to customer."),
    ("O  affers Engine re-fetches reward from Ad Server", "Offers Engine re-fetches reward from Ad Server"),
    ("A  bd Server calls RMP using the existing order ID.", "Ad Server calls RMP using the existing order ID."),
    ("O  cffers Engine retries notification delivery.", "Offers Engine retries notification delivery."),
]

# Heading style assignments — verified indices from the original session
HEADINGS = [
    (1, 33, "TITLE"),
    (121, 138, "HEADING_1"),
    (1583, 1611, "HEADING_1"),
    (5854, 5894, "HEADING_1"),
    (8567, 8613, "HEADING_1"),
    (10608, 10648, "HEADING_1"),
    (13020, 13055, "HEADING_1"),
    (14646, 14687, "HEADING_1"),
    (24789, 24826, "HEADING_1"),
    (25168, 25215, "HEADING_1"),
    (26135, 26167, "HEADING_1"),
    (26438, 26466, "HEADING_1"),
    (26880, 26913, "HEADING_1"),
    (27404, 27445, "HEADING_1"),
    (28394, 28437, "HEADING_1"),
    (28655, 28690, "HEADING_1"),
    (29196, 29213, "HEADING_1"),
    (139, 157, "HEADING_2"),
    (843, 869, "HEADING_2"),
    (1612, 1621, "HEADING_2"),
    (5895, 5919, "HEADING_2"),
    (5920, 5954, "HEADING_3"),
    (6730, 6763, "HEADING_3"),
    (7270, 7290, "HEADING_3"),
    (8614, 8644, "HEADING_2"),
    (8645, 8655, "HEADING_3"),
    (9424, 9434, "HEADING_3"),
    (9776, 9790, "HEADING_3"),
    (9906, 9949, "HEADING_3"),
    (10099, 10115, "HEADING_3"),
    (10547, 10557, "HEADING_3"),
    (10649, 10673, "HEADING_2"),
    (10829, 10850, "HEADING_3"),
    (11029, 11066, "HEADING_3"),
    (11589, 11628, "HEADING_3"),
    (11908, 11954, "HEADING_3"),
    (12151, 12183, "HEADING_3"),
    (12520, 12561, "HEADING_3"),
    (12729, 12762, "HEADING_3"),
    (13056, 13083, "HEADING_2"),
    (13084, 13112, "HEADING_3"),
    (14369, 14392, "HEADING_3"),
    (14688, 14713, "HEADING_2"),
    (14714, 14740, "HEADING_3"),
    (14801, 14822, "HEADING_3"),
    (14823, 14854, "HEADING_3"),
    (16492, 16540, "HEADING_3"),
    (16738, 16760, "HEADING_3"),
    (17376, 17407, "HEADING_3"),
    (18005, 18051, "HEADING_3"),
    (18052, 18087, "HEADING_3"),
    (18917, 18942, "HEADING_3"),
    (20086, 20114, "HEADING_3"),
    (21173, 21209, "HEADING_3"),
    (21723, 21752, "HEADING_3"),
    (22119, 22147, "HEADING_3"),
    (22653, 22680, "HEADING_3"),
    (23193, 23232, "HEADING_3"),
    (23993, 24024, "HEADING_3"),
    (24447, 24472, "HEADING_3"),
    (24827, 24848, "HEADING_2"),
    (24849, 24867, "HEADING_3"),
    (24914, 24946, "HEADING_3"),
    (25000, 25028, "HEADING_3"),
    (25216, 25254, "HEADING_2"),
    (25255, 25271, "HEADING_3"),
    (25458, 25475, "HEADING_3"),
    (25483, 25496, "HEADING_3"),
    (25783, 25798, "HEADING_3"),
    (25960, 25976, "HEADING_3"),
    (26103, 26127, "HEADING_3"),
    (26168, 26199, "HEADING_2"),
    (26200, 26226, "HEADING_3"),
    (26280, 26308, "HEADING_3"),
    (26467, 26484, "HEADING_2"),
    (26485, 26501, "HEADING_3"),
    (26712, 26729, "HEADING_3"),
    (26801, 26833, "HEADING_3"),
    (26914, 26931, "HEADING_2"),
    (26932, 26970, "HEADING_3"),
    (27263, 27291, "HEADING_3"),
    (27334, 27353, "HEADING_3"),
    (27446, 27471, "HEADING_2"),
    (27472, 27485, "HEADING_3"),
    (27874, 27886, "HEADING_3"),
    (28315, 28327, "HEADING_3"),
    (28438, 28465, "HEADING_2"),
    (28691, 28710, "HEADING_2"),
    (29214, 29227, "HEADING_2"),
]

# Section divider renames
HEADER_REPLACEMENTS = [
    ("――― OVERVIEW ―――", "Overview"),
    ("――― SECTION 1: GLOSSARY ―――", "Section 1: Glossary"),
    ("――― SECTION 2: CONTEXT & BACKGROUND ―――", "Section 2: Context & Background"),
    ("――― SECTION 3: SCOPE, GOALS & CONSTRAINTS ―――", "Section 3: Scope, Goals & Constraints"),
    ("――― SECTION 4: ARCHITECTURAL TENETS ―――", "Section 4: Architectural Tenets"),
    ("――― SECTION 5: SYSTEM OVERVIEW ―――", "Section 5: System Overview & Roles"),
    ("――― SECTION 6: PROPOSED ARCHITECTURE ―――", "Section 6: Proposed Architecture"),
    ("――― SECTION 7: APIS & DATA MODEL ―――", "Section 7: APIs & Data Model"),
    ("――― SECTION 8: NON-FUNCTIONAL REQUIREMENTS ―――", "Section 8: Non-Functional Requirements (NFRs)"),
    ("――― SECTION 9: DEPENDENCIES ―――", "Section 9: Feature Dependencies & SLAs"),
    ("――― SECTION 10: TESTING ―――", "Section 10: Testing Plan"),
    ("――― SECTION 11: GO-LIVE PLAN ―――", "Section 11: Go-Live Plan"),
    ("――― SECTION 12: MONITORING & LOGGING ―――", "Section 12: Monitoring & Logging"),
    ("――― SECTION 13: MILESTONES & TIMELINES ―――", "Section 13: Milestones & Timelines"),
    ("――― SECTION 14: OPEN QUESTIONS ―――", "Section 14: Open Questions"),
    ("――― APPENDIX ―――", "Section 15: Appendix"),
]

# Image insertions — verified indices from original session
# Format: (insert_at_index, obj_id, label)
IMAGE_INSERTIONS = [
    (8429,  "kix.jgg4r08z8ngq", "Current Architecture Diagram"),
    (8840,  "kix.jax6hj4tgod0", "Non-PBO Force-Fit Flow"),
    (16827, "kix.r9m6es4d68wf", "Architecture Overview HLD"),
    (16827, "kix.t9wnsw7wnt49", "Architecture Overview Detail"),
    (16767, "kix.ih0qvsyzsth0", "HLD Diagram"),
    (16881, "kix.fev46icgic3v", "Checkout Ad Serving Flow"),
    (20513, "kix.cy8lvp3j9d37", "Split Budget Tracking Diagram"),
    (21599, "kix.tovierv7funb", "Merchant Segments Lazy Tracking"),
    (21864, "kix.56h14wgw3110", "Guardrail Rules Rampup"),
    (21864, "kix.o0ibjvi3elqt", "Guardrail Rules Discovery"),
    (21864, "kix.8cyifua0w7kt", "Guardrail Rules Offer Validate"),
    (22906, "kix.kz1jqi9asvfe", "Customer Segmentation Data Flow"),
    (22906, "kix.y9vrpinu8p20", "Segment Ownership Matrix"),
    (24787, "kix.v95l8yi096oa", "Gratification Flow"),
    (25464, "kix.o4eyj2kjsh4f", "Ads Validation Approach 2"),
    (25464, "kix.c08rwgkml8s0", "Checkout Compliance Flow"),
    (25464, "kix.23bnfq6ogaxs", "Hybrid Approach Flow"),
    (26969, "kix.pvnlln1qpyhx", "Data Model ERD"),
]


def step_fix_headers(p: GDocsPipeline):
    print("Step: fix-headers — renaming section dividers")
    from gdocs.transforms import replace_text
    reqs = [replace_text(old, new) for old, new in HEADER_REPLACEMENTS]
    p.apply(reqs)
    print(f"  {len(reqs)} replacements applied.")


def step_apply_headings(p: GDocsPipeline):
    print("Step: apply-headings — applying paragraph styles")
    reqs = [apply_heading(s, e, style) for s, e, style in HEADINGS]
    p.apply(reqs)
    print(f"  {len(reqs)} heading styles applied.")


def step_insert_images(p: GDocsPipeline):
    print("Step: insert-images — fetching original doc and inserting images")
    orig_doc = fetch_doc(ORIG_DOC_ID)
    inline_objects = orig_doc.get("inlineObjects", {})
    insertions = sorted(IMAGE_INSERTIONS, key=lambda x: x[0], reverse=True)
    reqs = []
    for idx, obj_id, label in insertions:
        uri, w, h = get_image_info(inline_objects, obj_id)
        if not uri:
            print(f"  WARNING: no URI for {obj_id} ({label}), skipping")
            continue
        reqs.append(insert_image(idx, uri, w, h))
        print(f"  {label}: idx={idx}")
    p.apply(reqs)
    print(f"  {len(reqs)} images inserted.")


def step_remove_blanks(p: GDocsPipeline):
    print("Step: remove-blanks — removing blank paragraphs")
    p.remove_blank_paragraphs()
    print("  Done.")


def step_apply_bold(p: GDocsPipeline):
    print("Step: apply-bold — applying bold labels")
    p.apply_bold()
    print("  Done.")


def step_convert_lists(p: GDocsPipeline):
    print("Step: convert-lists — converting fake lists to bullets")
    p.convert_fake_lists(skip_ranges=SKIP_RANGES)
    print("  Done.")


def step_fix_garbled(p: GDocsPipeline):
    print("Step: fix-garbled — fixing garbled text from lettered-list deletion")
    p.fix_garbled_text(GARBLED_REPLACEMENTS)
    print(f"  {len(GARBLED_REPLACEMENTS)} replacements applied.")


STEPS = {
    "fix-headers":    step_fix_headers,
    "apply-headings": step_apply_headings,
    "insert-images":  step_insert_images,
    "remove-blanks":  step_remove_blanks,
    "apply-bold":     step_apply_bold,
    "convert-lists":  step_convert_lists,
    "fix-garbled":    step_fix_garbled,
}

ALL_STEPS = [
    "fix-headers",
    "apply-headings",
    "insert-images",
    "remove-blanks",
    "apply-bold",
    "convert-lists",
    "fix-garbled",
]


def main():
    args = sys.argv[1:]
    if "--step" in args:
        idx = args.index("--step")
        name = args[idx + 1]
        if name not in STEPS:
            print(f"Unknown step: {name!r}. Valid steps: {', '.join(ALL_STEPS)}")
            sys.exit(1)
        to_run = [name]
    else:
        to_run = ALL_STEPS

    print(f"Initialising pipeline for doc {DOC_ID}")
    p = GDocsPipeline(DOC_ID)

    for name in to_run:
        STEPS[name](p)

    print("\nAll done.")


if __name__ == "__main__":
    main()
