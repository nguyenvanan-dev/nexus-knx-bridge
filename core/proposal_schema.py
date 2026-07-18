import json
from datetime import datetime

def make_proposal_base(file_name, project_name="", parser_version="3.9.0"):
    return {
        "proposal_type": "knxproj_import",
        "schema_version": 1,
        "source": {
            "file": file_name,
            "project_name": project_name,
            "parsed_at": datetime.now().isoformat(timespec="seconds"),
            "parser": "xknxproject",
            "parser_version": parser_version
        },
        "summary": {
            "total_devices": 0,
            "ready": 0,
            "needs_review": 0,
            "missing_info": 0,
            "by_type": {},
            "total_group_addresses": 0
        },
        "proposed_devices": [],
        "duplicates": [],
        "unmapped_group_addresses": []
    }
