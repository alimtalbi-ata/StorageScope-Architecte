"""Non-graphical frozen-executable startup probe. Author: Abdelhalim Talbi."""
import json
import sys
from pathlib import Path

def runtime_self_test(paths):
    """Validate imports, data directory and bundled modules without opening Tk."""
    from decision_governance_v537 import GovernanceStore
    from campaign_history_v526 import CampaignHistory
    from decision_workspace_ui_v543 import open_workspace
    from campaign_dashboard_v527 import launch_dashboard
    from windows_preferences_v566 import load_preferences
    from windows_context_menu_v567 import attach_text_context_menu
    assert all((GovernanceStore, CampaignHistory, open_workspace, launch_dashboard, load_preferences, attach_text_context_menu))
    base = Path(paths['base'])
    if not base.is_dir():
        raise RuntimeError('Data directory missing')
    print(json.dumps({'status':'PASS','runtime':sys.version.split()[0], 'frozen':bool(getattr(sys,'frozen',False)), 'data_dir':str(base)}, ensure_ascii=False))
    return 0
