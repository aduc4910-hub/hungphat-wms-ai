"""
HUNG PHAT MASTER AGENT - COORDINATOR CORE
Thực thi điều phối chuẩn 5 bước theo System Instructions & Agent Blueprint:
- STEP 1: data_validation
- STEP 2: market_analysis
- STEP 3: location_evaluation
- STEP 4: HUMAN REVIEW
- STEP 5: report_generation
Tạo và xuất đầy đủ 6 đầu ra bắt buộc:
1. Data Quality Report
2. Market Analysis Report
3. Comparison Matrix
4. Recommendation Report
5. Survey Plan
6. Execution Log
"""

import json
import os
import sys
from typing import Dict, Any

from src.agent_core import AuditLogger, AgentContext
from src.skills.data_validation import DataValidationSkill
from src.skills.market_analysis import MarketAnalysisSkill
from src.skills.location_evaluation import LocationEvaluationSkill
from src.skills.human_review import HumanReviewSkill
from src.skills.report_generation import ReportGenerationSkill

class HungPhatMasterAgent:
    def __init__(self, session_name: str = "HUNG_PHAT_MASTER_AGENT"):
        self.logger = AuditLogger(log_name=session_name)
        self.skill_validation = DataValidationSkill(logger=self.logger)
        self.skill_market = MarketAnalysisSkill(logger=self.logger)
        self.skill_evaluation = LocationEvaluationSkill(logger=self.logger)
        self.skill_human_review = HumanReviewSkill(logger=self.logger)
        self.skill_report_gen = ReportGenerationSkill(logger=self.logger)

    def run_pipeline(
        self,
        raw_data_or_path: Any,
        output_dir: str = "outputs",
        run_tag: str = "run",
        auto_manager_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Thực thi quy trình 5 bước khép kín của HUNG PHAT MASTER AGENT
        """
        # 0. Nạp dữ liệu
        if isinstance(raw_data_or_path, str):
            with open(raw_data_or_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        else:
            raw_data = raw_data_or_path

        self.logger.record_step(
            step_id="INITIALIZATION",
            step_name="Master Agent Awakening",
            action="LOAD_PROJECT_DATASET",
            details={
                "project_name": raw_data.get("project_meta", {}).get("project_name"),
                "total_docs": len(raw_data.get("market_documents", [])),
                "total_hubs": len(raw_data.get("deployment_capacity", {}).get("regional_support_hubs", {}))
            }
        )

        ctx = AgentContext(raw_data=raw_data)

        # -------------------------------------------------------------
        # STEP 1: data_validation
        # -------------------------------------------------------------
        validation_res = self.skill_validation.execute(raw_data=raw_data)
        ctx.sanitized_data = validation_res["validated_locations"]
        ctx.data_warnings = validation_res["missing_issues"] + validation_res["duplicate_issues"]

        # -------------------------------------------------------------
        # STEP 2: market_analysis
        # -------------------------------------------------------------
        market_res = self.skill_market.execute(
            validated_data=validation_res,
            solution_catalog=raw_data.get("solution_catalog", {})
        )
        ctx.market_insights = market_res["location_insights"]

        # -------------------------------------------------------------
        # STEP 3: location_evaluation
        # -------------------------------------------------------------
        eval_res = self.skill_evaluation.execute(
            location_insights=ctx.market_insights,
            criteria_list=raw_data.get("selection_criteria", []),
            deployment_capacity=raw_data.get("deployment_capacity", {})
        )
        ctx.evaluation_results = eval_res
        ctx.recommended_locations = eval_res["top_2_recommendations"]
        ctx.rejected_locations = eval_res["unprioritized_locations"]

        # -------------------------------------------------------------
        # STEP 4: HUMAN REVIEW
        # -------------------------------------------------------------
        review_res = self.skill_human_review.review(
            validation_res=validation_res,
            eval_res=eval_res,
            auto_manager_approval=auto_manager_approval
        )

        # -------------------------------------------------------------
        # STEP 5: report_generation
        # -------------------------------------------------------------
        output_files = self.skill_report_gen.execute(
            project_meta=raw_data.get("project_meta", {}),
            validation_res=validation_res,
            market_res=market_res,
            eval_res=eval_res,
            review_res=review_res,
            output_dir=output_dir,
            tag=run_tag
        )

        top_2_ids = [l["location_id"] for l in ctx.recommended_locations]
        rejected_ids = [l["location_id"] for l in ctx.rejected_locations]

        final_status = review_res["review_status"]

        return {
            "final_status": final_status,
            "is_approved": review_res["is_approved"],
            "top_2_recommendations": top_2_ids if final_status != "NEED_MORE_DATA" else [],
            "unprioritized_locations": rejected_ids,
            "data_health_score": validation_res["health_score"],
            "total_warnings": len(ctx.data_warnings),
            "output_files": output_files,
            "review_notes": review_res["review_notes"],
            "action_required": review_res.get("action_required")
        }

# Giữ tương thích ngược với HungPhatAgentSystem
HungPhatAgentSystem = HungPhatMasterAgent
