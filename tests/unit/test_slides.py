import re

import pytest

from ffdt.experiments import slides as S


@pytest.fixture(scope="module")
def data():
    return S.load()


def test_five_slides_each_with_one_message_title(data):
    b, d = data
    figs = {"pareto": S.FIGS / "p.png", "forest": S.FIGS / "f.png"}
    page = S.build_html(b, d, figs)
    assert page.count('<section class="slide">') == 5
    titles = re.findall(r"<h1>(.*?)</h1>", page)
    assert len(titles) == 5 and all(len(t.split()) >= 6 for t in titles)
    assert page.count(S.viz.SIM_TAG) == 5  # every slide carries the simulated label


def test_committed_slides_and_script_match_the_results(data):
    b, d = data
    figs = {
        "pareto": S.FIGS / "slide_loss_pareto.png",
        "forest": S.FIGS / "slide_scenario_forest.png",
    }
    assert S.HTML.read_text(encoding="utf-8") == S.build_html(b, d, figs)
    assert S.SCRIPT.read_text(encoding="utf-8") == S.script(b, d)


def test_headline_numbers_come_from_results_final(data):
    b, d = data
    page = S.build_html(b, d, {"pareto": S.FIGS / "p", "forest": S.FIGS / "f"})
    m50 = next(s for s in d["scenarios"] if s["scenario"] == "sc04_changeover_m50")
    assert f"{100 * m50['pct_diff']:+.1f}%" in page
    assert f"{100 * d['baseline']['line_oee']['mean']:.1f}%" in page
    assert str(d["verification"]["automated_tests"]) in page


def test_pdf_has_five_pages():
    raw = S.PDF.read_bytes()
    assert raw.startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page[^s]", raw)) == 5


def test_figures_build_from_results(data):
    b, d = data
    assert len(S.pareto_fig(b).data[0].y) == 6
    main = [s for s in d["scenarios"] if s["set"] == "main"]
    assert len(S.forest_fig(d).data[0].y) == len(main)
