# Agent Interview Platform 设计文档

Version: v1.0

Author: Alex Walker

Status: Draft

---

# 1. 项目背景

本项目源于 Github 开源项目 AI_Interview。

但项目目标并非仅构建一个 AI 面试产品，而是作为一个完整的 Agent 学习项目，用于系统掌握：

* Agent Workflow
* LangGraph
* RAG
* Memory
* Evaluation
* Multimodal
* Sandbox
* Observability
* SaaS Architecture

通过真实业务场景，建立完整的 Agent 工程能力体系。

---

# 2. 项目目标

构建一个企业级 Agent Interview Platform。

支持：

* 简历分析
* JD分析
* AI面试
* 动态追问
* 技术评估
* 项目评估
* 系统设计评估
* 面试报告生成

并作为未来 Agent SaaS Platform 的基础架构。

---

# 
    3. 产品定位

## 当前阶段

AI Interview Platform

## 未来扩展

* AI Recruiter
* AI Tutor
* AI Coach
* AI Sales
* AI Customer Service

本质均为：

Workflow + Agent + RAG + Evaluation

---

# 4. 技术架构

```text
Frontend (Next.js)

        │

        ▼

FastAPI Gateway

        │

        ▼

Application Layer

        │

        ▼

LangGraph Workflow Engine

        │

        ├── Resume Agent
        ├── Question Agent
        ├── Evaluation Agent
        ├── Followup Agent
        ├── Report Agent

        ▼

LLM Gateway

        │

        ├── OpenAI
        ├── Claude
        ├── DeepSeek

        ▼

Infrastructure

        ├── PostgreSQL
        ├── Redis
        ├── Qdrant
        ├── MinIO
```

---

# 5. 技术选型

## Backend

Python 3.12

## API Framework

FastAPI

## Agent Workflow

LangGraph

## ORM

SQLAlchemy

## Migration

Alembic

## Cache

Redis

## Database

PostgreSQL

## Vector Database

Qdrant

## Object Storage

MinIO

## Async Task

Celery

## Observability

OpenTelemetry

LangSmith

---

# 6. 核心业务流程

```text
创建面试

↓

上传简历

↓

输入岗位JD

↓

简历分析

↓

JD分析

↓

生成面试计划

↓

阶段提问

↓

候选人回答

↓

AI评分

↓

AI追问

↓

生成最终报告

↓

结束面试
```

---

# 7. 面试阶段设计

## Introduction

开场介绍

## Resume

简历追问

## Basic

技术基础

## Project

项目经验

## System Design

系统设计

## Behavior

行为面试

## Summary

总结反馈

---

# 8. DDD设计

## Domain

```text
domain/

├── interview
├── resume
├── question
├── evaluation
└── report
```

## Application

```text
application/

├── interview_service
├── resume_service
├── question_service
├── evaluation_service
└── report_service
```

## Infrastructure

```text
infrastructure/

├── db
├── cache
├── vector
├── storage
└── llm
```

---

# 9. Workflow设计

## Interview State

```python
class InterviewState(TypedDict):

    interview_id: str

    user_id: str

    stage: str

    resume_summary: str

    jd_summary: str

    current_question: str

    current_answer: str

    score: float

    history: list
```

## Graph流程

```text
START

↓

Analyze Resume

↓

Analyze JD

↓

Build Plan

↓

Stage Router

↓

Generate Question

↓

Wait Answer

↓

Evaluate

↓

Need Followup

├── Yes
│
└── Followup

↓

Next Stage

↓

Generate Report

↓

END
```

---

# 10. Agent设计

## Resume Agent

职责：

* 解析简历
* 提取技能
* 提取项目
* 生成候选人画像

输出：

```json
{
  "skills": [],
  "projects": []
}
```

---

## Question Agent

职责：

* 生成面试题
* 控制难度
* 避免重复问题

输入：

* Resume
* JD
* Interview History

---

## Evaluation Agent

