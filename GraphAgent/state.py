import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict

class IterationRecord(TypedDict):
    iteration: int
    prompt: str
    image_path: str
    rating: int
    critique: str

class ThumbnailState(TypedDict):
    topic: str                          # Input: the video topic
    search_summary: str                 # From web_search node
    current_prompt: str                 # From prompt_writer node
    current_image_path: str             # From generator node
    rating: int                         # From critic node
    critique: str                       # From critic node
    iteration: int                      # Counter, starts at 0
    history: Annotated[list, operator.add]  # Append-only list of IterationRecord
    target_rating: int                  # Default 8
    max_iterations: int                 # Default 3
    output_dir: str                     # Output folder path