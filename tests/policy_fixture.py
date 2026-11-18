"""The policy skeleton every fixture policy repeats: one builder.

`scoring_block` returns exactly the `scoring`/`affinity` dict pair the
suites used to hand-write — the calibrated thresholds band and the
affinity factors — with the per-file exponents and top-k passed through,
so each resulting dict is byte-equivalent to the literal it replaced.
Extra keyword arguments land in `scoring` after the thresholds, in
declaration order (the free_share_inheritance shape).
"""


def scoring_block(alpha=1.0, beta=0.0, *, top1_min=0.2, top1_max=0.5,
                  top2_max=0.75, blend_weight=0.6, eligibility_top_k=5,
                  favor_validated=3.0, favor_suspected=2.0,
                  avoid_validated=0.3, avoid_suspected=0.5, **scoring):
    return {
        "scoring": {"alpha": alpha, "beta": beta,
                    "thresholds": {"top1_min": top1_min, "top1_max": top1_max,
                                   "top2_max": top2_max},
                    **scoring},
        "affinity": {"blend_weight": blend_weight,
                     "eligibility_top_k": eligibility_top_k,
                     "factors": {"favor_validated": favor_validated,
                                 "favor_suspected": favor_suspected,
                                 "avoid_validated": avoid_validated,
                                 "avoid_suspected": avoid_suspected}},
    }
