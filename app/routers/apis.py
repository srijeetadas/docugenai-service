from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import APIListItem, APIStatus
from app.routers.analysis import api_database
from datetime import datetime

router = APIRouter()


@router.get("/apis", response_model=List[APIListItem])
async def get_all_apis():
    """Get list of all analyzed APIs"""
    apis = []

    for api_id, api_data in api_database.items():
        doc_score = api_data['doc_score']

        # Determine status based on score
        score = doc_score['score']
        if score >= 85:
            status = APIStatus.EXCELLENT
        elif score >= 70:
            status = APIStatus.GOOD
        elif score >= 50:
            status = APIStatus.NEEDS_IMPROVEMENT
        else:
            status = APIStatus.CRITICAL

        apis.append(APIListItem(
            id=api_id,
            name=api_data['name'],
            version=api_data['spec'].get('info', {}).get('version', '1.0.0'),
            doc_score=score,
            previous_score=95,
            owner=api_data['owner'],
            status=status,
            last_updated=datetime.now(),
            duplicates=len(api_data['duplicates']),
            compliance_issues=len(api_data['compliance_issues']),
            missing_examples=doc_score['missing_examples'],
            vague_descriptions=doc_score['vague_descriptions']
        ))

    return apis


@router.get("/apis/{api_id}")
async def get_api_details(api_id: str):
    """Get detailed information about a specific API"""
    if api_id not in api_database:
        raise HTTPException(status_code=404, detail="API not found")

    api_data = api_database[api_id]

    return {
        'api_id': api_id,
        'name': api_data['name'],
        'owner': api_data['owner'],
        'doc_score': api_data['doc_score'],
        'improvements': api_data['improvements'],
        'duplicates': api_data['duplicates'],
        'compliance_issues': api_data['compliance_issues']
    }


@router.delete("/apis/{api_id}")
async def delete_api(api_id: str):
    """Delete an API from the system"""
    if api_id not in api_database:
        raise HTTPException(status_code=404, detail="API not found")

    del api_database[api_id]

    return {"message": "API deleted successfully"}


@router.get("/stats")
async def get_stats():
    """Get overall statistics"""
    if not api_database:
        return {
            'total_apis': 0,
            'avg_doc_score': 0,
            'total_improvements': 0,
            'total_duplicates': 0
        }

    total_score = sum(api['doc_score']['score'] for api in api_database.values())
    avg_score = total_score // len(api_database)

    total_improvements = sum(len(api['improvements']) for api in api_database.values())
    total_duplicates = sum(len(api['duplicates']) for api in api_database.values())

    return {
        'total_apis': len(api_database),
        'avg_doc_score': avg_score,
        'total_improvements': total_improvements,
        'total_duplicates': total_duplicates
    }