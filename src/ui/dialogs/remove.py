"""
Remove item dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_remove_template
from src.ui.dialogs.dialog_handlers import remove_submit_handler
from src.ui.context.app_context import AppContext


class RemoveDialog(BaseDialog):
    """Dialog for removing teams or players from league or current view."""

    def __init__(self, context: AppContext, parent=None):
        template = create_remove_template(submit_handler=remove_submit_handler)
        ctx_dict = context.to_dict()
        ctx_dict["lv_players"] = context.lv_players
        ctx_dict.setdefault("stack", None)
        ctx_dict.setdefault("undo", None)
        ctx_dict.setdefault("message", context.message)
        super().__init__(template, ctx_dict, parent=parent)
        self.lv_players = context.lv_players
