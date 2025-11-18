"""Application orchestration package for NewsNow Neon.

Contains controller-adjacent modules:
- services: service injection/proxies for data and persistence
- filtering: pure headline filtering and exclusion normalization
- timeutils: timezone coercion and localized timestamp formatting
- rendering: grouping, relative age, and metadata composition helpers
- actions: helpers for mute keyword/source derivation
"""

__all__ = ["services", "filtering", "timeutils", "rendering", "actions"]