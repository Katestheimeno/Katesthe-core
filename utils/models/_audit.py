from utils.models.timestamp import TimeStampedModel
from utils.models.trackable import TrackableModel
from utils.models.softdelete import SoftDeleteModel

imports = []

imports += ["AuditModel"]

class AuditModel(TimeStampedModel, TrackableModel, SoftDeleteModel):
    """
    Combo abstract model:
    - created_at / updated_at
    - created_by / updated_by
    - is_deleted
    """
    class Meta:
        abstract = True


__all__ = imports
