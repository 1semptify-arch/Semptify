"""Seed the community help directory (find help near me).

Idempotent: upserts by (name, category, state_code) so it can be re-run
safely. Run inside the module root with venv311 active:

    .\\venv311\\Scripts\\python.exe tools\\seed_help_directory.py

Data rules (Brad, 2026-09-21): every listing must either charge nothing
(is_no_charge) or be an officially verified nonprofit (is_verified_nonprofit
+ verified_source). Contact details were checked against the organizations'
own official pages on 2026-09-21.

Scope of this seed: nationwide organizations plus one verified legal-aid
entry per state (from static/data/state-laws.json). County/city-level local
orgs (food shelves, humane societies, shelters) are added through the admin
CSV importer (/admin/resources/import) — the schema supports them.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.utc import utc_now
from app.models.models import Resource as ResourceModel

# ---------------------------------------------------------------------------
# Nationwide verified set — contact info checked against official sites.
# is_no_charge = the service itself costs the caller nothing.
# ---------------------------------------------------------------------------
NATIONAL = [
    # --- crisis ---
    dict(name="988 Suicide & Crisis Lifeline", category="crisis", subcategory="suicide_crisis",
         contact_info=dict(phone="988", text_line="988", website="https://988lifeline.org",
                           hours="24/7"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=False,
         verified_source="samhsa.gov"),
    dict(name="Crisis Text Line", category="crisis", subcategory="text_support",
         contact_info=dict(text_line="Text HOME to 741741", website="https://www.crisistextline.org",
                           hours="24/7"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="crisistextline.org"),
    dict(name="National Domestic Violence Hotline", category="crisis", subcategory="domestic_violence",
         contact_info=dict(phone="1-800-799-7233", text_line="Text START to 88788",
                           tty="1-800-787-3224", website="https://www.thehotline.org", hours="24/7"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="thehotline.org"),
    dict(name="RAINN National Sexual Assault Hotline", category="crisis", subcategory="sexual_assault",
         contact_info=dict(phone="1-800-656-4673", website="https://www.rainn.org", hours="24/7"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="rainn.org"),
    dict(name="Veterans Crisis Line", category="crisis", subcategory="veterans",
         contact_info=dict(phone="988 then press 1", text_line="838255",
                           website="https://www.veteranscrisisline.net", hours="24/7"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=False,
         verified_source="va.gov"),
    dict(name="The Trevor Project Lifeline", category="crisis", subcategory="lgbtq_youth",
         contact_info=dict(phone="1-866-488-7386", text_line="Text START to 678678",
                           website="https://www.thetrevorproject.org", hours="24/7"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="thetrevorproject.org"),
    dict(name="National Runaway Safeline", category="crisis", subcategory="youth",
         contact_info=dict(phone="1-800-786-2929", text_line="66008",
                           website="https://www.1800runaway.org", hours="24/7"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="1800runaway.org"),
    dict(name="Childhelp National Child Abuse Hotline", category="crisis", subcategory="child_abuse",
         contact_info=dict(phone="1-800-422-4453", text_line="1-800-422-4453",
                           website="https://www.childhelp.org", hours="24/7"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="childhelp.org"),
    dict(name="National Human Trafficking Hotline", category="crisis", subcategory="trafficking",
         contact_info=dict(phone="1-888-373-7888", text_line="233733",
                           website="https://humantraffickinghotline.org", hours="24/7"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="humantraffickinghotline.org (Polaris)"),

    # --- food ---
    dict(name="USDA National Hunger Hotline", category="food", subcategory="hunger_hotline",
         contact_info=dict(phone="1-866-348-6479", text_line="914-342-7744",
                           website="https://www.usda.gov", hours="Mon–Fri, business hours"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=False,
         verified_source="usda.gov"),
    dict(name="Feeding America — find your food bank", category="food", subcategory="food_bank",
         contact_info=dict(website="https://www.feedingamerica.org/find-your-local-foodbank"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="feedingamerica.org"),
    dict(name="Meals on Wheels America — find local meals", category="food", subcategory="senior_meals",
         contact_info=dict(website="https://www.mealsonwheelsamerica.org/find-meals"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="mealsonwheelsamerica.org"),

    # --- shelter ---
    dict(name="American Red Cross — shelters & disaster help", category="shelter",
         subcategory="disaster_shelter",
         contact_info=dict(phone="1-800-733-2767", website="https://www.redcross.org/get-help.html",
                           hours="24/7"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="redcross.org (congressionally chartered)"),
    dict(name="The Salvation Army — shelters & meals", category="shelter", subcategory="emergency_shelter",
         contact_info=dict(website="https://www.salvationarmyusa.org/usn/location-search/"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="salvationarmyusa.org"),

    # --- housing ---
    dict(name="211 — local help referral (United Way)", category="housing", subcategory="community_referral",
         contact_info=dict(phone="211", website="https://www.211.org", hours="24/7 in most areas"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="211.org (United Way)"),
    dict(name="HUD Housing Counseling", category="housing", subcategory="housing_counseling",
         contact_info=dict(phone="1-800-569-4287",
                           website="https://www.hud.gov/counseling", hours="business hours"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=False,
         verified_source="hud.gov"),
    dict(name="Eldercare Locator", category="housing", subcategory="senior_services",
         contact_info=dict(phone="1-800-677-1116", website="https://eldercare.acl.gov",
                           hours="Mon–Fri 9am–8pm ET"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=False,
         verified_source="acl.gov"),

    # --- legal_aid ---
    dict(name="Legal Services Corporation — find legal aid", category="legal_aid",
         subcategory="legal_aid_finder",
         contact_info=dict(website="https://www.lsc.gov/about-lsc/what-legal-aid/get-legal-help"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="lsc.gov (congressionally established)"),
    dict(name="LawHelp.org — legal aid by state", category="legal_aid", subcategory="legal_aid_finder",
         contact_info=dict(website="https://www.lawhelp.org"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="lawhelp.org (Pro Bono Net)"),
    dict(name="ABA Find Legal Help — bar referrals by state", category="legal_aid",
         subcategory="bar_referral",
         contact_info=dict(website="https://www.americanbar.org/groups/legal_services/flh-home/"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="americanbar.org"),

    # --- addiction ---
    dict(name="SAMHSA National Helpline", category="addiction", subcategory="treatment_referral",
         contact_info=dict(phone="1-800-662-4357", tty="1-800-487-4889",
                           website="https://www.samhsa.gov/find-help/national-helpline", hours="24/7"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=False,
         verified_source="samhsa.gov"),
    dict(name="FindTreatment.gov", category="addiction", subcategory="treatment_locator",
         contact_info=dict(website="https://findtreatment.gov"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=False,
         verified_source="samhsa.gov"),
    dict(name="Alcoholics Anonymous", category="addiction", subcategory="peer_support",
         contact_info=dict(website="https://www.aa.org/find-aa"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="aa.org"),
    dict(name="Narcotics Anonymous", category="addiction", subcategory="peer_support",
         contact_info=dict(website="https://www.na.org/meetingsearch/"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="na.org"),
    dict(name="Al-Anon Family Groups", category="addiction", subcategory="family_support",
         contact_info=dict(phone="1-888-425-2666", website="https://al-anon.org",
                           hours="Mon–Fri 8am–6pm ET"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="al-anon.org"),
    dict(name="SMART Recovery", category="addiction", subcategory="peer_support",
         contact_info=dict(website="https://www.smartrecovery.org"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="smartrecovery.org"),

    # --- mental_health ---
    dict(name="NAMI HelpLine", category="mental_health", subcategory="peer_support",
         contact_info=dict(phone="1-800-950-6264", text_line="Text NAMI to 62640",
                           email="helpline@nami.org", website="https://www.nami.org/help",
                           hours="Mon–Fri 10am–10pm ET"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="nami.org"),

    # --- pet_health ---
    dict(name="RedRover — pets in crisis (DV boarding, vet grants)", category="pet_health",
         subcategory="pet_crisis",
         contact_info=dict(email="info@redrover.org", website="https://redrover.org"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="redrover.org"),
    dict(name="Feeding Pets of the Homeless", category="pet_health", subcategory="pet_food_vet",
         contact_info=dict(phone="775-841-7463", email="info@petsofthehomeless.org",
                           website="https://petsofthehomeless.org/get-help/"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="petsofthehomeless.org"),

    # --- faith ---
    dict(name="The Salvation Army", category="faith", subcategory="shelter_food",
         contact_info=dict(website="https://www.salvationarmyusa.org/usn/location-search/"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="salvationarmyusa.org"),
    dict(name="Catholic Charities USA — local agencies", category="faith", subcategory="community_services",
         contact_info=dict(website="https://www.catholiccharitiesusa.org/find-help/"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="catholiccharitiesusa.org"),
    dict(name="Society of St. Vincent de Paul — local conferences", category="faith",
         subcategory="rent_food_help",
         contact_info=dict(website="https://ssvpusa.org/assistance-services/"),
         languages=["en", "es"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="ssvpusa.org"),
    dict(name="Lutheran Services in America", category="faith", subcategory="community_services",
         contact_info=dict(website="https://lutheranservices.org"),
         languages=["en"], is_no_charge=True, is_verified_nonprofit=True,
         verified_source="lutheranservices.org"),
]


def _state_legal_aid() -> list[dict]:
    """One verified legal-aid listing per state from state-laws.json."""
    path = os.path.join(os.path.dirname(__file__), "..", "static", "data", "state-laws.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for code, info in sorted(data.get("states", {}).items()):
        for entry in info.get("legal_aid", []):
            name = entry.get("name")
            url = entry.get("url")
            if not name or not url:
                continue
            rows.append(dict(
                name=name,
                category="legal_aid",
                subcategory="legal_aid_office",
                service_area=f"{info.get('name', code)}",
                state_code=code,
                contact_info=dict(website=url),
                languages=["en"],
                is_no_charge=True,
                is_verified_nonprofit=True,
                verified_source="state-laws.json curated legal aid",
            ))
    return rows


async def main() -> None:
    entries = [dict(service_area="Nationwide", state_code=None, **e) for e in NATIONAL]
    entries += _state_legal_aid()

    created = updated = 0
    async with get_db_session() as session:
        for e in entries:
            q = select(ResourceModel).where(
                func.lower(ResourceModel.name) == e["name"].lower(),
                func.lower(ResourceModel.category) == e["category"].lower(),
            )
            if e.get("state_code"):
                q = q.where(ResourceModel.state_code == e["state_code"])
            else:
                q = q.where(ResourceModel.state_code.is_(None))
            existing = (await session.execute(q)).scalar_one_or_none()
            if existing:
                for k, v in e.items():
                    setattr(existing, k, v)
                existing.updated_at = utc_now()
                updated += 1
            else:
                session.add(ResourceModel(
                    id=make_id("res"),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                    last_verified=utc_now(),
                    is_active=True,
                    **e,
                ))
                created += 1
    print(f"seed_help_directory: {created} created, {updated} updated "
          f"({len(entries)} entries total)")


if __name__ == "__main__":
    asyncio.run(main())
