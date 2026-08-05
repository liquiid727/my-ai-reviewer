# agent-interview-platform-development-roadmap.md

Version: v1.0

Status: Planning

---

# 项目目标

通过开发 Agent Interview Platform 学习：

* LangGraph
* Agent Workflow
* State Machine
* RAG
* Evaluation
* Memory
* Sandbox
* Multimodal
* SaaS Architecture

最终沉淀：

一个可复用的 Agent Application Framework。

---

# 总开发阶段

```text
Phase 1
基础面试Agent

↓

Phase 2
Workflow升级

↓

Phase 3
RAG知识库

↓

Phase 4
Evaluation系统

↓

Phase 5
Memory系统

↓

Phase 6
Sandbox执行环境

↓

Phase 7
Multimodal

↓

Phase 8
SaaS化
```

---

# Phase 1

MVP面试Agent

预计：

1~2周

---

## 目标

完成：

```text
上传简历

输入JD

生成问题

回答问题

生成报告
```

---

## 技术栈

```text
FastAPI

LangGraph

PostgreSQL

Redis
```

---

## 实现模块

### Resume Service

接口：

```http
POST /api/resume/upload
```

功能：

```text
上传简历

解析文本

存储数据库
```

---

### Interview Service

接口：

```http
POST /api/interview/create
```

功能：

```text
创建面试
```

---

### Question Agent

输入：

```text
Resume

JD
```

输出：

```text
Question
```

---

### Evaluation Agent

输入：

```text
Question

Answer
```

输出：

```json
{
  "score":85,
  "feedback":"..."
}
```

---

## LangGraph

Graph：

```text
START

↓

AnalyzeResume

↓

GenerateQuestion

↓

WaitAnswer

↓

Evaluate

↓

GenerateReport

↓

END
```

---

## 验收标准

能够：

```text
上传简历

生成5个问题

回答

评分

输出报告
```

---

# Phase 2

Workflow升级

预计：

1周

---

## 新增

Stage Router

---

面试阶段：

```text
Resume

↓

Basic

↓

Project

↓

System Design

↓

Summary
```

---

## 新增节点

```text
StageRouter

QuestionGenerator

FollowupGenerator
```

---

Graph：

```text
START

↓

StageRouter

↓

GenerateQuestion

↓

Evaluate

↓

NeedFollowup

↓

NextStage

↓

END
```

---

## 学习目标

理解：

```text
State

Router

Transition
```

---

# Phase 3

RAG知识库

预计：

1周

---

## 新增

题库系统

---

数据来源：

```text
Go

Redis

MySQL

Kubernetes

System Design
```

---

Qdrant Collection：

```text
question_bank
```

---

流程：

```text
Question Request

↓

Retriever

↓

Reranker

↓

Prompt

↓

LLM
```

---

## 学习目标

掌握：

```text
Embedding

Retriever

Hybrid Search

Rerank
```

---

# Phase 4

Evaluation系统

预计：

1周

---

## 评分维度

### Technical

正确性

---

### Engineering

工程深度

---

### Architecture

架构能力

---

### Communication

表达能力

---

### Problem Solving

问题分析能力

---

## Evaluation Agent

输出：

```json
{
  "technical":80,
  "engineering":90,
  "architecture":75,
  "communication":88,
  "summary":"..."
}
```

---

## 学习目标

掌握：

```text
LLM-as-a-Judge

Structured Output

Evaluation Pipeline
```

---

# Phase 5

Memory系统

预计：

1周

---

## 短期记忆

Redis

---

保存：

```text
当前阶段

历史问题

历史回答
```

---

## 长期记忆

PostgreSQL

---

保存：

```text
技能画像

项目画像

弱项画像
```

---

示例：

```json
{
  "skills":["Go","Redis"],
  "weakness":["System Design"]
}
```

---

## 学习目标

掌握：

```text
Session Memory

Long Term Memory

Profile Memory
```

---

# Phase 6

Sandbox

预计：

2周

---

## 场景

代码题

---

支持：

```text
Python

Go

Java
```

---

执行流程：

```text
Submit Code

↓

Sandbox

↓

Execute

↓

Collect Result

↓

Destroy
```

---

## MVP

Docker

---

生产版

```text
gVisor

Firecracker

Kata
```

---

## 学习目标

掌握：

```text
Code Execution

Resource Isolation

Tool Runtime
```

---

# Phase 7

Multimodal

预计：

2周

---

## 语音面试

输入：

```text
Voice
```

↓

```text
ASR
```

↓

```text
Text
```

↓

```text
Agent
```

---

输出：

```text
TTS
```

---

推荐：

```text
Whisper

SenseVoice

OpenAI TTS
```

---

## 图像面试

支持：

```text
系统架构图

流程图

白板截图
```

---

使用：

```text
GPT-4o

Qwen-VL
```

---

## 学习目标

掌握：

```text
Multimodal Agent
```

---

# Phase 8

SaaS化

预计：

3周

---

## Tenant

多租户

---

## RBAC

权限系统

---

## Billing

计费

---

## Quota

额度

---

## Audit

审计

---

## 学习目标

掌握：

```text
Agent SaaS

Platform Design
```

---

# 推荐目录结构

```text
backend/

├── api
│
├── domain
│
├── application
│
├── infrastructure
│
├── workflow
│
├── agents
│
├── rag
│
├── memory
│
├── evaluation
│
├── sandbox
│
├── multimodal
│
└── tests
```

---

# 最终目标

完成后掌握：

✓ LangGraph

✓ Workflow

✓ State Machine

✓ Agent

✓ RAG

✓ Memory

✓ Evaluation

✓ Sandbox

✓ Multimodal

✓ SaaS Platform

并具备开发：

* AI Interview
* AI Recruiter
* AI Tutor
* AI Sales Agent
* AI Customer Service

等企业级 Agent 应用的能力。
