# Resume Rule-Based Classification

## Description

实现基于规则的简历分类器，根据 CandidateProfile 自动生成分类标签（技术方向、经验等级、行业领域）和统计信息（工作年限、项目数量等）。

PRD Reference: US-005
SPEC Reference: Section 5.4

## Acceptance Criteria

- [ ] `backend/infrastructure/classifiers/base.py`：ResumeClassifier ABC（含 version 属性）
- [ ] `backend/infrastructure/classifiers/rule_classifier.py`：RuleBasedResumeClassifier 实现
- [ ] 技术方向标签：根据 skills 中的关键词匹配生成（Backend/Frontend/AI Engineer/DevOps/Data Engineer 等）
- [ ] 经验等级标签：根据工作年限计算（Junior 0-2 / Mid 3-5 / Senior 6-9 / Staff 10+）
- [ ] 行业领域标签：从 work_experiences 的公司/行业信息提取
- [ ] 统计信息：total_years, project_count, tech_depth（技能数量/类别覆盖度）, has_management
- [ ] 标签写入 `CandidateProfile.ability_tags`
- [ ] 状态更新为 `classified`
- [ ] Typecheck 通过

## Dependencies

Issue #5

## Type

backend

## Priority

P1
