# choices.py
from django.db import models

class ProposalStatus(models.TextChoices):
    SUBMITTED = 'SUBMITTED', 'Submitted'
    APPROVED  = 'APPROVED',  'Approved'
    REJECTED  = 'REJECTED',  'Rejected'

class ApplicationStatus(models.TextChoices):
    OPEN   = 'OPEN',   'Open'
    CLOSED = 'CLOSED', 'Closed'