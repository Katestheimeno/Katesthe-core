from utils.models._timestamp import TimeStampedModel
from utils.models._trackable import TrackableModel
from utils.models._softdelete import SoftDeleteModel

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
