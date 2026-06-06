# app/services/unified_crawler.py
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Dict, List, Optional

from ..models import Attorney, Case, Docket, Entity
from ..crawlers import mcro, sos, plainsite, courtlistener

MCRO_CASE_DETAIL_TEMPLATE = "https://publicaccess.courts.state.mn.us/CaseDetail.aspx?CaseID={case_id}"

async def upsert_attorney(db: AsyncSession, bar_number: str, state: str = "MN") -> Attorney:
    result = await db.execute(
        Attorney.__table__.select().where(Attorney.bar_number == bar_number)
    )
    attorney = result.scalar_one_or_none()
    if not attorney:
        attorney = Attorney(name="", bar_number=bar_number, state=state, last_seen=datetime.utcnow())
        db.add(attorney)
        await db.commit()
        await db.refresh(attorney)
    else:
        attorney.last_seen = datetime.utcnow()
        await db.commit()
    return attorney

async def upsert_entity(db: AsyncSession, entity_data: Dict) -> Optional[Entity]:
    """
    Upsert an entity from SOS data.
    """
    if not entity_data or not entity_data.get("name"):
        return None
    
    result = await db.execute(
        Entity.__table__.select().where(Entity.sos_id == entity_data.get("sos_id"))
    )
    entity = result.scalar_one_or_none()
    
    if not entity:
        entity = Entity(
            name=entity_data.get("name"),
            type=entity_data.get("type"),
            sos_id=entity_data.get("sos_id"),
            registered_agent=entity_data.get("registered_agent"),
            address=entity_data.get("address"),
        )
        db.add(entity)
        await db.commit()
        await db.refresh(entity)
    else:
        # Update existing entity with new data
        if entity_data.get("registered_agent"):
            entity.registered_agent = entity_data.get("registered_agent")
        if entity_data.get("address"):
            entity.address = entity_data.get("address")
        await db.commit()
    
    return entity

async def upsert_case(db: AsyncSession, attorney: Attorney, case_data: Dict) -> Case:
    result = await db.execute(
        Case.__table__.select().where(
            Case.case_number == case_data["case_number"],
            Case.court == case_data["court"],
        )
    )
    case = result.scalar_one_or_none()
    
    # Parse filing date if present
    filing_date = None
    if case_data.get("filing_date"):
        try:
            if isinstance(case_data["filing_date"], str):
                for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
                    try:
                        filing_date = datetime.strptime(case_data["filing_date"], fmt).date()
                        break
                    except:
                        continue
        except:
            pass
    
    if not case:
        case = Case(
            court=case_data["court"],
            case_number=case_data["case_number"],
            case_title=case_data.get("case_title"),
            case_type=case_data.get("case_type"),
            status=case_data.get("status"),
            filing_date=filing_date,
            attorney_id=attorney.id,
            last_crawled=datetime.utcnow(),
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
    else:
        case.last_crawled = datetime.utcnow()
        # Update with new data if available
        if case_data.get("status"):
            case.status = case_data["status"]
        if filing_date:
            case.filing_date = filing_date
        await db.commit()
    return case

async def replace_case_dockets(db: AsyncSession, case: Case, dockets_data: List[Dict]):
    await db.execute(Docket.__table__.delete().where(Docket.case_id == case.id))
    for d in dockets_data:
        # Use parsed date if available, otherwise None
        docket_date = d.get("date") if isinstance(d.get("date"), datetime.date) else None
        
        docket = Docket(
            case_id=case.id,
            date=docket_date,
            entry_type=d.get("entry_type"),
            description=d.get("description"),
            document_url=d.get("document_url"),
        )
        db.add(docket)
    await db.commit()

async def crawl_attorney_full(db: AsyncSession, bar_number: str) -> Dict:
    attorney = await upsert_attorney(db, bar_number)

    cases_data = await mcro.fetch_cases_by_attorney(bar_number)
    crawled_cases: List[int] = []
    entities_created: List[int] = []

    for cdata in cases_data:
        case = await upsert_case(db, attorney, cdata)

        # Use case_id if available, otherwise fall back to case_number
        case_id = cdata.get("case_id") or cdata.get("case_number")
        case_detail_url = MCRO_CASE_DETAIL_TEMPLATE.format(case_id=case_id)
        
        dockets_data = await mcro.fetch_case_docket(case_detail_url)
        await replace_case_dockets(db, case, dockets_data)

        # Try to extract and upsert entity from case title
        if cdata.get("case_title"):
            entity_name = extract_entity_from_case_title(cdata["case_title"])
            if entity_name:
                entity_data = await sos.fetch_entity_from_sos(entity_name, state="MN")
                if entity_data:
                    entity = await upsert_entity(db, entity_data)
                    if entity:
                        # Link entity to case
                        case.entity_id = entity.id
                        await db.commit()
                        entities_created.append(entity.id)

        crawled_cases.append(case.id)

    # Enrich with PlainSite + CourtListener
    plainsite_profile = await plainsite.fetch_plainsite_profile(attorney.name or bar_number)
    federal_cases = await courtlistener.fetch_federal_cases_for_attorney(attorney.name or bar_number)

    return {
        "attorney_id": attorney.id,
        "cases_crawled": crawled_cases,
        "entities_created": entities_created,
        "plainsite_results": plainsite_profile.get("total_results", 0) if plainsite_profile else 0,
        "federal_cases_count": len(federal_cases),
    }

def extract_entity_from_case_title(case_title: str) -> Optional[str]:
    """
    Try to extract an entity name from a case title.
    
    Case titles are typically "Plaintiff v. Defendant" or similar.
    This is a simple heuristic - may need refinement.
    """
    if not case_title:
        return None
    
    # Split on common separators
    for separator in [" v. ", " vs. ", " V. ", " VS. ", " v ", " vs "]:
        if separator in case_title:
            parts = case_title.split(separator)
            if len(parts) >= 2:
                # Return the defendant (second part) as it's often the entity we care about
                defendant = parts[1].strip()
                # Remove common suffixes
                for suffix in [" LLC", " Inc", " Corp", " Ltd", " Co", " Corporation", " Company"]:
                    if defendant.endswith(suffix):
                        return defendant
                return defendant
    
    return None