职责：

* 回答评分
* 输出评价

评分维度：

* 技术正确性
* 工程深度
* 表达能力
* 逻辑能力

---

## Followup Agent

职责：

根据回答生成追问。

例如：

```text
Redis Cluster 为什么这样设计？

节点故障如何处理？

为什么不选择 Codis？
```

---

## Report Agent

职责：

生成最终报告。

内容：

* 技术能力
* 项目能力
* 架构能力
* 综合评价
* 改进建议

---

# 11. RAG设计

## 数据来源

* 技术题库
* 面试题库
* 公司题库
* 岗位知识库

---

## Collection

question_bank

---

## Metadata

```json
{
  "category": "redis",
  "difficulty": "middle",
  "tags": [
    "cluster"
  ]
}
```

---

## 检索流程

```text
关键词召回

↓

向量召回

↓

Rerank

↓

Prompt Assemble

↓

LLM
```

---

# 12. Memory设计

## 短期记忆

Interview Session

存储：

Redis

内容：

* 当前阶段
* 当前问题
* 历史问答

---

## 长期记忆

Candidate Profile

存储：

PostgreSQL

示例：

```json
{
  "skills": [
    "Go",
    "Redis"
  ],
  "weakness": [
    "System Design"
  ]
}
```

---

# 13. Multimodal设计

## 支持输入

* Text
* PDF
* DOCX
* Voice
* Image
* Video

---

## 处理流程

```text
Upload

↓

File Parser

↓

ASR

↓

Vision

↓

Normalize

↓

Agent Workflow
```

---

## 技术方案

### PDF

PyMuPDF

### Word

python-docx

### ASR

Whisper

SenseVoice

### TTS

OpenAI TTS

CosyVoice

### Vision

GPT-4o

Qwen-VL

InternVL

---

# 14. Sandbox设计

## 目标

安全执行：

* Python
* Go
* Java
* SQL

---

## 隔离内容

* CPU
* Memory
* Network
* Process
* Filesystem

---

## 流程

```text
Code Submit

↓

Sandbox Manager

↓

Create Container

↓

Execute

↓

Collect Result

↓

Destroy
```

---

## 实现方案

### MVP

Docker

### Production

gVisor

Kata

Firecracker

---

# 15. Evaluation系统

## 评分维度

### Technical

技术正确性

### Engineering

工程能力

### Architecture

架构能力

### Communication

表达能力

### Problem Solving

问题分析能力

---

## 综合评分

```text
30% 技术

30% 项目

20% 架构

20% 表达
```

---

# 16. Observability

## Trace

一次面试

## Span

* Resume Agent
* Question Agent
* Evaluation Agent
* Report Agent

---

## 指标

* Latency
* Token Usage
* Cost
* Error Rate
* Success Rate

---

# 17. 数据库表设计

核心表：

```text
users

interviews

interview_sessions

interview_messages

resumes

job_descriptions

questions

answers

evaluations

reports

agent_traces

sandbox_runs

files
```

---

# 18. MVP范围

## Phase 1

实现：

* 文本面试
* 简历上传
* JD输入
* 问题生成
* 回答评分
* 报告生成

---

## Phase 2

实现：

* RAG题库
* 动态追问
* 候选人画像

---

## Phase 3

实现：

* 语音面试
* ASR
* TTS

---

## Phase 4

实现：

* 代码题
* Sandbox

---

## Phase 5

实现：

* Agent Trace
* Evaluation Dashboard
* Cost Dashboard

---

## Phase 6

实现：

* Multi Tenant
* RBAC
* Billing
* Quota
* SaaS化部署

---

# 19. 学习目标

通过本项目掌握：

* LangGraph
* Agent Workflow
* State Machine
* RAG
* Memory
* Evaluation
* Tool Calling
* Sandbox
* Multimodal
* Observability
* SaaS Architecture

最终达到能够独立设计和开发企业级 Agent 应用平台的能力。
