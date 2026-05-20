# External Mappings Module

## Overview

This module provides a comprehensive system for mapping Semptify internal IDs to external system references. It acts as a bridge between Semptify's internal user ID system and external identifiers used by courts, property records, and government agencies.

## Features

### General Mappings
- **Universal mapping table** for any external system
- **Audit trail** with creation/update timestamps
- **Verification status** tracking
- **User-scoped** mappings for privacy

### Specialized Mappings
- **Court Cases**: Detailed legal case information with dates, parties, judges
- **Properties**: Parcel IDs, addresses, county assessor links
- **Agencies**: Complaint numbers, submission tracking, resolution status

## API Endpoints

### General Mappings
- `POST /api/external-mappings/mapping` - Create mapping
- `GET /api/external-mappings/mappings` - List user mappings
- `GET /api/external-mappings/mapping/{id}` - Get mapping details
- `PUT /api/external-mappings/mapping/{id}/status` - Update status

### Court Cases
- `POST /api/external-mappings/court-case` - Create court case mapping
- `GET /api/external-mappings/court-cases` - List court cases

### Properties
- `POST /api/external-mappings/property` - Create property mapping
- `GET /api/external-mappings/properties` - List properties

### Agencies
- `POST /api/external-mappings/agency` - Create agency mapping
- `GET /api/external-mappings/agencies` - List agency mappings

### Search
- `GET /api/external-mappings/search` - Search across all mappings

## Usage Examples

### Creating a Court Case Mapping

```python
# Map a Minnesota Housing Court case
case_data = {
    "court_system": "mn_state",
    "case_number": "27-HC-21-12345",
    "case_type": "eviction",
    "case_title": "Landlord vs Tenant",
    "court_name": "Hennepin County Housing Court",
    "judge_name": "Judge Smith",
    "filing_date": "2024-01-15T00:00:00Z",
    "hearing_date": "2024-02-01T10:00:00Z",
    "case_portal_url": "https://mncourts.gov/case/27-HC-21-12345",
    "septify_complaint_id": "abc-123-def"
}

response = await client.post("/api/external-mappings/court-case", json=case_data)
```

### Creating a Property Mapping

```python
# Map a Hennepin County property
property_data = {
    "parcel_id": "12-345-678-9012",
    "county": "hennepin",
    "municipality": "minneapolis",
    "street_address": "123 Main St Apt 4B",
    "city": "Minneapolis",
    "state": "MN",
    "zip_code": "55401",
    "county_assessor_url": "https://hennepin.us/property/12-345-678-9012",
    "septify_lease_doc_id": "lease-456-def"
}

response = await client.post("/api/external-mappings/property", json=property_data)
```

### Creating an Agency Mapping

```python
# Map a consumer protection complaint
agency_data = {
    "agency_code": "mn_ag_consumer",
    "agency_name": "Minnesota Attorney General's Office",
    "complaint_number": "AG-2024-001234",
    "complaint_type": "consumer_protection",
    "submission_date": "2024-01-10T00:00:00Z",
    "tracking_url": "https://www.ag.state.mn.us/track/AG-2024-001234",
    "septify_complaint_id": "complaint-789-ghi"
}

response = await client.post("/api/external-mappings/agency", json=agency_data)
```

## Database Schema

### Tables Created

1. **external_mappings** - General purpose mapping table
2. **court_case_mappings** - Detailed court case information
3. **property_mappings** - Property and parcel details
4. **agency_mappings** - Agency complaint tracking

### Key Relationships

- All mappings are **user-scoped** via `user_id` field
- Each specialized mapping also creates a **general mapping** entry
- Cross-references to Semptify entities via `septify_*_id` fields

## Integration with Semptify

### User ID Compatibility

- **Semptify IDs**: `GU7x9kM2pQ` (10 chars, internal)
- **External IDs**: Court numbers, parcel IDs, complaint numbers
- **Mapping Purpose**: Bridge between systems, not replacement

### Privacy Considerations

- All mappings are **user-scoped** and never shared
- External URLs are stored for user convenience only
- Verification status helps ensure data accuracy

## External System Examples

### Minnesota Courts
- **State Courts**: Format `27-CV-21-1234` (County-Type-Year-Sequence)
- **Housing Courts**: Format `27-HC-21-1234` (County-Housing Court-Year-Sequence)
- **Federal Courts**: Format `1:23-cv-00456-JMS` (Court-CaseType-Year-Sequence-Judge)

### Property Records
- **Hennepin County**: `12-345-678-9012` (PLSID format)
- **Ramsey County**: `R12.345.678.9012` (County prefix format)
- **Tax IDs**: Vary by county, often same as parcel ID

### Agency Complaints
- **Attorney General**: `AG-2024-001234` (Agency-Year-Sequence)
- **HUD**: `FHA-2024-5678` (Program-Year-Sequence)
- **Department of Human Rights**: `DHR-2024-9012` (Agency-Year-Sequence)

## Best Practices

1. **Always verify external IDs** before creating mappings
2. **Use official sources** (court portals, county websites)
3. **Keep mappings updated** when external information changes
4. **Document verification sources** for audit trails
5. **Use appropriate mapping types** for better organization

## Future Enhancements

- **Automatic verification** via external API integration
- **Bulk import/export** for data migration
- **Mapping templates** for common external systems
- **Change tracking** and history logs
- **Integration with document filing** systems
