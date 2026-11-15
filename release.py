"""Release mode and disclosure metadata; no credentials are read here."""
import os


def public_mode() -> bool:
    return os.environ.get('TRENDLENS_PUBLIC', '0') == '1'


AI_DISCLOSURE = ('OpenAI Codex assisted with code, tests, documentation, and interface text. '
                 'Measurements are NASA source data, not AI-generated. Statistics and findings '
                 'are produced deterministically by Python calculations and text templates; '
                 'no language model runs in this application.')


def release_metadata() -> dict:
    return {'application': 'Terravect / TrendLens', 'code_license': 'MIT',
            'ai_assistance': AI_DISCLOSURE,
            'third_party_terms': 'NASA data and dependencies retain their own terms; see THIRD_PARTY_NOTICES.md.'}
