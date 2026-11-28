"""site-build.yml's previews (QuantEcon/project-monorepo#79): on a pull request,
each site built is deployed to its own Cloudflare Pages project, with a comment
of its own, from a job that holds the token and runs no lecture code."""

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent


def jobs():
    return yaml.safe_load((ROOT / ".github/workflows/site-build.yml").read_text(encoding="utf-8"))["jobs"]


def steps():
    return jobs()["preview"]["steps"]


def named(name):
    return next(s for s in steps() if s.get("name") == name)


def deploy():
    return next(s for s in steps() if s.get("id") == "preview")


def test_the_preview_runs_on_pull_requests_after_every_leg_over_the_same_sites():
    preview, build = jobs()["preview"], jobs()["build"]

    assert preview["needs"] == ["sites", "build"]
    assert preview["if"] == "${{ !cancelled() && github.event_name == 'pull_request' && needs.sites.outputs.any == 'true' }}"
    assert preview["strategy"]["matrix"] == build["strategy"]["matrix"]
    assert preview["strategy"]["fail-fast"] is False
    assert preview["runs-on"] == "ubuntu-latest"
    assert preview["permissions"] == {"contents": "read", "actions": "read", "pull-requests": "write"}


def test_only_the_deploy_step_holds_the_cloudflare_secrets():
    for name, job in jobs().items():
        assert "secrets." not in yaml.safe_dump({k: v for k, v in job.items() if k != "steps"}), name
        for step in job["steps"]:
            if "secrets." in yaml.safe_dump(step):
                assert (name, step.get("id")) == ("preview", "preview"), (name, step.get("name"))
    assert deploy()["with"]["cloudflare-api-token"] == "${{ secrets.CLOUDFLARE_PAGES_TOKEN }}"
    assert deploy()["with"]["cloudflare-account-id"] == "${{ secrets.CLOUDFLARE_QE_ACCOUNT_ID }}"


def test_the_build_can_neither_comment_nor_read_a_secret():
    assert jobs()["build"]["permissions"] == {"contents": "read", "packages": "read"}


def test_each_site_previews_to_its_own_project_in_a_comment_of_its_own():
    w = deploy()["with"]

    assert deploy()["uses"] == "quantecon/actions/preview-cloudflare@v0"
    assert w["project-name"] == "qe-preview-${{ matrix.site.key }}"
    assert w["comment-key"] == "${{ matrix.site.key }}"
    assert w["toc-file"] == "sites/${{ matrix.site.key }}/_toc.yml"
    assert w["lectures-dir"] == "lectures"
    assert w["build-dir"] == "_build/html"


def test_the_preview_deploys_the_html_the_build_kept_without_the_pdf():
    upload = next(s for s in jobs()["build"]["steps"] if s.get("name") == "Keep the site's HTML")
    download = named("Download the site's HTML")
    drop = named("Leave the PDF out")

    assert download["with"]["name"] == upload["with"]["name"] == "html-${{ matrix.site.key }}"
    assert download["with"]["path"] == "_build/html"
    assert steps().index(download) < steps().index(drop) < steps().index(deploy())


def test_a_site_whose_build_kept_no_html_gets_no_preview():
    first, *rest = steps()

    assert first["id"] == "html"
    assert "artifacts?name=html-$KEY" in first["run"]
    for step in rest:
        assert step["if"] == "${{ steps.html.outputs.found == 'true' }}", step.get("name")


def run_drop(tmp_path, files):
    for rel, size in files.items():
        path = tmp_path / "_build/html" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(size)
    return subprocess.run(["bash", "-eo", "pipefail", "-c", named("Leave the PDF out")["run"]],
                          cwd=tmp_path, capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})


def test_the_pdf_is_left_out_and_the_rest_is_kept(tmp_path):
    res = run_drop(tmp_path, {"index.html": 100, "_pdf/book.pdf": 68 << 20, "_notebooks/a.ipynb": 200_000})

    assert res.returncode == 0, res.stdout + res.stderr
    assert not (tmp_path / "_build/html/_pdf").exists()
    assert (tmp_path / "_build/html/_notebooks/a.ipynb").exists()
    assert "The preview holds" in res.stdout


def test_the_preview_gets_a_404_page_so_a_missing_address_is_no_home_page(tmp_path):
    res = run_drop(tmp_path, {"index.html": 100, "_pdf/book.pdf": 1000})
    page = (tmp_path / "_build/html/404.html").read_text(encoding="utf-8")

    assert res.returncode == 0, res.stdout + res.stderr
    assert page.startswith("<!DOCTYPE html>\n")
    assert "<title>Not in this preview</title>" in page
    assert page.rstrip().endswith("</html>")


def test_a_404_page_the_site_has_is_kept(tmp_path):
    (tmp_path / "_build/html").mkdir(parents=True)
    (tmp_path / "_build/html/404.html").write_text("the site's own", encoding="utf-8")
    res = run_drop(tmp_path, {"index.html": 100})

    assert res.returncode == 0, res.stdout + res.stderr
    assert (tmp_path / "_build/html/404.html").read_text(encoding="utf-8") == "the site's own"


def test_any_other_file_over_25_mib_fails_before_the_deploy(tmp_path):
    res = run_drop(tmp_path, {"index.html": 100, "_images/huge.gif": (25 << 20) + 1, "_static/ok.js": 25 << 20})

    assert res.returncode == 1
    assert "::error::" in res.stdout
    assert "_images/huge.gif" in res.stdout
    assert "ok.js" not in res.stdout
