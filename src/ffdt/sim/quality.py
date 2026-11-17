"""Quality losses (T3.2.2, A-017, A-025, A-040, A-041).

Fill station (the product-contact station, ``changeover_scope: full``):
  - fill-weight in-process rejects are scrapped immediately (cause ``fill_weight``)
  - surviving vials carry hidden true defects ~ Binomial(vials, defect_frac)
AVI (``kind: inspection``):
  - true defects detected ~ Binomial(defects, detect); good vials falsely rejected
    ~ Binomial(good, false_reject). Rejects leave the flow as one reject lot.
Manual re-inspection (offline pool of ``staffing.inspector`` units, A-017):
  - confirmed defects ~ Binomial(detected, confirm) are scrapped (cause ``avi_confirmed``)
  - the rest (false rejects + unconfirmed true defects) return to the flow upstream of the
    labeler as a rework lot. Good vials are never scrapped by the manual inspector (A-025).
Undetected defects that reach the sink are counted as escapes (a quality-risk metric, not yield).

Every draw uses its own named stream so scenarios keep common random numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ffdt.config import Quality
from ffdt.rng import stream
from ffdt.sim.core import SubLot

CAUSES = ("fill_weight", "avi_confirmed")


@dataclass
class QualityLedger:
    """Vial counts by cause. ``scrapped`` keys are the yield-loss causes in ``CAUSES``."""

    scrapped: dict[str, int] = field(default_factory=lambda: dict.fromkeys(CAUSES, 0))
    defects_created: int = 0
    avi_true_rejects: int = 0
    avi_false_rejects: int = 0
    reworked_returned: int = 0
    escapes: int = 0  # true defects packed (missed by AVI, or unconfirmed on re-inspection)


class QualityModel:
    def __init__(self, line, q: Quality, root_seed: int, replication: int):
        self.line, self.q, self.ledger = line, q, QualityLedger()

        def rng(name):
            return stream(root_seed, replication, f"quality.{name}")

        self._fw, self._def = rng("fill_weight"), rng("defects")
        self._det, self._fr, self._conf = rng("avi_detect"), rng("avi_false"), rng("confirm")
        self.reject_store = None  # set by Line: simpy.Store feeding manual re-inspection

    # -- transforms (Machine hook signature: (machine, item) -> item | None) --------------
    def fill(self, _m, item: SubLot) -> SubLot:
        fw = int(self._fw.binomial(item.vials, self.q.fill_weight_reject_frac))
        if fw:
            item.vials -= fw
            self._scrap(item, fw, "fill_weight")
        item.defects = int(self._def.binomial(item.vials, self.q.defect_frac))
        self.ledger.defects_created += item.defects
        return item

    def avi(self, _m, item: SubLot) -> SubLot:
        if item.rework:
            return item
        det = int(self._det.binomial(item.defects, self.q.avi_detect_frac))
        fr = int(self._fr.binomial(item.vials - item.defects, self.q.avi_false_reject_frac))
        if det + fr:
            item.vials -= det + fr
            item.defects -= det
            self.ledger.avi_true_rejects += det
            self.ledger.avi_false_rejects += fr
            lot = SubLot(item.batch_id, item.product, item.format, det + fr, defects=det)
            lot.rework = True
            self.reject_store.put(lot)  # unbounded store: never blocks the AVI
        return item

    def manual(self, _m, lot: SubLot) -> SubLot | None:
        conf = int(self._conf.binomial(lot.defects, self.q.manual_confirm_frac))
        if conf:
            lot.vials -= conf
            lot.defects -= conf
            self._scrap(lot, conf, "avi_confirmed")
        self.ledger.reworked_returned += lot.vials
        return lot if lot.vials > 0 else None

    def packed(self, item: SubLot) -> None:
        self.ledger.escapes += item.defects

    def _scrap(self, item: SubLot, vials: int, cause: str) -> None:
        self.ledger.scrapped[cause] += vials
        self.line.scrap(item, vials)
