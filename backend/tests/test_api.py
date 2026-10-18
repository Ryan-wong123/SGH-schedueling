import asyncio
from io import BytesIO

import httpx
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from app.main import create_app
from app.services.workbook_writer import PREVIEW_HEADERS


def as_bytes(workbook):
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_health_endpoint():
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
    asyncio.run(check())


def test_generate_allocation_validates_password():
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://test") as client:
            response = await client.post("/api/generate-allocation", data={"glf_password": ""})
            assert response.status_code in {400, 422}
    asyncio.run(check())


def test_generation_and_both_downloads_preserve_all_records_and_original_workbook(tmp_path):
    glf = Workbook()
    glf.active.title = "Criteria"
    glf.active["A1"] = "=1+2"
    progress = glf.create_sheet("Progress")
    progress.append(["Name", "Rx Check", "Dispensing", "Med Recon", "MiniCeX"])
    progress.append(["Y1"])
    for i in range(130):
        progress.append([f"Person {i}"])
    progress["E3"] = "Prior Assessor 01/04/26"
    progress["E3"].fill = PatternFill(fill_type="solid", fgColor="FF000000")
    glf.create_sheet("Later")["A1"] = "Keep me"
    roster = Workbook()
    roster.active.append(["Name", "15/04/26"])
    for name, value, colour in [("OPS Assessor", "GLF/", "FFFFFF00"), ("Ward Assessor", "{45A}", "FFFFFFFF")]:
        roster.active.append([name, value])
        roster.active.cell(roster.active.max_row, 2).fill = PatternFill(fill_type="solid", fgColor=colour)
    for i in range(130):
        roster.active.append([f"Person {i}", "45A / MICA"])
        roster.active.cell(roster.active.max_row, 2).fill = PatternFill(fill_type="solid", fgColor="FFFFFFFF")

    async def check():
        app = create_app()
        app.state.output_dir = tmp_path
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/generate-allocation", data={"glf_password": "test-password"}, files={
                "glf_workbook": ("glf.xlsx", as_bytes(glf)),
                "roster_workbook": ("roster.xlsx", as_bytes(roster)),
            })
            assert response.status_code == 200, response.text
            body = response.json()
            assert len(body["records"]) == 520
            assert sum(body["summary"].values()) == 520
            allocated = [r for r in body["records"] if r["status"] == "Allocated"]
            full = await client.get("/api/download/" + body["download_id"])
            new = await client.get("/api/download-preview/" + body["preview_download_id"])
            assert full.status_code == new.status_code == 200
            updated = load_workbook(BytesIO(full.content))
            assert updated.sheetnames == ["Criteria", "Generated Allocation", "Progress", "Later"]
            assert updated["Criteria"]["A1"].value == "=1+2"
            assert updated["Progress"]["E3"].value == "Prior Assessor 01/04/26"
            assert updated["Generated Allocation"]["E3"].value is None
            assert updated["Generated Allocation"]["E3"].fill.fgColor.rgb == "FF000000"
            assert updated["Later"]["A1"].value == "Keep me"
            exported = load_workbook(BytesIO(new.content))["New Allocation"]
            assert tuple(c.value for c in exported[1]) == PREVIEW_HEADERS
            assert exported.max_row == len(allocated) + 1
            for row, record in zip(exported.iter_rows(min_row=2, values_only=True), allocated):
                assert row[:6] == (record["date"], record["assesseeName"], "Y1", record["assessmentType"], record["assesseeLocation"], record["assignedAssessor"])
            assert not list(tmp_path.iterdir())
            assert not app.state.downloads
    asyncio.run(check())
