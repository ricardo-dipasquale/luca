"""Utilidades del frontend."""

import os
import sys
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from course.practices import get_practice_repository


def get_subjects() -> List[str]:
    return [subject["name"] for subject in get_practice_repository().get_subjects()]
