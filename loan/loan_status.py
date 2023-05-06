from dataclasses import dataclass
from datetime import datetime


@dataclass
class LoanStatus:
    date: datetime.date
    balance: float
    interest: float
    principal: float
    taxes: float
