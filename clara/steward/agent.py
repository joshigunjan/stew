import json
from typing import List, Dict, Any, Optional

from clara.profiler.base import DatasetProfile
from clara.steward.prompts import (
    STEW_SYSTEM_PROMPT,
    STEW_INITIAL_REVIEW_PROMPT,
    STEW_DATA_ARTICLE_PROMPT
)
from clara.steward.llm_client import BlabladorClient
from clara.steward.fair_evaluator import evaluate_fair_score

class StewAgent:
    def __init__(self, client: Optional[BlabladorClient] = None):
        self.client = client or BlabladorClient()

    def format_profile_for_llm(self, profile: DatasetProfile) -> str:
        col_summaries = []
        for name, col in profile.columns.items():
            col_info = (
                f"- `{name}` ({col.inferred_type}, dtype={col.physical_dtype}): "
                f"nulls={col.null_count}/{col.total_count} ({int(col.null_ratio*100)}%), "
                f"distinct={col.distinct_count}. Samples={col.sample_values[:4]}. "
                f"Suggested: {col.suggested_description} [{col.suggested_unit or 'no unit'}]."
            )
            if col.missing_value_markers:
                col_info += f" Sentinel missing markers: {col.missing_value_markers}."
            col_summaries.append(col_info)

        doi_info = ""
        if profile.metadata_context.get("doi"):
            doi_info = f"\nDOI / Provenance: {profile.metadata_context.get('doi')} ({profile.metadata_context.get('source', 'External')})"

        summary_text = (
            f"Dataset Name: {profile.title}\n"
            f"File: {profile.file_name}\n"
            f"Format: {profile.file_format}\n"
            f"Rows: {profile.row_count:,}, Columns: {profile.column_count}\n"
            f"Spatial: {profile.is_spatial} (BBox: {profile.spatial_bbox}){doi_info}\n\n"
            f"Columns Analysis:\n" + "\n".join(col_summaries)
        )
        return summary_text

    def conduct_initial_review(self, profile: DatasetProfile) -> str:
        summary_str = self.format_profile_for_llm(profile)
        prompt = STEW_INITIAL_REVIEW_PROMPT.format(profile_summary=summary_str)
        
        messages = [
            {"role": "system", "content": STEW_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        review_result = self.client.chat_completion(messages)
        
        fair_res = evaluate_fair_score(profile)
        profile.fair_score = fair_res["overall_score"]
        profile.steward_assessment = review_result
        return review_result

    def chat_turn(
        self,
        profile: DatasetProfile,
        history: List[Dict[str, str]],
        user_message: str
    ) -> str:
        summary_str = self.format_profile_for_llm(profile)
        system_content = (
            f"{STEW_SYSTEM_PROMPT}\n\n"
            f"Currently Active Dataset Profile:\n{summary_str}"
        )
        
        messages = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        
        reply = self.client.chat_completion(messages)
        return reply

    def draft_data_article(self, profile: DatasetProfile, user_notes: str = "") -> str:
        cols_text = "\n".join([
            f"- **{c.name}** ({c.inferred_type}): {c.suggested_description or 'Measurement attribute'} "
            f"[Unit: {c.suggested_unit or 'dimensionless'}, Min: {c.min_val}, Max: {c.max_val}]"
            for c in profile.columns.values()
        ])
        
        doi_src = profile.metadata_context.get("doi") or profile.metadata_context.get("zenodo_url") or "Local Scientific Observation"
        prompt = STEW_DATA_ARTICLE_PROMPT.format(
            title=profile.title,
            file_name=profile.file_name,
            row_count=profile.row_count,
            column_count=profile.column_count,
            file_format=profile.file_format,
            domain=profile.domain_field or "Environmental & Earth System Science",
            license=profile.license,
            doi_source=doi_src,
            columns_summary=cols_text,
            user_notes=user_notes or "Dataset validated for open scientific reuse and AI model training."
        )
        
        messages = [
            {"role": "system", "content": STEW_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return self.client.chat_completion(messages, temperature=0.2)

# Backwards compatibility alias
ClaraAgent = StewAgent
